import os
import json
import pandas as pd
from pandas import json_normalize  # for flattening nested fields

# Step 1: Path to your folder with JSON files
folder_path = "jira-rag-pipeline/board_project_data_cleaned"

# Step 2: Load all JSON files
json_list = []
output_path="combined"
os.makedirs(output_path, exist_ok=True)
for filename in os.listdir(folder_path):
    if filename.endswith(".json"):
        print("filename",filename)
        file_path = os.path.join(folder_path, filename)
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            # If your file is an array of records
            if isinstance(data, list):
                json_list.extend(data)
            else:
                json_list.append(data)

# Step 3: Convert to DataFrame
df = json_normalize(json_list)

# Optional: Show first few rows
print(df.head())

# Step 4: Save as CSV or Excel if needed
df.to_csv("combined_jira_data.csv", index=False)
# or
df.to_excel("combined_jira_data.xlsx", index=False)
