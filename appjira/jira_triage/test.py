

from http.client import HTTPException
import json
from urllib import request
from agent import JiraTriageAgent

# def webhook_listener():
import json
from agent import JiraTriageAgent

import json
from agent import JiraTriageAgent

agent = JiraTriageAgent()

# Read each JSON object from file separately
with open("/Users/hemasagarendluri1996/jira-rag-pipeline/data.json", "r") as f:
    for line in f:
        line = line.strip()
        if not line:
            continue
        try:
            issue_payload = json.loads(line)
        except json.JSONDecodeError as e:
            print(f"❌ Failed to decode JSON: {e}")
            continue

        print("🔔 Raw payload received:", issue_payload)
        messages = agent.run(issue_payload)

        # Print final conversation outcome
        print("\n=== Group Chat Outcome ===")
        for msg in messages:
            print(f"[{msg['role']}] {msg['content']}")


    # return {"status": "ok", "received": bool(payload_str)}

