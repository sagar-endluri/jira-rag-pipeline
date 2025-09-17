import os
import json
import pandas as pd
from glob import glob
from uuid import uuid5, NAMESPACE_DNS
from tqdm import tqdm
from dotenv import load_dotenv

from weaviate.auth import AuthApiKey
import weaviate
import weaviate.classes.config as wc

# === Load Environment Variables ===
load_dotenv("/Users/hemasagarendluri1996/jira-rag-pipeline/.env")
JIRA_COLLECTION_NAME = os.getenv("wEAVIATE_COLLECTION_NAME") or "JiraIssue"
# === Part 1: Combine all JSON files into one dataset ===
def get_cleaned_files(folder):
    return glob(os.path.join(folder, "*_cleaned.json"))

def load_json(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)

def combine_issues(folder, output_path="combined"):
    os.makedirs(output_path, exist_ok=True)
    all_issues = []
    project_summary = []

    files = get_cleaned_files(folder)

    for path in files:
        try:
            data = load_json(path)

            if isinstance(data, dict) and "issues" in data:
                issues = data["issues"]
            elif isinstance(data, list):
                issues = data
            else:
                raise ValueError("Unrecognized JSON structure in file: " + path)

            project_name = data.get("project_name", "UnknownProject")
            total = 0

            for issue in issues:
                if not isinstance(issue, dict):
                    continue
                if "project_name" not in issue:
                    issue["project_name"] = project_name
                all_issues.append(issue)
                total += 1

            project_summary.append({
                "project_name": project_name,
                "file": os.path.basename(path),
                "total_issues": total
            })

        except Exception as e:
            print(f"❌ Failed to load {path}: {e}")

    with open(os.path.join(output_path, "all_issues.json"), "w", encoding="utf-8") as f:
        json.dump(all_issues, f, indent=2, ensure_ascii=False)

    with open(os.path.join(output_path, "all_issues.jsonl"), "w", encoding="utf-8") as f:
        for issue in all_issues:
            f.write(json.dumps(issue, ensure_ascii=False) + "\n")

    with open(os.path.join(output_path, "project_summary.json"), "w", encoding="utf-8") as f:
        json.dump(project_summary, f, indent=2, ensure_ascii=False)

    df = pd.DataFrame(all_issues)
    df.to_excel(os.path.join(output_path, "all_issues.xlsx"), index=False)
    df.to_csv(os.path.join(output_path, "all_issues.csv"), index=False)

    print(f"✅ Combined {len(files)} files into {len(all_issues)} issues.")
    print(f"📊 DataFrame shape: {df.shape}")
    print(f"📁 Output saved to: {output_path}")

    return df, all_issues


# === Part 2: Upload to Weaviate (v4 API) ===
def upload_to_weaviate(df):
    client = weaviate.connect_to_weaviate_cloud(
        cluster_url=os.getenv("WEAVIATE_URL"),
        auth_credentials=AuthApiKey(api_key=os.getenv("WEAVIATE_API_KEY")),
        headers={"X-OpenAI-Api-Key": os.getenv("OPENAI_API_KEY")}
    )

    collection_name = JIRA_COLLECTION_NAME

    # Check existing collections
    collections = client.collections.list_all()
    if collection_name not in collections:
        client.collections.create(
            name=collection_name,
            description="Stores Jira issues for RAG queries",
            vectorizer_config=wc.Configure.Vectorizer.text2vec_openai(),  # embed text fields
            properties=[
                wc.Property(name="key", data_type=wc.DataType.TEXT),
                wc.Property(name="project_key", data_type=wc.DataType.TEXT),
                wc.Property(name="project_name", data_type=wc.DataType.TEXT),
                wc.Property(name="summary", data_type=wc.DataType.TEXT),
                wc.Property(name="description", data_type=wc.DataType.TEXT),
                wc.Property(name="issue_type", data_type=wc.DataType.TEXT),
                wc.Property(name="status", data_type=wc.DataType.TEXT),
                wc.Property(name="priority", data_type=wc.DataType.TEXT),
                wc.Property(name="created", data_type=wc.DataType.DATE),
                wc.Property(name="updated", data_type=wc.DataType.DATE),
                wc.Property(name="reporter", data_type=wc.DataType.TEXT),
                wc.Property(name="creator", data_type=wc.DataType.TEXT),
                wc.Property(name="subtasks", data_type=wc.DataType.TEXT_ARRAY),
                wc.Property(name="files", data_type=wc.DataType.TEXT_ARRAY),
                wc.Property(name="parent_summary", data_type=wc.DataType.TEXT),
                wc.Property(name="parent_key", data_type=wc.DataType.TEXT),
                wc.Property(name="parent_priority", data_type=wc.DataType.TEXT),
                wc.Property(name="parent_description", data_type=wc.DataType.TEXT),
                wc.Property(name="parent_issuetype", data_type=wc.DataType.TEXT),
                wc.Property(name="parent_issuetype_icon", data_type=wc.DataType.TEXT),
            ]
        )
        print(f"✅ Collection '{collection_name}' created!")
    else:
        print(f"ℹ️ Collection '{collection_name}' already exists, skipping creation.")

    collection = client.collections.get(collection_name)

    def generate_uuid5(value: str) -> str:
        return str(uuid5(NAMESPACE_DNS, str(value)))

    with collection.batch.fixed_size(50) as batch:
        for _, row in tqdm(df.iterrows(), total=len(df)):
            jira_issue_obj = {
                "key": str(row.get("key", "")),
                "project_key": str(row.get("project_key", "")),
                "project_name": str(row.get("project_name", "")),
                "summary": str(row.get("summary", "")),
                "description": str(row.get("description", "")),
                "issue_type": str(row.get("issue_type", "")),
                "status": str(row.get("status", "")),
                "priority": str(row.get("priority", "")),
                "created": str(row.get("created", "")),
                "updated": str(row.get("updated", "")),
                "reporter": str(row.get("reporter", "")),
                "creator": str(row.get("creator", "")),
                "subtasks": [str(x) for x in row.get("subtasks", [])] if isinstance(row.get("subtasks"), list) else [],
                "files": [str(x) for x in row.get("files", [])] if isinstance(row.get("files"), list) else [],
                "parent_summary": str(row.get("parent_summary", "")),
                "parent_key": str(row.get("parent_key", "")),
                "parent_priority": str(row.get("parent_priority", "")),
                "parent_description": str(row.get("parent_description", "")),
                "parent_issuetype": str(row.get("parent_issuetype", "")),
                "parent_issuetype_icon": str(row.get("parent_issuetype_icon", "")),
            }

            batch.add_object(
                properties=jira_issue_obj,
                uuid=generate_uuid5(row["key"])
            )

    if len(collection.batch.failed_objects) > 0:
        print(f"❌ Failed to import {len(collection.batch.failed_objects)} objects:")
        for failed in collection.batch.failed_objects:
            print(f"→ Error: {failed.message}")
    else:
        print("✅ All data inserted successfully into 'JiraIssue'.")

    client.close()


# === Run Full Pipeline ===
if __name__ == "__main__":
    input_folder = "board_project_data_cleaned"
    combined_df, json_combined_issues = combine_issues(input_folder)
    upload_to_weaviate(combined_df)
