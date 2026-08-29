"""Utility tools for the copilot backend.

All public functions return plain strings. On success they return JSON strings
or plain text. On failure they return a readable error string instead of raising.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import psycopg2
import requests
from psycopg2 import sql
from langchain_core.tools import tool

from .config import CUBE_URL, DATABASE_URL_READONLY, SCHEMA_DOCS_DIR


_FORBIDDEN_SQL_RE = re.compile(
	r"\b(insert|update|delete|drop|alter|truncate)\b|;\s*\S",
	re.IGNORECASE,
)
_SELECT_START_RE = re.compile(r"^\s*(select|with)\b", re.IGNORECASE)
_BACKTICK_FIELD_RE = re.compile(r"`([A-Za-z_][A-Za-z0-9_]*)`")


def _schema_doc_paths() -> list[Path]:
	if not SCHEMA_DOCS_DIR.exists():
		return []
	return sorted(
		path for path in SCHEMA_DOCS_DIR.glob("*.md") if path.name.lower() != "readme.md"
	)


def _table_names() -> list[str]:
	return [path.stem for path in _schema_doc_paths()]


def _load_schema_doc(table_name: str) -> str | None:
	doc_path = SCHEMA_DOCS_DIR / f"{table_name}.md"
	if not doc_path.exists() or not doc_path.is_file():
		return None
	return doc_path.read_text(encoding="utf-8")


def _documented_columns(table_name: str) -> set[str]:
	content = _load_schema_doc(table_name)
	if content is None:
		return set()

	columns: set[str] = set()
	for line in content.splitlines():
		stripped = line.lstrip()
		if not stripped.startswith("-"):
			continue
		for match in _BACKTICK_FIELD_RE.findall(line):
			columns.add(match)
	return columns


def _sample_value_connection() -> psycopg2.extensions.connection:
	if not DATABASE_URL_READONLY:
		raise ValueError("DATABASE_URL_READONLY is not set.")
	return psycopg2.connect(DATABASE_URL_READONLY)


def _qualify_gold_tables(query: str) -> str:
	qualified_query = query
	for table_name in sorted(_table_names(), key=len, reverse=True):
		pattern = re.compile(rf"(?<!\.)\b{re.escape(table_name)}\b")
		qualified_query = pattern.sub(f"gold.{table_name}", qualified_query)
	return qualified_query


def _fetch_cube_meta() -> dict:
	"""GET the Cube semantic layer's self-describing catalog. Not cached - this
	is a fast same-network call, and always-fresh beats a stale cache if the
	cube model changes (correctness over a micro-optimization here)."""
	resp = requests.get(f"{CUBE_URL}/cubejs-api/v1/meta", timeout=10)
	resp.raise_for_status()
	return resp.json()


def _compact_catalog(meta: dict) -> list[dict]:
	"""Cube's raw /meta payload carries a lot of frontend-oriented fields
	(drillMembers, isVisible, aggType, ...) that only add tokens without
	helping the model pick the right member name. Slim it to what the agent
	actually needs: the exact name to reference, and why it exists. Kept as
	structured data (not text) since _valid_member_names also consumes it -
	list_cube_metrics is the one place that renders it down to text, since
	only that path is actually going into the model's limited context."""

	def _slim(members: list[dict]) -> list[dict]:
		out = []
		for m in members:
			entry = {"name": m["name"], "type": m.get("type")}
			if m.get("description"):
				entry["description"] = m["description"]
			if m.get("format"):
				entry["format"] = m["format"]
			out.append(entry)
		return out

	return [
		{
			"cube": c["name"],
			"description": c.get("description"),
			"measures": _slim(c.get("measures", [])),
			"dimensions": _slim(c.get("dimensions", [])),
		}
		for c in meta.get("cubes", [])
	]


def _valid_member_names(catalog: list[dict]) -> set[str]:
	names: set[str] = set()
	for c in catalog:
		names.update(m["name"] for m in c["measures"])
		names.update(m["name"] for m in c["dimensions"])
	return names


