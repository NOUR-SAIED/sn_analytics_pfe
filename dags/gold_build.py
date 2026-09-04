"""
Airflow DAG — Gold layer star schema build.

All 6 gold tables (dim_date, dim_agent, dim_assignment_group, dim_terminal,
fact_case, fact_case_status_history) are now built by dbt - see
docs/dbt_onboarding.md for the full per-table migration log. This DAG used
to run 6 PythonOperator tasks (one per table, in etl_core/gold/*.py); none
of that Python code exists anymore.

Runs via DockerOperator, same pattern as dags/sn_bronze_to_silver.py's
dbt_snapshot_sn_case task: a fresh, disposable container from the
dedicated sn_analytics-dbt image (docker/dbt/Dockerfile, no Airflow/Celery
dependencies at all) via the Docker socket mounted into airflow-worker,
removed when done. dbt-core was tried directly in the Airflow image once
and broke Celery (a `click` version collision) - see docs/dbt_onboarding.md
for that postmortem; this is the fix, not a workaround.

Task order: dbt run (builds/replaces all 6 tables via their own internal
dependency graph - dbt figures out dim_date before fact_case,
fact_case_status_history off the sn_case_snapshot before fact_case, etc.,
no manual sequencing needed) -> dbt test (the 34 dbt tests in
dbt/models/gold/_gold.yml - not_null/unique/relationships, replacing the
hard PK/FK DDL constraints the old Python-created tables had) ->
grant_copilot_reader_access (still genuinely Python's job - a Postgres
GRANT for an unrelated role, not something dbt does).
"""

import os
from datetime import timedelta

from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.providers.docker.operators.docker import DockerOperator
from airflow.utils.dates import days_ago

from etl_core.gold.loader import create_gold_schema, grant_copilot_reader_access

DEFAULT_ARGS = {
    "owner": "etl",
    "depends_on_past": False,
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
}


def _grant_access(**context):
    """Ensure the gold schema exists, then grant the read-only copilot role access."""
    create_gold_schema()
    grant_copilot_reader_access()


_DBT_ENVIRONMENT = {
    "DBT_PG_HOST": "postgres",
    "DBT_PG_PORT": os.getenv("POSTGRES_CONN_PORT", "5432"),
    "DBT_PG_USER": os.getenv("ELT_DATABASE_USERNAME", "elt_user"),
    "DBT_PG_DBNAME": os.getenv("ELT_DATABASE_NAME", ""),
}
_DBT_PRIVATE_ENVIRONMENT = {
    "DBT_PG_PASSWORD": os.getenv("ELT_DATABASE_PASSWORD", ""),
}
_DBT_DOCKER_KWARGS = dict(
    image="sn_analytics-dbt:latest",
    docker_url="unix://var/run/docker.sock",
    network_mode="sn_analytics_default",
    api_version="auto",
    auto_remove="success",
    mount_tmp_dir=False,  # host/container path mismatch trap - see docker/dbt/Dockerfile
    environment=_DBT_ENVIRONMENT,
    private_environment=_DBT_PRIVATE_ENVIRONMENT,
)


with DAG(
    dag_id="gold_build",
    default_args=DEFAULT_ARGS,
    description="Build gold star schema (dimensions + fact_case) for Superset",
    schedule_interval="0 2 * * *",
    start_date=days_ago(1),
    catchup=False,
    max_active_runs=1,
    tags=["gold", "star-schema", "dbt"],
) as dag:

    dbt_run_gold = DockerOperator(
        task_id="dbt_run_gold",
        command=["dbt", "run", "--select", "gold"],
        **_DBT_DOCKER_KWARGS,
    )

    dbt_test_gold = DockerOperator(
        task_id="dbt_test_gold",
        command=["dbt", "test", "--select", "gold"],
        **_DBT_DOCKER_KWARGS,
    )

    grant_access = PythonOperator(
        task_id="grant_copilot_reader_access",
        python_callable=_grant_access,
    )

    dbt_run_gold >> dbt_test_gold >> grant_access
