"""AnimaLearn — Centralized Settings"""
from __future__ import annotations
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

ROOT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT_DIR / "data" / "references"
OUTPUT_DIR = ROOT_DIR / "outputs"
VIDEO_DIR = OUTPUT_DIR / "videos"
LOG_FILE = ROOT_DIR / os.getenv("LOG_FILE", "outputs/trace_logs.jsonl")
CONFIG_DIR = ROOT_DIR / "config"
VIDEO_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# LLM: Groq (free, no credit card — https://console.groq.com/)
GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL: str = "llama-3.3-70b-versatile"
GROQ_BASE_URL: str = "https://api.groq.com/openai/v1"

# Embeddings: local sentence-transformers (no API key needed)
EMBEDDING_MODEL_NAME: str = "all-MiniLM-L6-v2"
EMBEDDING_DIMENSION: int = 384

# Vector Store
QDRANT_URL: str = os.getenv("QDRANT_URL", "http://localhost:6333")
QDRANT_API_KEY: str = os.getenv("QDRANT_API_KEY", "")
QDRANT_COLLECTION: str = os.getenv("QDRANT_COLLECTION", "animalearn_references")

# Animation & Avatar
RUNWAY_API_KEY: str = os.getenv("RUNWAY_API_KEY", "")
DID_API_KEY: str = os.getenv("DID_API_KEY", "")

# Flags
MOCK_MODE: bool = os.getenv("MOCK_MODE", "true").lower() == "true"
LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")

# Guard-rails
MAX_TOOL_CALLS_PER_AGENT: int = 15
MAX_STEPS: int = 30
RAG_TOP_K: int = 5
CHUNK_SIZE: int = 500
CHUNK_OVERLAP: int = 50
DEFAULT_DURATION_MINUTES: int = 1
WORDS_PER_MINUTE: int = 150
