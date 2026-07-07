"""Custom ReAct agent that handles Ollama models which output tool calls as JSON text."""

from __future__ import annotations

import json
import re

from langchain_ollama import ChatOllama
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage, SystemMessage

from .config import OLLAMA_MODEL, OLLAMA_URL, SCHEMA_DOCS_DIR
from .tools import describe_table, list_tables, run_sql, sample_values

_MAX_STEPS = 10

_TOOLS = [list_tables, describe_table, sample_values, run_sql]
_TOOL_MAP = {t.name: t for t in _TOOLS}

_TOOL_DEFS = "\n\n".join(
    f"## {t.name}\n{t.description}\n\nInput schema:\n{json.dumps(t.args_schema.schema() if t.args_schema else {}, indent=2)}"
    for t in _TOOLS
)


def _load_schema_docs() -> str:
    parts: list[str] = []
    for path in sorted(SCHEMA_DOCS_DIR.glob("*.md")):
        if path.name.lower() == "readme.md":
            continue
        parts.append(path.read_text(encoding="utf-8").strip())
    return "\n\n---\n\n".join(parts)


_SYSTEM_PROMPT = f"""You are a senior analytics engineer. You have access to the following tools:

{_TOOL_DEFS}

Here is the full schema documentation for every gold table:

{_load_schema_docs()}

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

_llm = ChatOllama(
    model=OLLAMA_MODEL,
    base_url=OLLAMA_URL,
    temperature=0,
    timeout=120,
)


def _parse_tool_call(text: str) -> dict | None:
    m = re.search(r"TOOL_CALL:\s*(\{.*\})", text, re.DOTALL)
    if not m:
        return None
    try:
        return json.loads(m.group(1))
    except json.JSONDecodeError:
        return None


def run_agent(question: str) -> dict:
    messages: list = [SystemMessage(content=_SYSTEM_PROMPT), HumanMessage(content=question)]
    trace: list[dict] = []

    for step in range(_MAX_STEPS):
        response = _llm.invoke(messages)
        content = response.content.strip()

        tc = _parse_tool_call(content)
        if tc is None:
            return {"answer": content, "trace": trace}

        tool_name = tc.get("name", "")
        tool_args = tc.get("arguments", {})
        tool_fn = _TOOL_MAP.get(tool_name)
        if tool_fn is None:
            result = f"Unknown tool: {tool_name}"
        else:
            try:
                result = tool_fn.invoke(tool_args)
            except Exception as e:
                result = f"Error calling {tool_name}: {e}"

        trace.append({"tool": tool_name, "arguments": tool_args, "result": str(result)})
        messages.append(AIMessage(content=content))
        messages.append(ToolMessage(content=str(result), tool_call_id=tool_name))

    return {"error": "Agent reached maximum steps without a final answer.", "trace": trace}
