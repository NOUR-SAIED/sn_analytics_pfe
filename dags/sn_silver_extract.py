"""
Airflow DAG: Silver entity extraction.

Reads from already-transformed silver tables (silver.incidents_flat)
and produces clean silver entity tables:
    silver.incidents   — incident records with FK refs
    silver.users        — unique users
    silver.assignment_groups — unique teams
    silver.terminals    — unique terminals

Runs AFTER sn_bronze_to_silver.
"""

from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator

from etl_core.loaders.postgres_silver import PostgresSilverLoader
from etl_core.loaders.postgres_silver_dimension import PostgresDimensionLoader
from etl_core.transformers.silver import SilverTransformer
from etl_core.transformers.silver_dimension import SilverDimensionTransformer
from etl_core.config.silver_mappings import get_config
from etl_core.config.silver_dimensions import DIM_REGISTRY, get_dimension_config


RECREATE_TABLES = True


default_args = {
    "owner": "data-engineering",
    "retries": 2,
    "retry_delay": timedelta(minutes=5),
    "email_on_failure": False,
}

dag = DAG(
    dag_id="sn_silver_extract",
    default_args=default_args,
    start_date=datetime(2026, 5, 1),
    schedule="@daily",
    catchup=False,
    tags=["servicenow", "silver", "extract"],
)


def transform_silver_table(config_key: str, **context):
    config = get_config(config_key)
    run_id = context["run_id"]

    print(f"[PIPELINE] Starting silver extract for '{config_key}' → silver.{config.target_table}")

    silver_loader = PostgresSilverLoader(host="postgres")
    records = silver_loader.fetch_records_for_dimensions(
        config, sys_id_field=None
    )

    print(f"[PIPELINE] Read {len(records)} records from silver.{config.source_silver_table}")

    if not records:
        print("[PIPELINE] No records to transform. Skipping.")
        return

    transformer = SilverTransformer(config)
    silver_records = transformer.transform(records)

    print(f"[PIPELINE] Transformed {len(silver_records)} records for silver.{config.target_table}")

    if RECREATE_TABLES:
        print("[PIPELINE] RECREATE_TABLES=True — dropping and recreating silver table")
        silver_loader.drop_table(config)

    silver_loader.ensure_table(config)
    loaded = silver_loader.upsert_records(config, silver_records)

    print(f"[PIPELINE] Upserted {loaded} records into silver.{config.target_table}")


def verify_silver(config_key: str, **context):
    config = get_config(config_key)
    loader = PostgresSilverLoader(host="postgres")
    count = loader.get_record_count(config)

    print(f"[VERIFY] Silver {config.target_schema}.{config.target_table} contains {count} records")

    if count == 0:
        raise ValueError("No data found in silver layer!")


def extract_dimension(dimension_name: str, **context):
    dim_config = get_dimension_config(dimension_name)
    run_id = context["run_id"]

    print(f"[PIPELINE] Extracting dimension '{dimension_name}' from silver.{dim_config.source_silver_table}")

    silver_loader = PostgresSilverLoader(host="postgres")
    incident_config = get_config("raw_incidents_flat")

    silver_records = silver_loader.fetch_records_for_dimensions(
        incident_config, dim_config.source_sys_id_field
    )

    print(f"[PIPELINE] Read {len(silver_records)} records from silver.{dim_config.source_silver_table}")

    if not silver_records:
        print("[PIPELINE] No records found. Skipping dimension extraction.")
        return

    transformer = SilverDimensionTransformer(dim_config)
    dim_records = transformer.extract_from_silver(silver_records, run_id=run_id)

    print(f"[PIPELINE] Extracted {len(dim_records)} unique entities for silver.{dim_config.target_table}")

    dim_loader = PostgresDimensionLoader(host="postgres")

    if RECREATE_TABLES:
        print(f"[PIPELINE] RECREATE_TABLES=True — dropping and recreating {dim_config.target_table}")
        dim_loader.drop_table(dim_config)

    dim_loader.ensure_table(dim_config)
    loaded = dim_loader.upsert_records(dim_config, dim_records)

    print(f"[PIPELINE] Upserted {loaded} records into silver.{dim_config.target_table}")


def verify_dimension(dimension_name: str, **context):
    dim_config = get_dimension_config(dimension_name)
    loader = PostgresDimensionLoader(host="postgres")
    count = loader.get_record_count(dim_config)

    print(f"[VERIFY] silver.{dim_config.target_table} contains {count} records")

    if count == 0:
        raise ValueError(f"No data found in silver.{dim_config.target_table}!")


prev_task = None

incidents_task = PythonOperator(
    task_id="transform_incidents",
    python_callable=transform_silver_table,
    op_kwargs={"config_key": "raw_incidents"},
    dag=dag,
)
verify_incidents = PythonOperator(
    task_id="verify_incidents",
    python_callable=verify_silver,
    op_kwargs={"config_key": "raw_incidents"},
    dag=dag,
)
incidents_task >> verify_incidents
prev_task = verify_incidents

for dimension_name in DIM_REGISTRY:
    extract_task = PythonOperator(
        task_id=f"extract_{dimension_name}",
        python_callable=extract_dimension,
        op_kwargs={"dimension_name": dimension_name},
        dag=dag,
    )
    verify_task = PythonOperator(
        task_id=f"verify_{dimension_name}",
        python_callable=verify_dimension,
        op_kwargs={"dimension_name": dimension_name},
        dag=dag,
    )
    prev_task >> extract_task >> verify_task
    prev_task = verify_task