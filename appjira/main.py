from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
# from appjira.rag_engine import run_rag_query
# from appjira.jira_fetcher import run_jira_pipeline
from rag_engine import run_rag_query
# from jira_fetcher import run_jira_pipeline
from fetch_all import JiraPipeline
from dotenv import load_dotenv
from fastapi import FastAPI, Request
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
    


@app.post("/")
async def webhook_listener(request: Request):
    # Get the raw payload (bytes)
    payload_bytes = await request.body()
    # Decode to string for printing (assumes utf-8, which is typical for webhooks)
    payload_str = payload_bytes.decode('utf-8', errors='replace')
    print("🔔 Raw payload received:", payload_str)
    # triage_agent = JiraTriageAgent()
    # import json
    # # Override payload_str with sample file content for local testing
    # try:
    #     with open("data.json", "r") as f:
    #         payload_str = f.read()
    # except FileNotFoundError:
    #     # If sample file is missing, proceed with actual webhook payload
    #     pass
    # try:
    #     issue_payload = json.loads(payload_str)
    # except json.JSONDecodeError:
    #     raise HTTPException(status_code=400, detail="Invalid JSON payload")
    # triage_agent.run(issue_payload)
    return {"status": "ok", "received": bool(payload_str)}
