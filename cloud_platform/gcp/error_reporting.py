import google.auth
from google.auth.transport.requests import Request
import requests
import datetime
import json

# Constants
SCOPES = ['https://www.googleapis.com/auth/cloud-platform']
API_BASE_URL = "https://clouderrorreporting.googleapis.com/v1beta1"

def get_access_token():
    """
    Obtains an access token using Google Application Default Credentials.

    Returns:
        tuple: (access token, project ID)
    """
    credentials, project_id = google.auth.default(scopes=SCOPES)
    credentials.refresh(Request())
    return credentials.token, project_id

def list_error_groups(project_id):
    """
    Retrieves error groups from the Error Reporting API.

    Args:
        project_id (str): GCP project ID.
        time_range_days (int): Number of days to look back for errors.

    Returns:
        list: List of error groups.
    """
    access_token, _ = get_access_token()
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/json"
    }

    # Prepare the request parameters
    params = {
        "pageSize": 100  # Adjust as needed
    }

    url = f"{API_BASE_URL}/projects/{project_id}/groupStats"

    error_groups = []
    next_page_token = None

    try:
        while True:
            if next_page_token:
                params['pageToken'] = next_page_token
            response = requests.get(url, headers=headers, params=params)
            response.raise_for_status()
            data = response.json()
            error_groups.extend(data.get('errorGroupStats', []))
            next_page_token = data.get('nextPageToken')
            if not next_page_token:
                break
    except requests.exceptions.HTTPError as http_err:
        print(f"HTTP error occurred while listing groups: {http_err} - {response.text}")
    except Exception as err:
        print(f"An error occurred while listing groups: {err}")

    return error_groups


def format_response_llm(project_id):
    list_errors = []
    error_groups = list_error_groups(project_id)
    for group_stat in error_groups:
        group = group_stat.get('group', {})
        group_resolution_status = group.get('resolutionStatus') 
        if group_resolution_status == "OPEN":
            error_info  = {}
            error_info["project_id"] = project_id
            error_info["group_name"] = group.get('name', "empty")
            error_info["resolution_status"] = group_resolution_status
            error_info["group_count"] = group_stat.get('count', 0)
            error_info["affected_service"] = group_stat.get('affectedServices',{})
            representative = group_stat.get('representative',{})
            error_info["serviceContext"] =representative.get('serviceContext',{})
            error_info["error_message"] =representative.get('message',{})
            list_errors.append(error_info) 
    return list_errors
