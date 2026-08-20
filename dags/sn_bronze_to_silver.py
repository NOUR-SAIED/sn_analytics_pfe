"""
Airflow DAG: Bronze -> Silver (flattening step).

Transforms bronze JSONB records into cleanly typed, flattened silver tables.
This maps 1:1 from Bronze to Silver, skipping complex joins.
"""

from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator

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

# NOTE: a dbt-snapshot task (history retention on sn_customerservice_case,
# see CLAUDE.md finding #1 / docs/dbt_onboarding.md) was attempted here and
# rolled back - installing dbt-core into this same image broke the
# airflow-worker Celery process (dbt pulled in click 8.4.2, incompatible
# with this project's Celery/Airflow version - the worker crash-looped on
# startup). The dbt project itself (dbt/) is real and validated standalone;
# it just isn't wired into this DAG yet until a safe execution path
# (isolated venv/container) is chosen. See docs/dbt_onboarding.md.
