import csv
import os
import json
import tempfile
from datetime import datetime

CSV_FILE = "/Users/hemasagarendluri1996/jira-rag-pipeline/all_issues.csv"

def save_webhook_to_dict(payload: dict) -> dict:
    """Flatten webhook JSON into a dict matching CSV fields."""
    issue = payload.get("issue", {})
    fields = issue.get("fields", {})
    project = fields.get("project", {})

    return {
        "key": issue.get("key"),
        "summary": fields.get("summary"),
        "status": "In Progress",
        "priority": fields.get("priority", {}).get("name"),
        "project": project.get("name"),
        "project_key": project.get("key"),
        "timestamp": datetime.utcnow().isoformat(),  # always update timestamp
    }

def upsert_issue(payload: dict):
    """Upsert webhook payload into CSV without losing existing columns."""
    new_row = save_webhook_to_dict(payload)
    rows = {}
    headers = list(new_row.keys())  # default headers from dict
    action = "inserted"

    # Step 1: Read existing CSV
    if os.path.exists(CSV_FILE) and os.path.getsize(CSV_FILE) > 0:
        with open(CSV_FILE, mode="r", newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            headers = reader.fieldnames or headers
            for row in reader:
                rows[row["key"]] = row

    # Step 2: Update existing row if found
    if new_row["key"] in rows:
        existing = rows[new_row["key"]]
        for k, v in new_row.items():
            if k in existing and v is not None:
                existing[k] = v
        rows[new_row["key"]] = existing
        action = "updated"
    else:
        rows[new_row["key"]] = new_row
        for k in new_row.keys():
            if k not in headers:
                headers.append(k)  # dynamically add new columns if needed

    # Step 3: Safe write back
    tmp_fd, tmp_path = tempfile.mkstemp(prefix="tmp_", dir=os.path.dirname(CSV_FILE) or ".", text=True)
    os.close(tmp_fd)
    try:
        with open(tmp_path, mode="w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=headers)
            writer.writeheader()
            for row in rows.values():
                writer.writerow(row)
        os.replace(tmp_path, CSV_FILE)
        print(f"✅ {action.title()} issue {new_row['key']} into {CSV_FILE}")
        print("📌 Final row data:", rows[new_row["key"]])   # show the row that was updated/inserted
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)

# Example test
if __name__ == "__main__":
    with open("/Users/hemasagarendluri1996/jira-rag-pipeline/data.json", "r", encoding="utf-8") as f:
        payload = json.load(f)
        upsert_issue(payload)
