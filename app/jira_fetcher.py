import os
import json
import hashlib
import requests
from requests.auth import HTTPBasicAuth
from dotenv import load_dotenv
from app.dynamic_cleaning_agentic import process_all_files
from app.download_attachments import JiraAttachmentProcessor
from app.weaviate_create_collections import combine_issues
# Load env
load_dotenv("/Users/hemasagarendluri1996/Jira_RAG/.env")
jira_url = os.getenv("jira_url")
jira_api_token = os.getenv("jira_api_token")
user_email = os.getenv("user_email")

auth = HTTPBasicAuth(user_email, jira_api_token)#"ATATT3xFfGF0hfORXaw3PFI1__5nKfH6fMc7F2oaMZm7Y7sFJ1K-Ip-vAe38Mpi52exFIf9qJQXTRenVv2k_gO02EYpji9pJysD4uA6Ucyca6lyZDJbdk2dL4c58Mf--Iq8LJTjeVTCNtvAKGiLc6H-3rNblZOt1LFPTqU7ERxEPGbOCBbbRpOU=4128C04E")
headers = {"Accept": "application/json"}

output_dir = "board_project_data"
os.makedirs(output_dir, exist_ok=True)

def get_all_boards():
    url = f"{jira_url}/rest/agile/1.0/board"
    # try:
    response = requests.get(url, headers=headers, auth=auth)
    response.raise_for_status()
    return response.json()
    # except requests.RequestException as e:
    #     print(f" Failed to fetch boards: {e}")
    #     return None

def project_board_issues(boards):
    return [
        {
            "board_id": board["id"],
            "board_name": board["name"],
            "board_type": board["type"],
            "project_name": board["location"]["projectName"],
            "project_key": board["location"]["projectKey"],
            "project_id": board["location"]["projectId"],
        }
        for board in boards.get("values", [])
    ]

def calculate_hash(data):
    return hashlib.md5(json.dumps(data, sort_keys=True).encode()).hexdigest()

def is_new_data(board_id, new_data_hash):
    hash_file = os.path.join(output_dir, f"board_{board_id}_hash.txt")
    if os.path.exists(hash_file):
        with open(hash_file, "r") as f:
            old_hash = f.read().strip()
        return old_hash != new_data_hash
    return True

def save_hash(board_id, new_data_hash):
    with open(os.path.join(output_dir, f"board_{board_id}_hash.txt"), "w") as f:
        f.write(new_data_hash)

def fetch_and_save_issues(board):
    board_id = board["board_id"]
    url = f"{jira_url}/rest/agile/1.0/board/{board_id}/issue"
    response = requests.get(url, headers=headers, auth=auth)

    if response.status_code == 200:
        issues = response.json()
        new_hash = calculate_hash(issues)

        if is_new_data(board_id, new_hash):
            filename = os.path.join(output_dir, f"board_{board_id}_issues.json")
            with open(filename, "w") as f:
                json.dump(issues, f, indent=2)
            save_hash(board_id, new_hash)
            return f"Issues updated for board {board_id}"
        else:
            return f"No changes in board {board_id}, skipping update."
    else:
        return f"Failed to fetch issues for board {board_id}, status code: {response.status_code}"

def run_jira_pipeline():
    boards = get_all_boards()
    if not boards:
        return {"status": "Failed to fetch boards"}

    board_list = project_board_issues(boards)
    update_messages = []

    for board in board_list:
        msg = fetch_and_save_issues(board)
        update_messages.append(msg)

    # Clean the data
    input_folder = "board_project_data"
    output_folder = "board_project_data_cleaned"
    processor = JiraAttachmentProcessor()
    process_all_files(input_folder, output_folder, processor)
    df ,json_all_issues = combine_issues(output_folder)
    # print(df)
    # print(json_all_issues)
    # with open(os.path.join(output_path, "project_summary.json"), "w", encoding="utf-8") as f:
    #     json.dump(project_summary, f, indent=2, ensure_ascii=False)
    return json_all_issues
# {
#         "status": "Success",
#         "updates": json_all_issues
#     }
