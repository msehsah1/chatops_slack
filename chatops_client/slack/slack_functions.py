
from fastapi import HTTPException
import time
import hmac, hashlib
import json
import httpx
from logger import main_logger
from chatops_agents_hub.cloud_agents.gcp.gcp_error_reporting_agent import handle_user_request
import os 

client = httpx.AsyncClient()

SLACK_SIGNING_SECRET = os.getenv("SLACK_SIGNING_SECRET")
SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN")

def check_signature(request_header, body, slack_signed_secret):
    check_signature_result = False
    slack_signature = request_header.get("X-Slack-Signature")
    slack_timestamp = request_header.get("X-Slack-Request-Timestamp")
    if not slack_signature or not slack_timestamp:
        print("Slack signature or timestamp missing")
        raise HTTPException(status_code=400, detail="Slack signature or timestamp missing")

    current_time = int(time.time())
    time_difference = abs(current_time - int(slack_timestamp))
    print("time_difference==",time_difference)
    if time_difference > 20 :
        print("Request timestamp out of allowed range")
        raise HTTPException(status_code=400, detail="Request timestamp out of allowed range")
    base_string = f"v0:{slack_timestamp}:{body.decode('utf-8')}"
    # Step 4: Generate HMAC SHA256 signature using the Slack signing secret
    my_signature = 'v0=' + hmac.new(
        slack_signed_secret.encode('utf-8'),
        base_string.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()
    # Step 5: Compare signatures securely
    if not hmac.compare_digest(my_signature, slack_signature):
       raise HTTPException(status_code=400, detail="Invalid request signature")
    else:
        check_signature_result=True
    return check_signature_result

def generate_error_block(errors) -> list:
    """
    Generates a Block Kit JSON payload for Slack based on multiple error and solution data.

    :param error_data: A list of dictionaries, each containing error details.
    :param solution_data: A list of dictionaries, each containing solution details for the corresponding error.
    :return: A list representing the Block Kit JSON payload.
    """
    blocks = [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": "🚨 Error Report",
                "emoji": True
            }
        },
        {"type": "divider"},
    ]
    for error in errors:
        error_data = json.loads(error)
        error_summary = error_data.get("error_summary",{})
        potential_solution = error_data.get("potential_solution",{})
        blocks.extend([
            {
                "type": "section",
                "fields": [
                    {"type": "mrkdwn", "text": f"*Project ID:*\n{error_summary.get('project_id', 'N/A')}"},
                    {"type": "mrkdwn", "text": f"*Affected Service:*\n{error_summary.get('affected_service', 'N/A')}"},
                    {"type": "mrkdwn", "text": f"*Service Version:*\n{error_summary.get('service_version', 'N/A')}"},
                    {"type": "mrkdwn", "text": f"*Error Type:*\n{error_summary.get('error_type', 'N/A')}"},
                    {"type": "mrkdwn", "text": f"*Resource Type:*\n{error_summary.get('resource_type', 'N/A')}"}
                ]
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Error Description:*\n{error_summary.get('error_description', 'No description provided.')}"
                }
            },
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": "💡 Potential Solutions",
                    "emoji": True
                }
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Suggested Action:*\n{potential_solution.get('suggested_action', 'No action suggested.')}"
                }
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Code Snippet:*\n```python\n{potential_solution.get('code_snippet', '# No code provided.')}\n```"
                }
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Additional Tip:*\n{potential_solution.get('additional_tip', 'No additional tips.')}"
                }
            },
            {"type": "divider"},
        ])

    # Optionally, add a final context section
    blocks.append({
        "type": "context",
        "elements": [
            {
                "type": "mrkdwn",
                "text": "• For more details, visit the [project dashboard](https://your-dashboard-link.com)."
            }
        ]
    })
    return blocks

async def process_event(event):
    user = event.get('user')
    text = event.get('text')
    channel = event.get('channel')
    # Process the message as needed
    result = handle_user_request(text)
    use_blocks=False
    message_for_user = result
    if isinstance(result, list) and 'error_summary' in json.loads(result[0]):
        message_for_user = generate_error_block(result)
        use_blocks=True
    await send_message(channel, message_for_user, use_blocks)

async def send_message(channel: str, message: str,use_blocks: bool, retries: int = 3, backoff_factor: float = 0):
    """
    Sends a message to a Slack channel using Slack's REST API with retry logic.

    Args:
        channel (str): The ID of the Slack channel where the message will be sent.
        text (str): The text content of the message.
        retries (int): Number of retry attempts in case of failure.
        backoff_factor (float): Factor for exponential backoff between retries.
    """
    try:
            response = await client.post(
                "https://slack.com/api/chat.postMessage",
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {SLACK_BOT_TOKEN}"
                },
                json={
                    "channel": channel,
                    "text": message if not use_blocks else None, 
                    "blocks": message if use_blocks else None,
                }
            )
            response_data = response.json()
            if response_data.get("ok"):
                main_logger.info(f"Message sent successfully to channel {channel}")
                return
            else:
                error = response_data.get("error")
                main_logger.error(f"Error sending message: {error}")
                if error in ["rate_limited", "server_error"]:
                    raise httpx.HTTPError(f"Slack API error: {error}")
    except httpx.HTTPError as e:
            main_logger.info(f"Retrying in  seconds...")