"""Backend configuration for copilot tools."""

from pathlib import Path
import os


BACKEND_DIR = Path(__file__).resolve().parent
SCHEMA_DOCS_DIR = BACKEND_DIR / "schema_docs"
DATABASE_URL_READONLY = os.getenv("DATABASE_URL_READONLY", "")
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://ollama:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5-coder:7b-instruct-q4_K_M")
