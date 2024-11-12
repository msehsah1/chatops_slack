import json
from openai import OpenAI
from logger import main_logger
from chatops_tools.cloud_tools.gcp.error_reporting import format_response_llm
from pydantic import BaseModel
from typing import Optional
client = OpenAI()


gcp_init_messages = [
    {"role": "system", "content": "You are a GCP cloud expert, that help user to perform their request on GCP."},
]

class ErrorSummary(BaseModel):
    project_id: str
    affected_service: str
    service_version: str
    error_type: str
    error_description: str
    resource_type: str

class PotentialSolution(BaseModel):
    suggested_action: str
    code_snippet: Optional[str] = None
    additional_tip: str

class ErrorReport(BaseModel):
    error_summary: ErrorSummary
    potential_solution: PotentialSolution


def summarize_error(message):
    response = client.beta.chat.completions.parse(
        model="gpt-4o-mini",
        messages=message,
        response_format=ErrorReport
    )
    result = response.choices[0].message.content
    return result

def get_error_reporting_gcp(project_id):
    list_of_errors = format_response_llm(project_id)
    gcp_message = gcp_init_messages
    main_logger.info("list_of_errors")
    main_logger.info(list_of_errors)
    all_error_message = []
    if len(list_of_errors) > 0:
        for error in list_of_errors:
             error_content = str(error)
             error_content = "summarize the following error and give a potential solution, return the result in JSON format" + error_content
             error_summarizer = {"role": "user", "content": error_content}
             gcp_message.append(error_summarizer)
             error_sumary = summarize_error(gcp_message)
             all_error_message.append(error_sumary)
    return all_error_message


# Define the functions available to the assistant
tools = [
    {
        "type":"function",
        "function" : {
        "name": "get_error_reporting_gcp",
        "description": "List all errors related to a specific porject in GCP",
        "parameters": {
            "type": "object",
            "properties": {
                "project_id": {
                    "type": "string",
                    "description": "The GCP project ID."
                }
            },
            "required": ["project_id"]
        }
      }
    }
]

# Initial messages


# Function to execute the assistant's function calls
def execute_function_call(function):
    function_name = function.name
    arguments = json.loads(function.arguments)
    
    if function_name == "get_error_reporting_gcp":
        main_logger.info("get_error_reporting_gcp")
        result = get_error_reporting_gcp(**arguments)
    else:
        result = f"Function '{function_name}' not found."
    return result



def handle_user_request(user_request):
    gcp_init_messages = [
        {"role": "system", "content": "You are a GCP cloud expert, that help user to perform their request on GCP."},
        {"role": "user", "content": user_request},
    ]
    response = client.chat.completions.create(
        model="gpt-4",
        messages=gcp_init_messages,
        tools=tools,
        tool_choice="auto",
    )
    message = response.choices[0].message
    main_logger.info(f"OpenAI message {message}")
    if message.tool_calls:
        function = message.tool_calls[0].function
        result = execute_function_call(function)
    else:
        result = message.content
    return result

