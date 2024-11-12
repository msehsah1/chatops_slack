from fastapi import FastAPI, Request, HTTPException, BackgroundTasks
import hmac
import hashlib
import time
import json
import os
import httpx
import logging 
import asyncio
# main.py
from logger import main_logger
from exceptions import GcpKeyNotFound
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

app = FastAPI()
client = httpx.AsyncClient()


from fastapi import Depends, FastAPI
from chatops_apis_routers import slack, gcloud_error_reporting_api
#from .dependencies import get_query_token, get_token_header

#app = FastAPI(dependencies=[Depends(get_query_token)])
app = FastAPI()
app.include_router(slack.router)
app.include_router(gcloud_error_reporting_api.router)

@app.get("/")
async def root():
    return {"message": "chatops agent!"}