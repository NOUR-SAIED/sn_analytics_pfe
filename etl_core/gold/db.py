"""
Database connection utility for the gold layer.

Reuses the same environment-variable connection pattern as
etl_core.loaders.postgres_silver and postgres_jsonb.
"""

import os
from typing import Optional

import psycopg2
import psycopg2.extras
from psycopg2 import sql


def get_connection(
    host: Optional[str] = None,
    port: Optional[int] = None,
    database: Optional[str] = None,
    user: Optional[str] = None,
    password: Optional[str] = None,
):
    """Create a PostgreSQL connection using env vars as defaults."""
    return psycopg2.connect(
        host=host or os.getenv("POSTGRES_CONN_HOST", "postgres"),
        port=port or int(os.getenv("POSTGRES_CONN_PORT", "5432")),
        dbname=database or os.getenv("ELT_DATABASE_NAME"),
        user=user or os.getenv("ELT_DATABASE_USERNAME", "elt_user"),
        password=password or os.getenv("ELT_DATABASE_PASSWORD"),
    )


def execute(sql_text: str, autocommit: bool = True) -> None:
    """Execute a SQL string against the ELT database."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            statements = [s.strip() for s in sql_text.split(";") if s.strip()]
            for stmt in statements:
                cur.execute(stmt)
        if autocommit:
            conn.commit()


def execute_many(sql_text: str, params_list: list[tuple]) -> None:
    """Execute a parameterized SQL statement with many value tuples."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            for params in params_list:
                cur.execute(sql_text, params)
        conn.commit()


def fetch_all(sql_text: str) -> list[dict]:
    """Execute a query and return rows as dicts."""
    with get_connection() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(sql_text)
            return cur.fetchall()
