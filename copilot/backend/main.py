"""FastAPI entrypoint for the copilot backend."""

from __future__ import annotations

import json
import queue
import threading
import time
import uuid

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from . import agent
from .config import AGENT_TIMEOUT_SECONDS, COPILOT_ALLOWED_ORIGINS


class AskRequest(BaseModel):
    question: str
    thread_id: str | None = None


app = FastAPI(title="Copilot Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=COPILOT_ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

_SENTINEL = object()


def _sse_event(event: dict) -> str:
    return f"event: {event['type']}\ndata: {json.dumps(event)}\n\n"


def _stream_with_timeout(question: str, thread_id: str):
    """Run agent.stream_agent on a worker thread, bounded by an overall wall-clock deadline.

    stream_agent() itself blocks on synchronous Ollama/DB calls, so it's run off the
    main thread and polled through a queue rather than iterated directly — that's
    what lets us enforce a total time budget instead of the old fixed step count,
    which only bounded the number of turns, not how long they could each take.
    """
    q: queue.Queue = queue.Queue()

    def _worker():
        try:
            for event in agent.stream_agent(question, thread_id):
                q.put(event)
        except Exception as exc:  # noqa: BLE001 - surfaced to the client as an SSE error event
            q.put({"type": "error", "error": f"Unexpected backend error: {exc}"})
        finally:
            q.put(_SENTINEL)

    threading.Thread(target=_worker, daemon=True).start()

    deadline = time.monotonic() + AGENT_TIMEOUT_SECONDS
    while True:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            yield _sse_event({"type": "error", "error": "Agent timed out."})
            return
        try:
            item = q.get(timeout=remaining)
        except queue.Empty:
            yield _sse_event({"type": "error", "error": "Agent timed out."})
            return
        if item is _SENTINEL:
            return
        yield _sse_event(item)


@app.post("/api/ask")
def ask(request: AskRequest) -> StreamingResponse:
    """Stream the agent's tool calls/results and final answer as Server-Sent Events.

    A thread_id groups turns into one remembered conversation; the client should
    generate one per chat session and resend it on every follow-up question.
    """
    thread_id = request.thread_id or str(uuid.uuid4())
    return StreamingResponse(
        _stream_with_timeout(request.question, thread_id),
        media_type="text/event-stream",
        headers={"X-Thread-Id": thread_id},
    )
