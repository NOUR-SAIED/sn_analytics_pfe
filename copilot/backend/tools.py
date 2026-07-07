"""Utility tools for the copilot backend.

All public functions return plain strings. On success they return JSON strings
or plain text. On failure they return a readable error string instead of raising.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import psycopg2
from psycopg2 import sql
from langchain_core.tools import tool

from .config import DATABASE_URL_READONLY, SCHEMA_DOCS_DIR


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
