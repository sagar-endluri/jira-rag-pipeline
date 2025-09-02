from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from app.rag_engine import run_rag_query
from app.jira_fetcher import run_jira_pipeline
from dotenv import load_dotenv
from fastapi import FastAPI, Request
import os
import json
app = FastAPI()



# Load env
load_dotenv("/Users/hemasagarendluri1996/Jira_RAG/.env")
JIRA_DOMAIN = os.getenv("jira_url")
API_TOKEN = os.getenv("jira_api_token")
EMAIL = os.getenv("user_email")


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
        result = run_jira_pipeline()
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    


@app.post("/")
async def jira_webhook_listener(request: Request):
    """
    Receives Jira webhook events and prints key information:
    - Event type
    - Issue key
    - Summary
    - Issue type
    - Status
    - User who made the change
    """

    # Get raw body
    raw_body = await request.body()
    if not raw_body:
        print("⚠️ Empty webhook payload received")
        return {"status": "no payload"}

    # Parse JSON safely
    try:
        body = json.loads(raw_body)
    except json.JSONDecodeError:
        print("⚠️ Received non-JSON payload:", raw_body)
        return {"status": "invalid json", "data": raw_body.decode("utf-8")}

    # Extract useful fields
    webhook_event = body.get("webhookEvent", "unknown_event")
    issue = body.get("issue", {})
    issue_key = issue.get("key", "N/A")
    fields = issue.get("fields", {})
    summary = fields.get("summary", "N/A")
    issue_type = fields.get("issuetype", {}).get("name", "N/A")
    status = fields.get("status", {}).get("name", "N/A")
    user = body.get("user", {}).get("displayName", "N/A")

    # Print nicely
    print(f"\n🔔 Jira Event Received: {webhook_event}")
    print(f"Issue Key: {issue_key}")
    print(f"Summary: {summary}")
    print(f"Issue Type: {issue_type}")
    print(f"Status: {status}")
    print(f"Changed by: {user}")

    return {"status": "ok"}