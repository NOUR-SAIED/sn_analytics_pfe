"""
Gold layer pipeline orchestrator.

Runs the full star schema build in dependency order:
  1. Schema + dim_date (idempotent, always safe)
  2. dim_agent, dim_assignment_group, dim_terminal (independent)
  3. fact_case (depends on all dimensions)
"""

from .config import (
    GOLD_SCHEMA,
    DATE_DIM_COLUMNS,
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
from . import dim_date, dim_agent, dim_assignment_group, dim_terminal, fact_case


def build_all() -> dict[str, int]:
    """Execute the full gold layer build. Returns row counts per table."""
    counts: dict[str, int] = {}

    # ── 1. Schema and tables ────────────────────────────────────────────
    create_gold_schema()

    if not table_exists("dim_date"):
        create_gold_table("dim_date", DATE_DIM_COLUMNS)
    if not table_exists("dim_agent"):
        create_gold_table("dim_agent", AGENT_DIM_COLUMNS)
    if not table_exists("dim_assignment_group"):
        create_gold_table("dim_assignment_group", ASSIGNMENT_GROUP_DIM_COLUMNS)
    if not table_exists("dim_terminal"):
        create_gold_table("dim_terminal", TERMINAL_DIM_COLUMNS)
    if not table_exists("fact_case"):
        create_gold_table("fact_case", FACT_CASE_COLUMNS)

    # ── 2. Date dimension (idempotent append) ───────────────────────────
    counts["dim_date"] = dim_date.build()

    # ── 3. Small dimensions (full refresh, independent) ─────────────────
    counts["dim_agent"] = dim_agent.build()
    counts["dim_assignment_group"] = dim_assignment_group.build()
    counts["dim_terminal"] = dim_terminal.build()

    # ── 4. Fact table (depends on all dimensions) ───────────────────────
    counts["fact_case"] = fact_case.build()

    return counts
