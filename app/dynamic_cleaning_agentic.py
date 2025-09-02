import os
import json
from app.download_attachments import JiraAttachmentProcessor
from dateutil import parser as date_parser

# === Helper to load JSON ===
def load_json(file_path):
    with open(file_path, 'r') as f:
        return json.load(f)

# === Get all JSON files ===
def get_all_json_files(folder_path):
    return [
        os.path.join(root, file)
        for root, _, files in os.walk(folder_path)
        for file in files if file.endswith(".json")
    ]

def parse_datetime_rfc3339(date_str):
    try:
        dt = date_parser.parse(date_str)
        return dt.isoformat()
    except Exception:
        return ""

def extract_issue_data(issue, attachments_folder, processor):
    fields = issue.get("fields", {})
    issue_key = issue.get("key", "")
    project = fields.get("project", {})
    parent = fields.get("parent", {})

    issue_data = {
        "key": issue_key,
        "project_key": project.get("key", ""),
        "project_name": project.get("name", ""),
        "summary": fields.get("summary", ""),
        "description": fields.get("description", ""),
        "issue_type": fields.get("issuetype", {}).get("name", ""),
        "status": fields.get("status", {}).get("name", ""),
        "priority": fields.get("priority", {}).get("name", ""),
        "created": parse_datetime_rfc3339(fields.get("created", "")),
        "updated": parse_datetime_rfc3339(fields.get("updated", "")),
        "reporter": fields.get("reporter", {}).get("displayName", ""),
        "creator": fields.get("creator", {}).get("displayName", ""),
        "subtasks": [],
        "files": []
    }

    # ✅ Extract custom parent info with full issuetype details
    if parent and "fields" in parent:
        parent_fields = parent["fields"]
        issuetype = parent_fields.get("issuetype", {})

        issue_data["parent_summary"] = parent_fields.get("summary", "")
        issue_data["parent_key"] = parent.get("key", "")
        issue_data["parent_priority"] = parent_fields.get("priority", {}).get("name", "")
        issue_data["parent_description"] = issuetype.get("description", "")
        issue_data["parent_issuetype"] = issuetype.get("name", "")
        issue_data["parent_issuetype_icon"] = issuetype.get("iconUrl", "")

    # ✅ Add subtasks
    for sub in fields.get("subtasks", []):
        sub_fields = sub.get("fields", {})
        issue_data["subtasks"].append({
            "key": sub.get("key", ""),
            "summary": sub_fields.get("summary", ""),
            "status": sub_fields.get("status", {}).get("name", ""),
            "issuetype": sub_fields.get("issuetype", {}).get("name", "")
        })

    # ✅ Process attachments
    for att in fields.get("attachment", []):
        filename = att.get("filename")
        content_url = att.get("content")
        if filename and content_url and attachments_folder:
            issue_folder = os.path.join(attachments_folder, issue_key)
            extracted_text = processor.download_attachment(content_url, filename, issue_folder)
            issue_data["files"].append({
                "filename": filename,
                "extracted_text": extracted_text
            })
        


    return issue_data

# === Main processor ===
def process_all_files(input_folder, output_folder, processor):
    os.makedirs(output_folder, exist_ok=True)
    all_files = get_all_json_files(input_folder)

    for file_path in all_files:
        try:
            data = load_json(file_path)
            issues = data.get("issues", [])
            if not issues:
                continue

            project_name = issues[0].get("fields", {}).get("project", {}).get("name", "UnknownProject")
            cleaned_issues = []

            filename_stem = os.path.basename(file_path).replace(".json", "")
            attachments_folder = os.path.join(output_folder, f"{filename_stem}_attachments")

            for issue in issues:
                cleaned = extract_issue_data(issue, attachments_folder, processor)
                cleaned_issues.append(cleaned)

            output_data = {
                "project_name": project_name,
                "maxResults": len(cleaned_issues),
                "total": len(cleaned_issues),
                "issues": cleaned_issues
            }

            output_filename = filename_stem + "_cleaned.json"
            output_path = os.path.join(output_folder, output_filename)

            with open(output_path, 'w') as f:
                json.dump(output_data, f, indent=2)

            print(f"✅ Saved cleaned file: {output_path}")

        except Exception as e:
            print(f"❌ Error in {file_path}: {e}")

# === Run the script ===
if __name__ == "__main__":
    processor = JiraAttachmentProcessor()
    input_folder = "board_project_data"          # your input path here
    output_folder = "board_project_cleaned"      # your output path here
    process_all_files(input_folder, output_folder, processor)
    