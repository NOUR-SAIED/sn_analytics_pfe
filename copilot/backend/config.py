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
# Ollama now has GPU passthrough (see docker-compose.yml `ollama` service -
# was previously undetected/unused despite the host having an RTX GPU, fixed
# 2026-08-27). `ollama ps` shows this model split 56%/44% CPU/GPU (a 5.1GB
# model doesn't fully fit in the ~3.2GB VRAM available, so it's partial
# offload, not full GPU), and a single inference call now completes in ~2.5s
# instead of the ~60-90s/step this comment used to document for CPU-only.
# 480s was sized for the old CPU-only path across a typical 3-5 step question
# (list_tables -> describe_table x1-2 -> run_sql -> final) - now generous
# headroom rather than a tight budget. Left unchanged rather than guessed
# down without re-timing a real multi-step question end to end.
AGENT_TIMEOUT_SECONDS = int(os.getenv("COPILOT_AGENT_TIMEOUT_SECONDS", "480"))
