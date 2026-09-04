"""
Airflow DAG: Bronze -> Silver (flattening step).

Transforms bronze JSONB records into cleanly typed, flattened silver tables.
This maps 1:1 from Bronze to Silver, skipping complex joins.
"""

import os
from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.providers.docker.operators.docker import DockerOperator

from etl_core.loaders.postgres_jsonb import PostgresJSONBLoader
from etl_core.loaders.postgres_silver import PostgresSilverLoader
from etl_core.transformers.silver import SilverTransformer
from etl_core.config.silver_mappings import REGISTRY, get_config


RECREATE_TABLES = False


default_args = {
    "owner": "data-engineering",
    "retries": 2,
    "retry_delay": timedelta(minutes=5),
    "email_on_failure": False,
}

dag = DAG(
    dag_id="sn_bronze_to_silver",
    default_args=default_args,
    start_date=datetime(2026, 5, 1),
    schedule="@daily",
    catchup=False,
    tags=["servicenow", "bronze", "silver", "flatten"],
)


def transform_table(config_key: str, **context):
    config = get_config(config_key)

    print(f"[PIPELINE] Starting bronze -> silver for '{config.bronze_table}'")

    bronze_loader = PostgresJSONBLoader(host="postgres")
    bronze_records = bronze_loader.fetch_records(
        table_name=config.bronze_table,
        source_table=config.source_table_name,
    )

    print(f"[PIPELINE] Read {len(bronze_records)} records from bronze.{config.bronze_table}")

    if not bronze_records:
        print("[PIPELINE] No records to transform. Skipping.")
        return

    transformer = SilverTransformer(config)
    silver_records = transformer.transform(bronze_records)

    print(f"[PIPELINE] Transformed {len(silver_records)} records for silver.{config.target_table}")

    silver_loader = PostgresSilverLoader(host="postgres")

    if RECREATE_TABLES:
        print(f"[PIPELINE] RECREATE_TABLES=True - dropping and recreating silver.{config.target_table}")
        silver_loader.drop_table(config)

    silver_loader.ensure_table(config)
    loaded = silver_loader.upsert_records(config, silver_records)

    print(f"[PIPELINE] Upserted {loaded} records into silver.{config.target_table}")


def verify_silver(config_key: str, **context):
    config = get_config(config_key)
    loader = PostgresSilverLoader(host="postgres")
    count = loader.get_record_count(config)

    print(f"[VERIFY] Silver table {config.target_schema}.{config.target_table} contains {count} records")

    if count == 0:
        raise ValueError(f"No data found in silver layer for {config.target_table}!")


# Dynamically generate tasks for every table in our registry
verify_tasks = {}
for config_key, config in REGISTRY.items():
    transform_task = PythonOperator(
        task_id=f"transform_{config.bronze_table}_to_silver",
        python_callable=transform_table,
        op_kwargs={"config_key": config_key},
        dag=dag,
    )

    verify_task = PythonOperator(
        task_id=f"verify_{config.target_table}",
        python_callable=verify_silver,
        op_kwargs={"config_key": config_key},
        dag=dag,
    )

    transform_task >> verify_task
    verify_tasks[config_key] = verify_task


# History retention (CLAUDE.md finding #1 / docs/dbt_onboarding.md):
# bronze/silver both upsert-by-sys_id, so a case's status/assignment
# history is only ever captured if we snapshot it here, right after
# silver is verified fresh. Purely additive - snapshots.sn_case_snapshot
# is a new table; nothing downstream reads it yet.
#
# Runs via DockerOperator, NOT installed into this image: dbt-core was
# tried directly in this image once and broke Celery (a `click` version
# collision - see docs/dbt_onboarding.md for the postmortem). This task
# instead launches a fresh, disposable container from the dedicated
# sn_analytics-dbt image (docker/dbt/Dockerfile, has no Airflow/Celery
# dependencies at all) via the Docker socket mounted into airflow-worker,
# and removes it when done.
dbt_snapshot_case = DockerOperator(
    task_id="dbt_snapshot_sn_case",
    image="sn_analytics-dbt:latest",
    docker_url="unix://var/run/docker.sock",
    network_mode="sn_analytics_default",
    api_version="auto",
    auto_remove="success",
    mount_tmp_dir=False,  # avoid host/container path mismatches - see docker/dbt/Dockerfile
    command=["dbt", "snapshot", "--select", "sn_case_snapshot"],
    environment={
        "DBT_PG_HOST": "postgres",
        "DBT_PG_PORT": os.getenv("POSTGRES_CONN_PORT", "5432"),
        "DBT_PG_USER": os.getenv("ELT_DATABASE_USERNAME", "elt_user"),
        "DBT_PG_DBNAME": os.getenv("ELT_DATABASE_NAME", ""),
    },
    private_environment={
        "DBT_PG_PASSWORD": os.getenv("ELT_DATABASE_PASSWORD", ""),
    },
    dag=dag,
)

verify_tasks["sn_customerservice_case"] >> dbt_snapshot_case

# Same history-retention idea, applied to the other half of finding #1
# ("dims are not snapshotted"): silver.sys_user is a real, independently
# extracted source table, so an agent's name/email/phone getting changed
# over time is meaningful history to keep, not something derived. See
# snapshots/sys_user_snapshot.sql for why this uses a `check` strategy
# instead of `timestamp` (no sys_updated_on column in silver.sys_user yet),
# and why dim_assignment_group/dim_terminal don't get the same treatment
# (no independent source table for either - they're denormalized out of
# sn_customerservice_case, whose own history sn_case_snapshot already
# covers).
dbt_snapshot_sys_user = DockerOperator(
    task_id="dbt_snapshot_sys_user",
    image="sn_analytics-dbt:latest",
    docker_url="unix://var/run/docker.sock",
    network_mode="sn_analytics_default",
    api_version="auto",
    auto_remove="success",
    mount_tmp_dir=False,  # avoid host/container path mismatches - see docker/dbt/Dockerfile
    command=["dbt", "snapshot", "--select", "sys_user_snapshot"],
    environment={
        "DBT_PG_HOST": "postgres",
        "DBT_PG_PORT": os.getenv("POSTGRES_CONN_PORT", "5432"),
        "DBT_PG_USER": os.getenv("ELT_DATABASE_USERNAME", "elt_user"),
        "DBT_PG_DBNAME": os.getenv("ELT_DATABASE_NAME", ""),
    },
    private_environment={
        "DBT_PG_PASSWORD": os.getenv("ELT_DATABASE_PASSWORD", ""),
    },
    dag=dag,
)

verify_tasks["sys_user"] >> dbt_snapshot_sys_user
