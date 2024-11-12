
# Retrieve environment variables
from fastapi import FastAPI, Request, HTTPException, BackgroundTasks
from fastapi import APIRouter
from logger import main_logger
from exceptions import SlackSecretsNotfound
from chatops_client.slack.slack_functions import check_signature, process_event
import os, json, time
import hmac, hashlib

router = APIRouter()
SLACK_SIGNING_SECRET = os.getenv("SLACK_SIGNING_SECRET")
SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN")

# Validate environment variables
if not SLACK_SIGNING_SECRET:
    raise SlackSecretsNotfound("SLACK_SIGNING_SECRET is not set in the environment variables.")
if not SLACK_BOT_TOKEN:
    raise SlackSecretsNotfound("SLACK_BOT_TOKEN is not set in the environment variables.")


@router.get("/slack/health",tags=["slack"])
async def slack_endpoint_health():
    return 200

# Retrieve the Slack signing secret from environment variables
@router.post("/slack/events",tags=["slack"])
async def slack_events(request: Request,background_tasks: BackgroundTasks):
    # Read the raw body of the request
    body = await request.body()
    # Parse the request body as JSON
    headers = request.headers
    data = json.loads(body)
    check_signature_output = check_signature(headers, body, SLACK_SIGNING_SECRET)
    if check_signature_output == False:
        raise HTTPException(status_code=400, detail="Invalid request signature")
    
    # Handle Slack URL verification challenge
    if data.get('type') == 'url_verification':
        return {"challenge": data.get('challenge')}

    # Handle event callbacks
    if data.get('type') == 'event_callback':
        event = data.get('event', {})
        event_type = event.get('type')
        # Example: Handle message events
        if (event_type == 'message' or event_type == 'app_mention')  and 'bot_id' not in event:
            background_tasks.add_task(process_event, event)
            return {"ok": True}
    return {"ok": True}

