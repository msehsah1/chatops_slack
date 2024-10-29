from fastapi import FastAPI, Request, HTTPException
import hmac
import hashlib
import time
import json
import os
import httpx
import logging
import asyncio
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

app = FastAPI()
client = httpx.AsyncClient()

# Retrieve environment variables
SLACK_SIGNING_SECRET = os.getenv("SLACK_SIGNING_SECRET")
SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN")

# Validate environment variables
if not SLACK_SIGNING_SECRET:
    raise ValueError("SLACK_SIGNING_SECRET is not set in the environment variables.")
if not SLACK_BOT_TOKEN:
    raise ValueError("SLACK_BOT_TOKEN is not set in the environment variables.")

# Configure the root logger
logging.basicConfig(
    level=logging.INFO,  # Set the minimum log level to INFO
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler()  # Log to standard output (console)
    ]
)

# Create a logger for your application
logger = logging.getLogger(__name__)

@app.post("/slack/events")
async def slack_events(request: Request):
    try:
        # Retrieve headers
        slack_signature = request.headers.get("X-Slack-Signature")
        slack_timestamp = request.headers.get("X-Slack-Request-Timestamp")

        if not slack_signature or not slack_timestamp:
            logger.warning("Missing Slack signature or timestamp.")
            raise HTTPException(status_code=400, detail="Slack signature or timestamp missing.")

        # Protect against replay attacks
        current_time = int(time.time())
        if abs(current_time - int(slack_timestamp)) > 60 * 5:
            logger.warning("Slack request timestamp is too old.")
            raise HTTPException(status_code=400, detail="Request timestamp out of allowed range.")

        # Read the raw body of the request
        body = await request.body()
        body_str = body.decode('utf-8')
        data = json.loads(body_str)
        logger.debug(f"Received data: {data}")

        # Create the basestring for signature verification
        basestring = f"v0:{slack_timestamp}:{body_str}"

        # Generate HMAC SHA256 signature using the Slack signing secret
        my_signature = 'v0=' + hmac.new(
            SLACK_SIGNING_SECRET.encode('utf-8'),
            basestring.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()

        # Compare signatures securely
        if not hmac.compare_digest(my_signature, slack_signature):
            logger.warning("Invalid Slack signature.")
            raise HTTPException(status_code=400, detail="Invalid request signature.")

        logger.info("Valid Slack request received.")

        # Handle Slack URL verification challenge
        if data.get('type') == 'url_verification':
            return {"challenge": data.get('challenge')}

        # Handle event callbacks
        if data.get('type') == 'event_callback':
            event = data.get('event', {})
            event_type = event.get('type')

            # Handle message and app_mention events
            if (event_type in ['message', 'app_mention']) and not event.get('bot_id'):
                user = event.get('user')
                text = event.get('text')
                channel = event.get('channel')
                ts = event.get('ts')
                logger.info(f"Message from user {user} in channel {channel}: {text}")

                # Integrate with LLM here (e.g., generate a response)
                response_text = "Hello From DevOps Assistante"

                await send_message(channel, response_text)

        return {"ok": True}

    except json.JSONDecodeError:
        logger.error("Invalid JSON payload.")
        raise HTTPException(status_code=400, detail="Invalid JSON payload.")
    except Exception as e:
        logger.exception("An error occurred while processing the request.")
        raise HTTPException(status_code=500, detail="Internal server error.")

async def send_message(channel: str, text: str, retries: int = 3, backoff_factor: float = 0.5):
    """
    Sends a message to a Slack channel using Slack's REST API with retry logic.

    Args:
        channel (str): The ID of the Slack channel where the message will be sent.
        text (str): The text content of the message.
        retries (int): Number of retry attempts in case of failure.
        backoff_factor (float): Factor for exponential backoff between retries.
    """
    for attempt in range(1, retries + 1):
        try:
            response = await client.post(
                "https://slack.com/api/chat.postMessage",
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {SLACK_BOT_TOKEN}"
                },
                json={
                    "channel": channel,
                    "text": text
                }
            )
            response_data = response.json()
            if response_data.get("ok"):
                logger.info(f"Message sent successfully to channel {channel}")
                return
            else:
                error = response_data.get("error")
                logger.error(f"Error sending message: {error}")
                if error in ["rate_limited", "server_error"]:
                    raise httpx.HTTPError(f"Slack API error: {error}")
                else:
                    break  # Non-retryable error
        except httpx.HTTPError as e:
            logger.error(f"Attempt {attempt}: HTTP error occurred while sending message: {e}")
            if attempt < retries:
                sleep_time = backoff_factor * (2 ** (attempt - 1))
                logger.info(f"Retrying in {sleep_time} seconds...")
                await asyncio.sleep(sleep_time)
            else:
                logger.error("Max retries reached. Failed to send message.")