# Example local settings (committed). Copy to local_settings.py and adjust.
# All secrets are read from environment variables (.env); never hardcode them here.
import os
from pathlib import Path

# Build paths inside the project like this: BASE_DIR / 'subdir'.
# We redefine BASE_DIR here to use it in custom paths
# BASE_DIR = Path(__file__).resolve().parent.parent
BASE_DIR = Path(__file__).resolve().parent
# ==========================================
# 1. SECURITY & DEBUG CONFIGURATIONS
# ==========================================
# Defaults to False. Set DJANGO_DEBUG=1 in .env for local development.
DEBUG = os.getenv("DJANGO_DEBUG", "0") == "1"

# Keep the secret key used in production secret!
SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "")

if not SECRET_KEY:
    if DEBUG:
        SECRET_KEY = "dev-only-insecure-key"
    else:
        raise RuntimeError("❌ DJANGO_SECRET_KEY is not set")

ALLOWED_HOSTS = [h.strip() for h in os.getenv("DJANGO_ALLOWED_HOSTS", "127.0.0.1,localhost").split(",") if h.strip()]

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': os.getenv('DB_NAME', 'genai_chat_db'),
        'USER': os.getenv('DB_USER', 'genai_user'),
        'PASSWORD': os.getenv('DB_PASSWORD', 'your_password_here'),
        'HOST': os.getenv('DB_HOST', 'localhost'),
        'PORT': os.getenv('DB_PORT', '3306'),
    }
}

# ==========================================
# 2. LLM CONFIGURATION (Ollama / OpenAI)
# ==========================================
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "ollama")
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2:1b")
OLLAMA_MODEL_FAST = os.getenv("OLLAMA_MODEL_FAST", "qwen2.5:1.5b")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL")

SYSTEM_PROMPT = (
    "You are a helpful AI assistant named 'GenAI'. "
    "You are NOT the user; you are talking with a human user. "
    "If the user tells you their name or personal details, remember them and use them correctly. "
    "Answer math questions accurately. Use markdown for formatting."
)

# ==========================================
# 3. RAG (RETRIEVAL-AUGMENTED GENERATION) CONFIG
# ==========================================
# Absolute path for ChromaDB, independent of the working directory
RAG_PATH = BASE_DIR / "rag" / "rag_data" / "chroma_db"
OLLAMA_EMBED_URL = os.getenv("OLLAMA_EMBED_URL", "http://localhost:11434/api/embeddings")
EMBED_MODEL = os.getenv("EMBED_MODEL", "nomic-embed-text")

# Cosine distance cutoff: results farther than this are considered irrelevant
RAG_MAX_DISTANCE = float(os.getenv("RAG_MAX_DISTANCE", "0.55"))
RAG_MAX_UPLOAD_BYTES = int(os.getenv("RAG_MAX_UPLOAD_BYTES", str(10 * 1024 * 1024)))  # 10 MB

# ==========================================
# 4. RATE LIMITING CONFIG
# ==========================================
CHAT_RATE_LIMIT = int(os.getenv("CHAT_RATE_LIMIT", "20"))
RATE_WINDOW_SECONDS = int(os.getenv("RATE_WINDOW_SECONDS", "60"))
UPLOAD_RATE_LIMIT = int(os.getenv("UPLOAD_RATE_LIMIT", "5"))

# Only enable behind a reverse proxy YOU control; otherwise clients can spoof X-Forwarded-For.
TRUST_X_FORWARDED_FOR = os.getenv("TRUST_X_FORWARDED_FOR", "0") == "1"

# ==========================================
# 5. VALIDATIONS
# ==========================================
if LLM_PROVIDER == "openai" and not OPENAI_API_KEY:
    raise RuntimeError("❌ LLM_PROVIDER=openai but OPENAI_API_KEY is not set")

if LLM_PROVIDER not in ("ollama", "openai"):
    raise RuntimeError(f"❌ Unknown LLM_PROVIDER='{LLM_PROVIDER}'")


# Redis Configuration
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
REDIS_DB = int(os.getenv("REDIS_DB", "0"))

# Tavily Key
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY", "")

# Redis Cache Configuration
CACHE_TTL = int(os.getenv("CACHE_TTL", "86400")) # 24 hours
SIMILARITY_THRESHOLD = float(os.getenv("SIMILARITY_THRESHOLD", "0.95")) # 95% match