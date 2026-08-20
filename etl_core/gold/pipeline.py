"""
Gold layer pipeline orchestrator.

Runs the star schema build in dependency order:
  1. Schema + small dims (dim_agent, dim_assignment_group, dim_terminal)
  2. fact_case (depends on all dimensions)

dim_date is NOT built here anymore - it's now dbt's job
(dbt/models/gold/dim_date.sql, run via `dbt run --select dim_date`). This
is the first table migrated in the etl_core/gold -> dbt migration; see
docs/dbt_onboarding.md for the per-table log. The other four tables below
are still Python-owned pending their own migration.
"""

from .config import (
    GOLD_SCHEMA,
    AGENT_DIM_COLUMNS,
    ASSIGNMENT_GROUP_DIM_COLUMNS,
    TERMINAL_DIM_COLUMNS,
    FACT_CASE_COLUMNS,
)
from .loader import (
    create_gold_schema,
    create_gold_table,
    table_exists,
)
from . import dim_agent, dim_assignment_group, dim_terminal, fact_case


def build_all() -> dict[str, int]:
    """Execute the gold layer build for the still-Python-owned tables.

    Returns row counts per table. Does not touch gold.dim_date - run
    `dbt run --select dim_date` separately for that (see
    dags/sn_bronze_to_silver.py / docs/dbt_onboarding.md for how this is
    meant to be wired into Airflow once the rest of the migration lands).
    """
    counts: dict[str, int] = {}

    # ── 1. Schema and tables ────────────────────────────────────────────
    create_gold_schema()

    if not table_exists("dim_agent"):
        create_gold_table("dim_agent", AGENT_DIM_COLUMNS)
    if not table_exists("dim_assignment_group"):
        create_gold_table("dim_assignment_group", ASSIGNMENT_GROUP_DIM_COLUMNS)
    if not table_exists("dim_terminal"):
        create_gold_table("dim_terminal", TERMINAL_DIM_COLUMNS)
    if not table_exists("fact_case"):
        create_gold_table("fact_case", FACT_CASE_COLUMNS)

    # ── 2. Small dimensions (full refresh, independent) ─────────────────
    counts["dim_agent"] = dim_agent.build()
    counts["dim_assignment_group"] = dim_assignment_group.build()
    counts["dim_terminal"] = dim_terminal.build()

    # ── 3. Fact table (depends on all dimensions) ───────────────────────
    counts["fact_case"] = fact_case.build()

    return counts
