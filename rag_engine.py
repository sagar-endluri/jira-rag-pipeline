import os
from dotenv import load_dotenv
import weaviate
from weaviate.auth import AuthApiKey
import weaviate.classes.query as wq
from langchain.chat_models import ChatOpenAI
from langchain.schema import HumanMessage

# === Load environment variables ===
load_dotenv("/Users/hemasagarendluri1996/Jira_RAG/.env")

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
os.environ['OPENAI_API_KEY'] = OPENAI_API_KEY
WEAVIATE_URL = os.getenv("WEAVIATE_URL")
WEAVIATE_API_KEY = os.getenv("WEAVIATE_API_KEY")

# === Setup LLM ===
llm = ChatOpenAI(openai_api_key=OPENAI_API_KEY, model="gpt-3.5-turbo", temperature=0)

# === Connect to Weaviate ===
client = weaviate.connect_to_weaviate_cloud(
    cluster_url=WEAVIATE_URL,
    auth_credentials=AuthApiKey(api_key=WEAVIATE_API_KEY),
)

if not client.is_ready():
    raise Exception("❌ Weaviate is not reachable")



print("✅ Connected to Weaviate")
# === Use your new collection ===
jira_collection = client.collections.get("newjiras")

def run_rag_query(query: str) -> dict:
    responses = {}

    try:
        # === Retrieve top documents from Weaviate ===
        try:
            context_result = jira_collection.query.bm25(
                query=query,
                limit=10,
                return_metadata=wq.MetadataQuery(score=True)
            )
        except Exception as e:
            error_msg = f"Error retrieving documents from Weaviate: {e}"
            print(error_msg)
            responses[query] = error_msg
            return {"responses": responses}

        # === Format documents ===
        docs = []
        if not getattr(context_result, "objects", None):
            docs.append("No documents retrieved from Weaviate.")
        else:
            for obj in context_result.objects:
                props = getattr(obj, "properties", {}) or {}
                project = props.get("project_name", "Unknown Project")
                key = props.get("key", "")
                summary = props.get("summary", "")
                description = props.get("description", "")
                status = props.get("status", "")
                priority = props.get("priority", "")

                docs.append(
                    f"🔹 Project: {project}\n"
                    f"Issue Key: {key}\n"
                    f"Summary: {summary}\n"
                    f"Description: {description}\n"
                    f"Status: {status} | Priority: {priority}\n"
                )

        context_text = "\n\n".join(docs)

        # === Prompt with instructions ===
        prompt_template = f"""
You are an AI assistant answering questions about real-time Jira issue data.

Context:
{context_text}

Question:
{query}

Provide a clear and concise answer based only on the above context.
"""

        # === Ask OpenAI ===
        try:
            answer = llm([HumanMessage(content=prompt_template)]).content
        except Exception as e:
            error_msg = f"Error generating answer from LLM: {e}"
            print(error_msg)
            responses[query] = error_msg
            return {"responses": responses}

        responses[query] = answer
        print("answer:", answer)

    except Exception as e:
        # Catch any unexpected errors
        error_msg = f"Unexpected error: {e}"
        print(error_msg)
        responses[query] = error_msg

    return {"responses": responses}
