"""
Gold schema/grants management.

create_gold_table, truncate_gold_table, and table_exists used to live
here too, for the Python-built gold tables. Removed now that all 5 gold
tables (dim_date, dim_agent, dim_assignment_group, dim_terminal,
fact_case) are built by dbt (see docs/dbt_onboarding.md) - dbt's `table`
materialization creates/replaces its own tables and their target schema
automatically, so none of that DDL management is needed from Python
anymore. What's left here is genuinely still Python/Airflow's job: making
sure the schema exists before dbt's first-ever run on a fresh environment,
and granting the read-only copilot role access - neither is a dbt concern.
"""

import logging
import os

from psycopg2 import sql

from .config import GOLD_SCHEMA
from .db import get_connection

logger = logging.getLogger(__name__)

COPILOT_READER_ROLE = os.getenv("COPILOT_DB_USERNAME", "copilot_reader")


def create_gold_schema() -> None:
    """Create the gold schema if it does not exist.

    Belt-and-suspenders: dbt also creates the schema automatically on its
    first run, but grant_copilot_reader_access() needs the schema to
    already exist (GRANT USAGE ON SCHEMA fails on a schema that isn't
    there yet), so this is called before it as a safety net.
    """
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                sql.SQL("CREATE SCHEMA IF NOT EXISTS {}").format(
                    sql.Identifier(GOLD_SCHEMA)
                )
            )
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
