"""Airflow DAG to create and refresh gold layer views.

Creates gold schema, views, and materialized views if they don't exist.
Then refreshes materialized views daily for Superset dashboards.

Requirements:
- Add a Postgres connection in Airflow UI with Conn Id `postgres_elt` pointing
  to your ELT Postgres (use values from your .env: ELT_DATABASE_USERNAME, ELT_DATABASE_PASSWORD, ELT_DATABASE_NAME, POSTGRES_CONN_HOST, POSTGRES_CONN_PORT).

Run schedule: daily at 01:00 UTC (can be changed).
"""
from datetime import timedelta
from pathlib import Path

from airflow import DAG
from airflow.utils.dates import days_ago
import os
import psycopg2
from airflow.operators.python import PythonOperator

DEFAULT_ARGS = {
    'owner': 'etl',
    'depends_on_past': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

SQL_DIR = Path(__file__).resolve().parents[1] / "sql"


def _read_sql(filename: str) -> str:
    return (SQL_DIR / filename).read_text(encoding="utf-8")


CREATE_CASE_FACT_SQL = _read_sql("gold_case_fact.sql")
CREATE_MVIEW_DAILY_KPI_SQL = _read_sql("gold_daily_kpi.sql")
CREATE_MVIEW_ASSIGNMENT_GROUP_SQL = _read_sql("gold_assignment_group_daily.sql")
CREATE_MVIEW_AGENT_DAILY_SQL = _read_sql("gold_agent_daily.sql")

with DAG(
    dag_id='gold_refresh_mviews',
    default_args=DEFAULT_ARGS,
    description='Create and refresh gold materialized views for Superset dashboards',
    schedule_interval='0 1 * * *',  # daily at 01:00
    start_date=days_ago(1),
    catchup=False,
    max_active_runs=1,
) as dag:

    # ── Create views (idempotent) ──
    def _run_sql(sql_text: str):
      """Execute SQL against ELT Postgres using env vars."""
      host = os.getenv("POSTGRES_CONN_HOST", "postgres")
      port = int(os.getenv("POSTGRES_CONN_PORT", "5432"))
      db = os.getenv("ELT_DATABASE_NAME") or os.getenv("POSTGRES_DB")
      user = os.getenv("ELT_DATABASE_USERNAME") or os.getenv("POSTGRES_CONN_USERNAME")
      pwd = os.getenv("ELT_DATABASE_PASSWORD") or os.getenv("POSTGRES_CONN_PASSWORD")

      if not all([db, user, pwd]):
        raise RuntimeError("Missing ELT DB credentials in environment variables")

      conn = psycopg2.connect(host=host, port=port, dbname=db, user=user, password=pwd)
      try:
        with conn.cursor() as cur:
          # Some SQL strings contain multiple statements (CREATE SCHEMA; CREATE VIEW;).
          # Execute each statement separately to avoid driver/server multi-statement parsing issues.
          statements = [s.strip() for s in sql_text.split(";") if s.strip()]
          for stmt in statements:
            cur.execute(stmt)
        conn.commit()
      finally:
        conn.close()

    create_case_fact = PythonOperator(
      task_id='create_case_fact',
      python_callable=lambda: _run_sql(CREATE_CASE_FACT_SQL),
    )

    create_daily_kpi = PythonOperator(
      task_id='create_daily_kpi',
      python_callable=lambda: _run_sql(CREATE_MVIEW_DAILY_KPI_SQL),
    )

    create_assignment_group_daily = PythonOperator(
      task_id='create_assignment_group_daily',
      python_callable=lambda: _run_sql(CREATE_MVIEW_ASSIGNMENT_GROUP_SQL),
    )

    create_agent_daily = PythonOperator(
      task_id='create_agent_daily',
      python_callable=lambda: _run_sql(CREATE_MVIEW_AGENT_DAILY_SQL),
    )

    # NOTE: Refresh tasks removed for now — materialized views will be created
    # by this DAG but not refreshed automatically. Refreshing can be enabled
    # later when dashboards need scheduled updates.

    # ── Task ordering ──
    # Create case_fact first (dependency for all mviews)
    create_case_fact >> [create_daily_kpi, create_assignment_group_daily, create_agent_daily]
    
    # No automatic refreshes configured in this initial draft
