"""
Airflow DAG — Gold layer star schema build.

dim_date, dim_agent, dim_assignment_group, and dim_terminal are NOT built
here anymore - they're dbt's job now (dbt/models/gold/), the first four
tables migrated off this Python pipeline. See docs/dbt_onboarding.md for
the per-table migration log. fact_case is the only gold table left here -
the biggest, last piece (joins all 4 dbt-built dims plus the SLA pivot).

Nothing in this DAG runs dbt yet - a dbt task exists so far only in
dags/sn_bronze_to_silver.py (dbt_snapshot_sn_case), which builds none of
the dims above. Running those dbt models is currently manual
(`dbt run --select dim_date dim_agent dim_assignment_group dim_terminal`);
wiring dbt into a DAG (likely this one, once fact_case migrates too and
this DAG's shape settles for good) is follow-on work.
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
from etl_core.gold.config import FACT_CASE_COLUMNS

DEFAULT_ARGS = {
    "owner": "etl",
    "depends_on_past": False,
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
}


# ── Task callables ─────────────────────────────────────────────────────

def _ensure_tables(**context):
    """Create gold schema and fact_case (the only still-Python-owned table) if missing."""
    create_gold_schema()
    if not table_exists("fact_case"):
        create_gold_table("fact_case", FACT_CASE_COLUMNS)
    grant_copilot_reader_access()


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

    build_fact_case = PythonOperator(
        task_id="build_fact_case",
        python_callable=_build_fact_case,
    )

    # ── Dependencies ──
    # NOTE: all 4 gold dims fact_case joins against are now built by dbt,
    # run manually (see module docstring) - this DAG has no automated
    # dependency on any of them yet. Worth wiring dbt tasks + dependencies
    # here once fact_case itself migrates and this DAG's shape settles.
    ensure_tables >> build_fact_case
