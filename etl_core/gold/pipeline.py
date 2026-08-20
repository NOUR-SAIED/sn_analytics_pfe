"""
Gold layer pipeline orchestrator.

Runs the star schema build:
  1. Schema (fact_case's table, if not already present)
  2. fact_case (the last Python-owned gold table)

dim_date, dim_agent, dim_assignment_group, and dim_terminal are NOT built
here anymore - they're dbt's job now (dbt/models/gold/, run via
`dbt run --select dim_date dim_agent dim_assignment_group dim_terminal`).
fact_case is the only gold table still Python-owned, pending its own
migration (the biggest and last piece - joins all 4 dims plus the SLA
pivot). See docs/dbt_onboarding.md for the per-table migration log.
"""

from .config import (
    GOLD_SCHEMA,
    FACT_CASE_COLUMNS,
)
from .loader import (
    create_gold_schema,
    create_gold_table,
    table_exists,
)
from . import fact_case


def build_all() -> dict[str, int]:
    """Execute the gold layer build for fact_case, the last Python-owned table.

    Returns row counts. Does not touch gold.dim_date, gold.dim_agent,
    gold.dim_assignment_group, or gold.dim_terminal - run
    `dbt run --select dim_date dim_agent dim_assignment_group dim_terminal`
    separately for those (see dags/sn_bronze_to_silver.py /
    docs/dbt_onboarding.md for how this is meant to be wired into Airflow
    once fact_case itself migrates too).
    """
    counts: dict[str, int] = {}

    # ── 1. Schema and table ─────────────────────────────────────────────
    create_gold_schema()

    if not table_exists("fact_case"):
        create_gold_table("fact_case", FACT_CASE_COLUMNS)

    # ── 2. Fact table (depends on all 4 dbt-built dimensions) ───────────
    counts["fact_case"] = fact_case.build()

    return counts
