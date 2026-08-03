"""
Gold table lifecycle management.

Handles CREATE SCHEMA, CREATE TABLE, TRUNCATE, INSERT for gold objects.
"""

import logging
import os

from psycopg2 import sql

from .config import GOLD_SCHEMA, FACT_CASE_COLUMNS
from .db import get_connection

logger = logging.getLogger(__name__)

COPILOT_READER_ROLE = os.getenv("COPILOT_DB_USERNAME", "copilot_reader")


def create_gold_schema() -> None:
    """Create the gold schema if it does not exist."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                sql.SQL("CREATE SCHEMA IF NOT EXISTS {}").format(
                    sql.Identifier(GOLD_SCHEMA)
                )
            )
        conn.commit()


def create_gold_table(table_name: str, columns: list[str]) -> None:
    """Create a gold table from a list of column DDL definitions."""
    full_name = sql.SQL("{}.{}").format(
        sql.Identifier(GOLD_SCHEMA), sql.Identifier(table_name)
    )
    ddl = sql.SQL("CREATE TABLE IF NOT EXISTS {} (\n  {}\n)").format(
        full_name,
        sql.SQL(",\n  ").join(map(sql.SQL, columns)),
    )
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(ddl)
        conn.commit()


def truncate_gold_table(table_name: str) -> None:
    """Remove all rows from a gold table."""
    full_name = sql.SQL("{}.{}").format(
        sql.Identifier(GOLD_SCHEMA), sql.Identifier(table_name)
    )
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql.SQL("TRUNCATE TABLE {}").format(full_name))
        conn.commit()


def grant_copilot_reader_access() -> None:
    """Grant the read-only copilot role SELECT access to gold, including future tables.

    Runs as elt_user, the owner of the gold schema, so no superuser is needed.
    Idempotent — safe to call on every gold DAG run. If the role hasn't been
    provisioned yet (e.g. the copilot stack isn't deployed), this logs a
    warning instead of failing the pipeline.
    """
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT 1 FROM pg_roles WHERE rolname = %s", (COPILOT_READER_ROLE,))
            if cur.fetchone() is None:
                logger.warning(
                    "Role '%s' does not exist — skipping copilot read-only grants.",
                    COPILOT_READER_ROLE,
                )
                return

            cur.execute(
                sql.SQL("GRANT USAGE ON SCHEMA {} TO {}").format(
                    sql.Identifier(GOLD_SCHEMA), sql.Identifier(COPILOT_READER_ROLE)
                )
            )
            cur.execute(
                sql.SQL("GRANT SELECT ON ALL TABLES IN SCHEMA {} TO {}").format(
                    sql.Identifier(GOLD_SCHEMA), sql.Identifier(COPILOT_READER_ROLE)
                )
            )
            cur.execute(
                sql.SQL(
                    "ALTER DEFAULT PRIVILEGES IN SCHEMA {} GRANT SELECT ON TABLES TO {}"
                ).format(sql.Identifier(GOLD_SCHEMA), sql.Identifier(COPILOT_READER_ROLE))
            )
        conn.commit()


def table_exists(table_name: str) -> bool:
    """Check if a gold table already exists."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT EXISTS (
                    SELECT 1 FROM information_schema.tables
                    WHERE table_schema = %s AND table_name = %s
                )
                """,
                (GOLD_SCHEMA, table_name),
            )
            return cur.fetchone()[0]
