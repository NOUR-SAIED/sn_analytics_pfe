"""LangGraph agent for the copilot backend.

Ollama's qwen2.5-coder does not reliably populate structured `AIMessage.tool_calls`
even when given a native `tools` schema (verified empirically against the running
model: it just writes the call as JSON text into `message.content`). So this module
keeps the working "ask the model to emit `TOOL_CALL: {...}` on its own line and parse
it" convention, but runs it inside a real LangGraph `StateGraph` instead of a hand-
rolled step counter — that's what gets us streaming and per-thread memory for free.
"""

from __future__ import annotations

import json
import re
from typing import Any, Iterator

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_ollama import ChatOllama
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.errors import GraphRecursionError
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import MessagesState
from pydantic import ValidationError

from .config import OLLAMA_MODEL, OLLAMA_URL, STATE_DB_PATH
from .tools import describe_table, list_tables, run_sql, sample_values

RECURSION_LIMIT = 20

_TOOLS = [list_tables, describe_table, sample_values, run_sql]
_TOOL_MAP = {t.name: t for t in _TOOLS}

_TOOL_DEFS = "\n\n".join(
    f"## {t.name}\n{t.description}\n\nInput schema:\n"
    f"{json.dumps(t.args_schema.model_json_schema() if t.args_schema else {}, indent=2)}"
    for t in _TOOLS
)

_SYSTEM_PROMPT = f"""You are a senior analytics engineer. You have access to the following tools:

{_TOOL_DEFS}

Rules:
- Always start by exploring — call `list_tables` first, then `describe_table` on relevant tables before writing SQL.
- When you need to call a tool, respond with EXACTLY this JSON format on its own line:
  TOOL_CALL: {{"name": "<tool_name>", "arguments": {{...}}}}
- After you receive the tool result, continue the conversation.
- When you have enough information to answer, provide a clear concise answer in plain English.
- Never make up tool results — always call the tool.
- Keep SQL queries simple and focused. Use fully-qualified table names (e.g. `gold.fact_case`).
- If you get stuck, explain what is missing.
"""

_TOOL_CALL_RE = re.compile(r"TOOL_CALL:\s*(\{.*\})", re.DOTALL)

_llm = ChatOllama(
    model=OLLAMA_MODEL,
    base_url=OLLAMA_URL,
    temperature=0,
    timeout=120,
)


def _parse_tool_call(text: str) -> dict | None:
    m = _TOOL_CALL_RE.search(text or "")
    if not m:
        return None
    try:
        return json.loads(m.group(1))
    except json.JSONDecodeError:
        return None


def _call_model(state: MessagesState) -> dict:
    messages = [SystemMessage(content=_SYSTEM_PROMPT), *state["messages"]]
    response = _llm.invoke(messages)
    return {"messages": [response]}


def _route_after_model(state: MessagesState) -> str:
    last = state["messages"][-1]
    if isinstance(last, AIMessage) and _parse_tool_call(last.content):
        return "call_tool"
    return END


def _previous_tool_call(messages: list) -> dict | None:
    """The (name, arguments) of the tool call before the current one, if any.

    Message layout is [..., AIMessage(call N-1), ToolMessage(result N-1), AIMessage(call N)],
    so the prior call sits two messages back from the current (last) one.
    """
    if len(messages) < 3:
        return None
    prev = messages[-3]
    if isinstance(prev, AIMessage):
        return _parse_tool_call(prev.content)
    return None


def _call_tool(state: MessagesState) -> dict:
    messages = state["messages"]
    last = messages[-1]
    tc = _parse_tool_call(last.content) or {}
    tool_name = tc.get("name", "")
    tool_args = tc.get("arguments", {})

    previous = _previous_tool_call(messages)
    if previous and previous.get("name") == tool_name and previous.get("arguments", {}) == tool_args:
        # The model just repeated its immediately preceding call verbatim — nothing about
        # the world changed since then, so re-running it would only reproduce the same
        # result (or error) again. Left unchecked, a model that doesn't know how to
        # recover from a failed query will do this until it burns the whole step/time
        # budget. Block the repeat and push it to try something different instead.
        result = (
            "You already made this exact tool call and it did not help — repeating it "
            "verbatim will not produce a different result. Try a materially different "
            "query or table, or if you're stuck, explain what's missing instead of retrying."
        )
    else:
        tool_fn = _TOOL_MAP.get(tool_name)
        if tool_fn is None:
            result = f"Unknown tool: {tool_name}"
        else:
            try:
                if tool_fn.args_schema is not None:
                    tool_fn.args_schema(**tool_args)
                result = tool_fn.invoke(tool_args)
            except ValidationError as exc:
                result = f"Invalid arguments for {tool_name}: {exc}"
            except Exception as exc:  # noqa: BLE001 - surfaced to the model as a tool result
                result = f"Error calling {tool_name}: {exc}"

    return {
        "messages": [
            ToolMessage(content=str(result), name=tool_name, tool_call_id=tool_name)
        ]
    }


STATE_DB_PATH.parent.mkdir(parents=True, exist_ok=True)

# `from_conn_string` is a @contextmanager: the connection is closed as soon as
# its generator is garbage-collected. Keeping this reference at module scope
# (not just the .__enter__() result) is what keeps it alive for the process's
# lifetime instead of closing itself moments after startup.
_checkpointer_cm = SqliteSaver.from_conn_string(str(STATE_DB_PATH))


def _build_graph():
    graph = StateGraph(MessagesState)
    graph.add_node("call_model", _call_model)
    graph.add_node("call_tool", _call_tool)
    graph.add_edge(START, "call_model")
    graph.add_conditional_edges(
        "call_model", _route_after_model, {"call_tool": "call_tool", END: END}
    )
    graph.add_edge("call_tool", "call_model")

    checkpointer = _checkpointer_cm.__enter__()
    return graph.compile(checkpointer=checkpointer)


_GRAPH = _build_graph()


def stream_agent(question: str, thread_id: str) -> Iterator[dict[str, Any]]:
    """Run the agent and yield one event per step.

    Event shapes: {"type": "tool_call", "name", "arguments"},
    {"type": "tool_result", "name", "result"}, {"type": "final", "answer"},
    {"type": "error", "error"}.
    """
    config = {
        "configurable": {"thread_id": thread_id},
        "recursion_limit": RECURSION_LIMIT,
    }
    inputs = {"messages": [HumanMessage(content=question)]}

    try:
        for update in _GRAPH.stream(inputs, config=config, stream_mode="updates"):
            for node_name, node_output in update.items():
                for msg in node_output.get("messages", []):
                    if node_name == "call_tool" and isinstance(msg, ToolMessage):
                        yield {"type": "tool_result", "name": msg.name, "result": msg.content}
                    elif node_name == "call_model" and isinstance(msg, AIMessage):
                        tc = _parse_tool_call(msg.content)
                        if tc:
                            yield {
                                "type": "tool_call",
                                "name": tc.get("name"),
                                "arguments": tc.get("arguments", {}),
                            }
                        else:
                            yield {"type": "final", "answer": msg.content}
    except GraphRecursionError:
        yield {"type": "error", "error": "Agent reached maximum steps without a final answer."}
    except Exception as exc:  # noqa: BLE001 - surfaced to the client as an SSE error event
        yield {"type": "error", "error": f"Unexpected agent error: {exc}"}