def _one_line(text: str, max_len: int = 130) -> str:
	"""Collapse a (possibly multi-sentence) description to one short line.
	This model runs with a 4096-token context window (auto-sized from the
	host's 4GB VRAM - see docker-compose.yml `ollama` service); the full
	pretty-printed JSON catalog measured ~1700 tokens on its own, over 40% of
	the entire budget for one tool result. That's what was actually causing
	the model to run out of room and emit truncated, unparseable JSON on its
	*next* turn - not a flaw in the model's reasoning. Plain text with short
	descriptions and no redundant fields (the raw catalog's "title" is just
	a title-cased copy of "name" - dropped entirely, it added tokens with no
	information the model didn't already have) is a large, direct fix.
	"""
	one_line = " ".join(text.split())
	return one_line if len(one_line) <= max_len else one_line[: max_len - 1] + "…"


def _format_catalog_text(catalog: list[dict]) -> str:
	lines: list[str] = []
	for c in catalog:
		lines.append(f"CUBE {c['cube']}" + (f" - {_one_line(c['description'])}" if c.get("description") else ""))
		lines.append("  measures:")
		for m in c["measures"]:
			desc = f" — {_one_line(m['description'])}" if m.get("description") else ""
			lines.append(f"    {m['name']} ({m['type']}){desc}")
		lines.append("  dimensions:")
		for d in c["dimensions"]:
			desc = f" — {_one_line(d['description'])}" if d.get("description") else ""
			lines.append(f"    {d['name']} ({d['type']}){desc}")
	return "\n".join(lines)


@tool
def list_cube_metrics() -> str:
	"""List every measure and dimension available through the Cube semantic layer, each with its exact name and a one-line description. ALWAYS call this before run_cube_query if you are not already sure of the exact member names - there are no joins to write, Cube already resolved them; you only need the right names."""
	try:
		return _format_catalog_text(_compact_catalog(_fetch_cube_meta()))
	except requests.RequestException as exc:
		return f"Error reaching Cube: {exc}"
	except Exception as exc:  # noqa: BLE001 - return readable error text
		return f"Error listing Cube metrics: {exc}"


@tool
def run_cube_query(
	measures: list[str] | None = None,
	dimensions: list[str] | None = None,
	filters: list[dict] | None = None,
	time_dimensions: list[dict] | None = None,
	limit: int = 500,
) -> str:
	"""Run a structured query against the Cube semantic layer - the preferred way to answer any question about cases, agents, terminals, or SLAs. No SQL, no joins to write; Cube already resolved every join.

	measures: e.g. ["Cases.total_cases", "Cases.response_sla_breach_rate"]
	dimensions: e.g. ["Cases.assigned_to_agent_name"] - group-by fields. To see the
	  distinct values of one dimension (like sampling a column), query it alone
	  with no measures.
	filters: e.g. [{"member": "Cases.priority_label", "operator": "equals", "values": ["1 - Critical"]}]
	  operator is one of: equals, notEquals, contains, notContains, gt, gte, lt, lte, set, notSet
	time_dimensions: e.g. [{"dimension": "Cases.opened_date", "granularity": "month"}] -
	  use this (not a plain filter) to bucket a time field by day/week/month/quarter/year,
	  or to restrict a date range via {"dimension": "...", "dateRange": ["2025-01-01", "2025-12-31"]}

	Call list_cube_metrics first if you are not sure of the exact member names -
	an unrecognized name is rejected before Cube is even called.
	"""
	try:
		measures = measures or []
		dimensions = dimensions or []
		filters = filters or []
		time_dimensions = time_dimensions or []

		if not measures and not dimensions:
			return "Invalid query: provide at least one measure or one dimension."

		# Deterministic pre-flight check - no LLM call spent finding out a
		# hallucinated member name was wrong. Cheap, same-network, always-fresh.
		valid_names = _valid_member_names(_compact_catalog(_fetch_cube_meta()))
		requested = set(measures) | set(dimensions)
		requested.update(f["member"] for f in filters if "member" in f)
		requested.update(td["dimension"] for td in time_dimensions if "dimension" in td)
		unknown = requested - valid_names
		if unknown:
			return (
				f"Unknown Cube member(s): {sorted(unknown)}. "
				"Call list_cube_metrics to see the exact available names."
			)

		query = {
			"measures": measures,
			"dimensions": dimensions,
			"filters": filters,
			"timeDimensions": time_dimensions,
			"limit": min(limit, 5000),
		}
		resp = requests.post(f"{CUBE_URL}/cubejs-api/v1/load", json={"query": query}, timeout=15)
		if resp.status_code >= 400:
			try:
				err = resp.json().get("error", resp.text)
			except ValueError:
				err = resp.text
			return f"Cube rejected the query: {err}"

		return json.dumps(resp.json().get("data", []), default=str)
	except requests.RequestException as exc:
		return f"Error reaching Cube: {exc}"
	except Exception as exc:  # noqa: BLE001 - return readable error text
		return f"Error running Cube query: {exc}"


