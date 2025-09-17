from fastapi import FastAPI, Request,HTTPException
from pydantic import BaseModel
# from appjira.rag_engine import run_rag_query
# from appjira.jira_fetcher import run_jira_pipeline
from rag_engine import run_rag_query
# from jira_fetcher import run_jira_pipeline

from datetime import datetime
from fetch_all import JiraPipeline
from dotenv import load_dotenv

import os
import json
# from jira_triage.agent import JiraTriageAgent




app = FastAPI()

# Load env
load_dotenv("/Users/hemasagarendluri1996/Jira_RAG/.env")
JIRA_DOMAIN = os.getenv("JIRA_URL")
API_TOKEN = os.getenv("JIRA_API_TOKEN")
EMAIL = os.getenv("USER_EMAIL")


# Accept a list of questions
class QueryRequest(BaseModel):
    questions: list[str]

@app.post("/rag-query/")
def rag_query(payload: QueryRequest):
    try:
        responses = {}
        for question in payload.questions:
            result = run_rag_query(question)
            responses[question] = result
        return {"responses": responses}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/fetch-jira-data/")
def fetch_jira_data():
    try:
        pipeline = JiraPipeline()
        pipeline.run_pipeline()
        return {"status": "Pipeline executed successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    




WEBHOOK_LOG_FILE = "webhook_events.json"

@app.post("/webhook/")
async def webhook_listener(request: Request):
    try:
        # Get raw payload (bytes → string → dict)
        payload_bytes = await request.body()
        payload_str = payload_bytes.decode("utf-8", errors="replace")

        try:
            issue_payload = json.loads(payload_str)
        except json.JSONDecodeError:
            raise HTTPException(status_code=400, detail="Invalid JSON payload")

        # Add timestamp for tracking
        event_with_meta = {
            "timestamp": datetime.utcnow().isoformat(),
            "payload": issue_payload
        }

        # === Save to JSON file ===
        if os.path.exists(WEBHOOK_LOG_FILE):
            with open(WEBHOOK_LOG_FILE, "r", encoding="utf-8") as f:
                existing_data = json.load(f)
        else:
            existing_data = []

        existing_data.append(event_with_meta)

        with open(WEBHOOK_LOG_FILE, "w", encoding="utf-8") as f:
            json.dump(existing_data, f, indent=2, ensure_ascii=False)

        # === Return response to Postman ===
        return {
            "status": "ok",
            "message": "Webhook event stored successfully",
            "event_preview": issue_payload.get("issue", {}).get("key", "No issue key"),
            "total_events_stored": len(existing_data)
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
