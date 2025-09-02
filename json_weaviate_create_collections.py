import os
import weaviate
from dotenv import load_dotenv
from langchain.document_loaders import JSONLoader
from langchain.vectorstores import Weaviate
from langchain.embeddings import OpenAIEmbeddings
# from langchain_openai import OpenAIEmbeddings
from langchain_text_splitters import CharacterTextSplitter
# 🛠️ Step 1: Load environment variables
load_dotenv(".env")
WEAVIATE_URL = os.getenv("WEAVIATE_URL")
WEAVIATE_API_KEY = os.getenv("WEAVIATE_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# 🧩 Step 2: Load your JSONL data
loader = JSONLoader(
    file_path='combined/all_issues.jsonl',
    jq_schema=".",
    json_lines=True,
    text_content=False
)
docs = loader.load()
print("✅ Loaded documents:", len(docs))

text_splitter = CharacterTextSplitter(chunk_size=1000, chunk_overlap=0)
docs = text_splitter.split_documents(docs)

embeddings = OpenAIEmbeddings()