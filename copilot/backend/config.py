"""Backend configuration for copilot tools."""

from pathlib import Path
import os


BACKEND_DIR = Path(__file__).resolve().parent
SCHEMA_DOCS_DIR = BACKEND_DIR / "schema_docs"
DATABASE_URL_READONLY = os.getenv("DATABASE_URL_READONLY", "")
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://ollama:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5-coder:7b-instruct-q4_K_M")

# Comma-separated list of origins allowed to call this API.
COPILOT_ALLOWED_ORIGINS = [
    origin.strip()
    for origin in os.getenv("COPILOT_ALLOWED_ORIGINS", "http://localhost:3000").split(",")
    if origin.strip()
]

# SQLite checkpoint DB backing per-thread conversation memory. Mounted onto a
# named volume in docker-compose.yml so history survives container restarts.
STATE_DIR = Path(os.getenv("COPILOT_STATE_DIR", "/app/.state"))
STATE_DB_PATH = STATE_DIR / "checkpoints.sqlite"

# Overall wall-clock budget for one /api/ask call, regardless of step count.
# This model runs on CPU-only Ollama in local dev (~60-90s per inference step,
# confirmed via `ollama ps` showing 100% CPU processor), and a typical question
# needs 3-5 steps (list_tables -> describe_table x1-2 -> run_sql -> final), so
# the budget needs real headroom rather than a short "safety" timeout.
AGENT_TIMEOUT_SECONDS = int(os.getenv("COPILOT_AGENT_TIMEOUT_SECONDS", "480"))
