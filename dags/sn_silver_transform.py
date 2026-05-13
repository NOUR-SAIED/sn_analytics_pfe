"""
Airflow DAG: Bronze → Silver transformation.

Orchestrates the transformation of bronze JSONB records into
typed silver tables. Reusable: any table registered in
etl_core.config.silver_mappings can be transformed.

Schema migration:
  Set RECREATE_TABLES = True below, run the DAG once, then set back to False.
  This drops and recreates all silver tables with the latest schema.
"""

from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator

from etl_core.loaders.postgres_jsonb import PostgresJSONBLoader
from etl_core.loaders.postgres_silver import PostgresSilverLoader
from etl_core.transformers.silver import SilverTransformer
from etl_core.config.silver_mappings import get_config, REGISTRY


# Set to True for schema migrations (drops + recreates all silver tables)
RECREATE_TABLES = True


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
    tags=["servicenow", "silver", "transform"],
)


def transform_table(bronze_table: str, **context):
    """
    Transform a single bronze table to silver.

    Steps:
        1. Read records from bronze table
        2. Transform using SilverTransformer
        3. Upsert into silver table
    """
    config = get_config(bronze_table)
    run_id = context["run_id"]

    print(f"[PIPELINE] Starting bronze → silver for '{bronze_table}'")

    # Step 1: Read from bronze
    bronze_loader = PostgresJSONBLoader(host="postgres")
    bronze_records = bronze_loader.fetch_records(
        table_name=config.bronze_table,
        source_table=config.source_table_name,
    )

    print(f"[PIPELINE] Read {len(bronze_records)} records from bronze.{config.bronze_table}")

    if not bronze_records:
        print("[PIPELINE] No records to transform. Skipping.")
        return

    # Step 2: Transform
    transformer = SilverTransformer(config)
    silver_records = transformer.transform(bronze_records)

    print(f"[PIPELINE] Transformed {len(silver_records)} records for silver.{config.target_table}")

    # Step 3: Load to silver
    silver_loader = PostgresSilverLoader(host="postgres")

    if RECREATE_TABLES:
        print("[PIPELINE] RECREATE_TABLES=True — dropping and recreating silver table")
        silver_loader.drop_table(config)

    silver_loader.ensure_table(config)

    loaded = silver_loader.upsert_records(config, silver_records)

    print(f"[PIPELINE] Upserted {loaded} records into silver.{config.target_table}")


def verify_silver(bronze_table: str, **context):
    """Verify silver table has data."""
    config = get_config(bronze_table)
    loader = PostgresSilverLoader(host="postgres")
    count = loader.get_record_count(config)

    print(f"[VERIFY] Silver {config.target_schema}.{config.target_table} contains {count} records")

    if count == 0:
        raise ValueError("No data found in silver layer!")


# ── Create dynamic tasks for every registered bronze table ───────────────────

for bronze_table_name in REGISTRY:
    transform_task = PythonOperator(
        task_id=f"transform_{bronze_table_name}_to_silver",
        python_callable=transform_table,
        op_kwargs={"bronze_table": bronze_table_name},
        dag=dag,
    )

    verify_task = PythonOperator(
        task_id=f"verify_{bronze_table_name}_silver",
        python_callable=verify_silver,
        op_kwargs={"bronze_table": bronze_table_name},
        dag=dag,
    )

    transform_task >> verify_task
