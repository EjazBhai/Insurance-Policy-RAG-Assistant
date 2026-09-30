import os
from dotenv import load_dotenv

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")

RAW_DATA_DIR = "data/raw"
CHROMA_DIR = "chroma_db"
COLLECTION_NAME = "policies"

EMBEDDING_MODEL = "BAAI/bge-small-en-v1.5"
RERANK_MODEL = "cross-encoder/ms-marco-MiniLM-L-6-v2"
LLM_MODEL = "llama-3.3-70b-versatile"

CHUNK_SIZE = 800
CHUNK_OVERLAP = 100
TOP_K = 5
CANDIDATES = 20   # how many chunks to fetch before re-ranking