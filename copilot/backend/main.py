"""FastAPI entrypoint for the copilot backend."""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from . import agent


class AskRequest(BaseModel):
	question: str


app = FastAPI(title="Copilot Backend")

app.add_middleware(
	CORSMiddleware,
	allow_origins=["http://localhost:3000"],
	allow_credentials=True,
	allow_methods=["*"],
	allow_headers=["*"],
)


@app.post("/api/ask")
def ask(request: AskRequest) -> dict[str, Any]:
	"""Pass a question to the agent and return its JSON result."""
	try:
		return agent.run_agent(request.question)
	except Exception as exc:  # noqa: BLE001 - return a readable error payload
		return {"error": f"Unexpected backend error: {exc}"}

