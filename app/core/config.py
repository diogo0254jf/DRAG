import os

from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "")
OLLAMA_CHAT_MODEL = os.getenv("OLLAMA_CHAT_MODEL", "llama3.1")
OLLAMA_EMBED_MODEL = os.getenv("OLLAMA_EMBED_MODEL", "nomic-embed-text")
DOCS_DIR = os.getenv("DOCS_DIR", "docs")
FAISS_PATH = os.getenv("FAISS_PATH", "faiss_index")
RAG_K = int(os.getenv("RAG_K", "4"))
PROMPT_SEED_PATH = os.getenv("PROMPT_SEED_PATH", "prompts.seed.json")
HISTORY_MAX_CHARS = int(os.getenv("HISTORY_MAX_CHARS", "4000"))
HISTORY_MAX_MESSAGES = int(os.getenv("HISTORY_MAX_MESSAGES", "30"))
MEMORY_UPDATE_EVERY = int(os.getenv("MEMORY_UPDATE_EVERY", "6"))

MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "minio:9000")
MINIO_ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY", "minioadmin")
MINIO_SECRET_KEY = os.getenv("MINIO_SECRET_KEY", "minioadmin")
MINIO_BUCKET = os.getenv("MINIO_BUCKET", "documents")
MINIO_SECURE = os.getenv("MINIO_SECURE", "false").lower() == "true"
HATCHET_CLIENT_TOKEN = os.getenv("HATCHET_CLIENT_TOKEN", "")
