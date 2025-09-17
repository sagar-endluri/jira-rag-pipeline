import requests
import json
import hashlib
import os
from requests.auth import HTTPBasicAuth
from dotenv import load_dotenv
from dynamic_cleaning_agentic import process_all_files
from download_attachments import JiraAttachmentProcessor
from weaviate_create_collections import combine_issues, upload_to_weaviate


class JiraPipeline:
    def __init__(self, env_path="/Users/hemasagarendluri1996/jira-rag-pipeline/.env", output_dir="board_project_data"):
        # Load credentials
        load_dotenv(env_path)
        self.jira_url = os.getenv("JIRA_URL")
        self.jira_api_token = os.getenv("JIRA_API_TOKEN")
        self.user_email = os.getenv("USER_EMAIL")
        self.collection_name = os.getenv("WEAVIATE_COLLECTION_NAME")

        # Auth and headers
        self.auth = HTTPBasicAuth(self.user_email, self.jira_api_token)
        self.headers = {"Accept": "application/json"}

        # Directories
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)

    # ------------------ Utility Methods ------------------
    def _calculate_hash(self, data):
        return hashlib.md5(json.dumps(data, sort_keys=True).encode()).hexdigest()

    def _is_new_data(self, board_id, new_data_hash):
        hash_file = os.path.join(self.output_dir, f"board_{board_id}_hash.txt")
        if os.path.exists(hash_file):
            with open(hash_file, "r") as f:
                old_hash = f.read().strip()
            return old_hash != new_data_hash
        return True

    def _save_hash(self, board_id, new_data_hash):
        with open(os.path.join(self.output_dir, f"board_{board_id}_hash.txt"), "w") as f:
            f.write(new_data_hash)

    def _get(self, endpoint):
        url = f"{self.jira_url}{endpoint}"
        response = requests.get(url, headers=self.headers, auth=self.auth)
        response.raise_for_status()
        return response.json()

    # ------------------ Jira Data Collection ------------------
    def get_all_boards(self):
        return self._get("/rest/agile/1.0/board")

    def project_board_issues(self, boards):
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

    def fetch_project_data(self, project_key):
        """Fetch all boards, sprints, and issues for a given project key."""
        project_url = f"/rest/agile/1.0/board?projectKeyOrId={project_key}"
        boards = self._get(project_url)

        project_data = {"project": project_key, "boards": []}

        for board in boards.get("values", []):
            board_id = board["id"]
            board_info = {"id": board_id, "name": board["name"], "sprints": []}

            # ---- Get Sprints ----
            sprints = self._get(f"/rest/agile/1.0/board/{board_id}/sprint")

            for sprint in sprints.get("values", []):
                sprint_id = sprint["id"]
                sprint_info = sprint.copy()
                sprint_info["issues"] = []

                # ---- Get Issues ----
                issues = self._get(f"/rest/agile/1.0/sprint/{sprint_id}/issue")
                sprint_info["issues"].extend(issues.get("issues", []))
                board_info["sprints"].append(sprint_info)

            project_data["boards"].append(board_info)

            # ---- Save with Hash Check ----
            new_hash = self._calculate_hash(project_data)
            if self._is_new_data(board_id, new_hash):
                filename = os.path.join(self.output_dir, f"project_{project_key}_board_{board_id}.json")
                with open(filename, "w") as f:
                    json.dump(project_data, f, indent=2)
                self._save_hash(board_id, new_hash)
                print(f"✅ Issues updated for board {board_id}")
            else:
                print(f"No changes in board {board_id}, skipping update.")

        return project_data

    # ------------------ Full Pipeline ------------------
    def run_pipeline(self):
        boards = self.get_all_boards()
        projects = self.project_board_issues(boards)
        print("Boards and Projects:", projects)

        for project in projects:
            print(f"🔄 Exporting project: {project['project_key']}")
            self.fetch_project_data(project["project_key"])

        # ---- Cleaning + Upload to Weaviate ----
        input_folder = self.output_dir
        output_folder = f"{self.output_dir}_cleaned"
        processor = JiraAttachmentProcessor()
        print("Starting data cleaning...",input_folder,output_folder)
        process_all_files(input_folder, output_folder, processor)
        combined_df, _ = combine_issues(output_folder)
        upload_to_weaviate(combined_df)


# if __name__ == "__main__":
#     pipeline = JiraPipeline(env_path="/Users/hemasagarendluri1996/jira-rag-pipeline/.env")
    