# ─────────────────────────────────────────────────────────────────────────────
# Fallback tools - raw SQL against gold.* and its hand-maintained markdown
# docs. Cube only models `fact_case` today (see cube/model/cubes/cases.yml);
# nothing built on the SCD2 snapshot or anything outside that grain exists as
# a cube yet. Kept available for that gap, not as the first choice - the
# system prompt in agent.py steers the model to try the Cube tools above
# first, since those can't misuse a role-playing join the way hand-written
# SQL can.
# ─────────────────────────────────────────────────────────────────────────────


@tool
def list_tables() -> str:
	"""List the available gold schema markdown files under schema_docs/ and use this to discover which gold tables exist."""
	try:
		return json.dumps(_table_names())
	except Exception as exc:  # noqa: BLE001 - return readable error text
		return f"Error listing tables: {exc}"


@tool
def describe_table(table_name: str) -> str:
	"""Read and return the markdown schema document for one gold table; use this before writing SQL whenever you need the table grain, fields, or join keys."""
	try:
		content = _load_schema_doc(table_name)
		if content is None:
			return "Table not found. Available tables: " + list_tables.invoke({})
		return content
	except Exception as exc:  # noqa: BLE001 - return readable error text
		return f"Error describing table: {exc}"


@tool
def sample_values(table_name: str, column_name: str) -> str:
	"""Fetch up to 10 distinct values from a documented gold table column; use this when code-like values such as status, priority, or labels are unclear."""
	try:
		available_tables = set(_table_names())
		if table_name not in available_tables:
			return "Table not found. Available tables: " + list_tables.invoke({})

		allowed_columns = _documented_columns(table_name)
		if column_name not in allowed_columns:
			return (
				f"Column not found for {table_name}. Available columns: "
				+ json.dumps(sorted(allowed_columns))
			)

		query = sql.SQL("SELECT DISTINCT {column} FROM gold.{table} LIMIT 10").format(
			column=sql.Identifier(column_name),
			table=sql.Identifier(table_name),
		)

		with _sample_value_connection() as conn:
			with conn.cursor() as cur:
				cur.execute(query)
				values = [row[0] for row in cur.fetchall()]
		return json.dumps(values, default=str)
	except Exception as exc:  # noqa: BLE001 - return readable error text
		return f"Error sampling values: {exc}"


@tool
def run_sql(query: str) -> str:
	"""Validate and run a single read-only SELECT query against the warehouse; use this only after you are confident in the table structure and joins."""
	try:
		if not _SELECT_START_RE.search(query):
			return "Invalid query: only SELECT statements are allowed."
		if _FORBIDDEN_SQL_RE.search(query):
			return "Invalid query: destructive or multi-statement SQL is not allowed."

		cleaned_query = query.strip()
		if cleaned_query.endswith(";"):
			cleaned_query = cleaned_query[:-1].rstrip()
		cleaned_query = _qualify_gold_tables(cleaned_query)

		if not re.search(r"\blimit\b", cleaned_query, re.IGNORECASE):
			cleaned_query = f"{cleaned_query} LIMIT 200"

		with _sample_value_connection() as conn:
			with conn.cursor() as cur:
				cur.execute("SET statement_timeout TO 10000")
				cur.execute(cleaned_query)

				if cur.description is None:
					return json.dumps([])

				columns = [column[0] for column in cur.description]
				rows = [dict(zip(columns, row)) for row in cur.fetchall()]
		return json.dumps(rows, default=str)
	except Exception as exc:  # noqa: BLE001 - return readable error text
		return str(exc)
