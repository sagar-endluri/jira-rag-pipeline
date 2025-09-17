# import os
# from dotenv import load_dotenv
# import weaviate
# from weaviate.auth import AuthApiKey
# import weaviate.classes.query as wq
# from langchain.chat_models import ChatOpenAI
# from langchain.schema import HumanMessage

# # === Load environment variables ===
# load_dotenv("/Users/hemasagarendluri1996/jira-rag-pipeline/.env")

# OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
# os.environ['OPENAI_API_KEY'] = OPENAI_API_KEY
# print("OpenAI API Key loaded.", OPENAI_API_KEY)
# WEAVIATE_URL = os.getenv("WEAVIATE_URL")
# WEAVIATE_API_KEY = os.getenv("WEAVIATE_API_KEY")
# JIRA_COLLECTION_NAME = os.getenv("WEAVIATE_COLLECTION_NAME")

# # === Setup LLM ===
# llm = ChatOpenAI(openai_api_key=OPENAI_API_KEY, model="gpt-3.5-turbo", temperature=0)

# # === Connect to Weaviate ===
# client = weaviate.connect_to_weaviate_cloud(
#     cluster_url=WEAVIATE_URL,
#     auth_credentials=AuthApiKey(api_key=WEAVIATE_API_KEY),
# )

# if not client.is_ready():
#     raise Exception("❌ Weaviate is not reachable")



# print("✅ Connected to Weaviate RAG database.")
# # === Use your new collection ===
# jira_collection = client.collections.get(JIRA_COLLECTION_NAME)

# def run_rag_query(query: str) -> dict:
#     responses = {}

#     try:
#         # === Retrieve top documents from Weaviate ===
#         try:
#             context_result = jira_collection.query.bm25(
#                 query=query,
#                 limit=10,
#                 return_metadata=wq.MetadataQuery(score=True)
#             )
#         except Exception as e:
#             error_msg = f"Error retrieving documents from Weaviate: {e}"
#             print(error_msg)
#             responses[query] = error_msg
#             return {"responses": responses}

#         # === Format documents ===
#         docs = []
#         if not getattr(context_result, "objects", None):
#             docs.append("No documents retrieved from Weaviate.")
#         else:
#             for obj in context_result.objects:
#                 props = getattr(obj, "properties", {}) or {}
#                 project = props.get("project_name", "Unknown Project")
#                 key = props.get("key", "")
#                 summary = props.get("summary", "")
#                 description = props.get("description", "")
#                 status = props.get("status", "")
#                 priority = props.get("priority", "")

#                 docs.append(
#                     f"🔹 Project: {project}\n"
#                     f"Issue Key: {key}\n"
#                     f"Summary: {summary}\n"
#                     f"Description: {description}\n"
#                     f"Status: {status} | Priority: {priority}\n"
#                 )

#         context_text = "\n\n".join(docs)

#         # === Prompt with instructions ===
#         prompt_template = f"""
# You are an AI assistant answering questions about real-time Jira issue data.

# Context:
# {context_text}

# Question:
# {query}

# Provide a clear and concise answer based only on the above context.
# """

#         # === Ask OpenAI ===
#         try:
#             answer = llm([HumanMessage(content=prompt_template)]).content
#         except Exception as e:
#             error_msg = f"Error generating answer from LLM: {e}"
#             print(error_msg)
#             responses[query] = error_msg
#             return {"responses": responses}

#         responses[query] = answer
#         print("answer:", answer)

#     except Exception as e:
#         # Catch any unexpected errors
#         error_msg = f"Unexpected error: {e}"
#         print(error_msg)
#         responses[query] = error_msg

#     return {"responses": responses}

import os
from dotenv import load_dotenv
import weaviate
from weaviate.auth import AuthApiKey
import weaviate.classes.query as wq
from langchain.chat_models import ChatOpenAI
from langchain.schema import HumanMessage

# === Load environment variables ===
load_dotenv("/Users/hemasagarendluri1996/jira-rag-pipeline/.env")

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
os.environ['OPENAI_API_KEY'] = OPENAI_API_KEY
print("OpenAI API Key loaded.", OPENAI_API_KEY)
WEAVIATE_URL = os.getenv("WEAVIATE_URL")
WEAVIATE_API_KEY = os.getenv("WEAVIATE_API_KEY")
JIRA_COLLECTION_NAME = os.getenv("WEAVIATE_COLLECTION_NAME")

# === Setup LLM ===
llm = ChatOpenAI(openai_api_key=OPENAI_API_KEY, model="gpt-3.5-turbo", temperature=0)

# === Connect to Weaviate ===
client = weaviate.connect_to_weaviate_cloud(
    cluster_url=WEAVIATE_URL,
    auth_credentials=AuthApiKey(api_key=WEAVIATE_API_KEY),
)

if not client.is_ready():
    raise Exception("❌ Weaviate is not reachable")

print("✅ Connected to Weaviate RAG database.")
jira_collection = client.collections.get(JIRA_COLLECTION_NAME)

# === NLP Helpers with OpenAI ===
def clean_query(query: str) -> str:
    """Rephrase query to make it more precise"""
    try:
        prompt = f"Rephrase the following Jira search query into a clearer form:\n\n{query}"
        response = llm([HumanMessage(content=prompt)]).content
        return response.strip()
    except Exception:
        return query

def summarize_docs(docs: list) -> list:
    """Summarize each document using OpenAI"""
    summarized = []
    for d in docs:
        try:
            prompt = f"Summarize this Jira issue in one short sentence:\n{d}"
            response = llm([HumanMessage(content=prompt)]).content
            summarized.append(response.strip())
        except Exception:
            summarized.append(d)
    return summarized

def adapt_prompt(query: str, context: str) -> str:
    """Adapt instructions based on query intent"""
    if "bug" in query.lower():
        style = "Focus only on Bug issues and their statuses."
    elif "sprint" in query.lower():
        style = "Focus on sprint progress, remaining work, and completion."
    else:
        style = "Answer concisely using Jira issues."
    
    return f"""
You are an AI assistant answering questions about Jira issue data.
{style}

Context:
{context}

Question:
{query}

Provide a clear and concise answer based only on the above context.
"""

# === RAG Query Pipeline ===
def run_rag_query(query: str) -> dict:
    responses = {}

    try:
        # Step 1: Clean query
        cleaned_query = clean_query(query)
        print(f"🔍 Original query: {query}")
        print(f"✨ Cleaned query: {cleaned_query}")

        # Step 2: Retrieve top docs
        try:
            context_result = jira_collection.query.bm25(
                query=cleaned_query,
                limit=10,
                return_metadata=wq.MetadataQuery(score=True)
            )
        except Exception as e:
            error_msg = f"Error retrieving documents from Weaviate: {e}"
            print(error_msg)
            responses[cleaned_query] = error_msg
            return {"responses": responses}

        # Step 3: Format docs
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

        # Step 4: Summarize docs
        docs = summarize_docs(docs)
        context_text = "\n\n".join(docs)

        # Step 5: Adaptive prompt
        prompt_template = adapt_prompt(cleaned_query, context_text)

        # Step 6: Ask OpenAI
        try:
            answer = llm([HumanMessage(content=prompt_template)]).content
        except Exception as e:
            error_msg = f"Error generating answer from LLM: {e}"
            print(error_msg)
            responses[cleaned_query] = error_msg
            return {"responses": responses}

        responses[cleaned_query] = answer
        print("answer:", answer)

    except Exception as e:
        error_msg = f"Unexpected error: {e}"
        print(error_msg)
        responses[query] = error_msg

    return {"responses": responses}
