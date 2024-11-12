
# Retrieve environment variables
from fastapi import FastAPI, Request, HTTPException, BackgroundTasks
from fastapi import APIRouter
from logger import main_logger
from chatops_client.slack.slack_functions import check_signature, process_event
import os, json, time
import hmac, hashlib
from pydantic import BaseModel
from chatops_agents_hub.cloud_agents.gcp.gcp_error_reporting_agent import handle_user_request

router = APIRouter()

class MessageBody(BaseModel):
    text: str

# Retrieve the Slack signing secret from environment variables
@router.post("/gcp_agent",tags=["cloud_agent"])
async def gcp_agent(request: Request,background_tasks: BackgroundTasks,body: MessageBody):
    # Log the parsed 'text' from the request body
    main_logger.info(f"Parsed text: {body.text}")
    result = handle_user_request(body.text)
    main_logger.info(f"Result from OpenAI: {result}")
    return {"resul": result}

