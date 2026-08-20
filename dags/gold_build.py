"""
Airflow DAG — Gold layer star schema build.

Each dimension and the fact table get their own task for:
  - Granular logs and observability
  - Independent retry on failure
  - Clear dependency graph in the Airflow UI
  - No single point of failure

dim_date is NOT built here anymore - it's dbt's job now
(dbt/models/gold/dim_date.sql), the first table migrated off this Python
pipeline. See docs/dbt_onboarding.md for the per-table migration log.
Nothing in this DAG runs dbt yet - a dbt task exists so far only in
dags/sn_bronze_to_silver.py (dbt_snapshot_sn_case), which does not build
dim_date either. Running gold.dim_date's dbt model is currently manual
(`dbt run --select dim_date`); wiring it into a DAG (likely this one, once
more gold tables migrate to dbt) is follow-on work.
"""

from datetime import timedelta

from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.utils.dates import days_ago

# -- Infrastructure imports (always safe — these modules have no DB side effects) --
from etl_core.gold.loader import (
    create_gold_schema,
    create_gold_table,
    grant_copilot_reader_access,
    table_exists,
)
from etl_core.gold.config import (
    AGENT_DIM_COLUMNS,
    ASSIGNMENT_GROUP_DIM_COLUMNS,
    TERMINAL_DIM_COLUMNS,
    FACT_CASE_COLUMNS,
)

DEFAULT_ARGS = {
    "owner": "etl",
    "depends_on_past": False,
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
}


# ── Task callables ─────────────────────────────────────────────────────

def _ensure_tables(**context):
    """Create gold schema and all still-Python-owned tables if they don't exist."""
    create_gold_schema()
    for name, cols in [
        ("dim_agent", AGENT_DIM_COLUMNS),
        ("dim_assignment_group", ASSIGNMENT_GROUP_DIM_COLUMNS),
        ("dim_terminal", TERMINAL_DIM_COLUMNS),
        ("fact_case", FACT_CASE_COLUMNS),
    ]:
        if not table_exists(name):
            create_gold_table(name, cols)
    grant_copilot_reader_access()


def _build_dim_agent(**context):
    from etl_core.gold import dim_agent
    count = dim_agent.build()
    context["ti"].xcom_push(key="count", value=count)


def _build_dim_assignment_group(**context):
    from etl_core.gold import dim_assignment_group
    count = dim_assignment_group.build()
    context["ti"].xcom_push(key="count", value=count)


def _build_dim_terminal(**context):
    from etl_core.gold import dim_terminal
    count = dim_terminal.build()
    context["ti"].xcom_push(key="count", value=count)


def _build_fact_case(**context):
    from etl_core.gold import fact_case
    count = fact_case.build()
    context["ti"].xcom_push(key="count", value=count)


# ── DAG definition ─────────────────────────────────────────────────────

with DAG(
    dag_id="gold_build",
    default_args=DEFAULT_ARGS,
    description="Build gold star schema (dimensions + fact_case) for Superset",
    schedule_interval="0 2 * * *",
    start_date=days_ago(1),
    catchup=False,
    max_active_runs=1,
    tags=["gold", "star-schema"],
) as dag:

    ensure_tables = PythonOperator(
        task_id="ensure_tables",
        python_callable=_ensure_tables,
    )

    build_dim_agent = PythonOperator(
        task_id="build_dim_agent",
        python_callable=_build_dim_agent,
    )

    build_dim_assignment_group = PythonOperator(
        task_id="build_dim_assignment_group",
        python_callable=_build_dim_assignment_group,
    )

    build_dim_terminal = PythonOperator(
        task_id="build_dim_terminal",
        python_callable=_build_dim_terminal,
    )

    build_fact_case = PythonOperator(
        task_id="build_fact_case",
        python_callable=_build_fact_case,
    )

    # ── Dependencies ──
    # NOTE: gold.dim_date is a dependency of fact_case's date-role columns
    # too, but it's now built by dbt, run manually (see module docstring) -
    # this DAG has no automated dependency on that yet. In practice dim_date
    # rarely changes (fixed calendar range), so this is a soft gap, not a
    # correctness bug today; worth wiring a dbt task + dependency here once
    # more gold tables migrate and this DAG's shape settles.
    ensure_tables >> [
        build_dim_agent,
        build_dim_assignment_group,
        build_dim_terminal,
    ]

    [
        build_dim_agent,
        build_dim_assignment_group,
        build_dim_terminal,
    ] >> build_fact_case
