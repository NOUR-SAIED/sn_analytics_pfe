from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator

from etl_core.api.servicenow_api import ServiceNowAPIClient
from etl_core.loaders.postgres_jsonb import PostgresJSONBLoader
from etl_core.api.config import APIConfig


# ----------------------------
# CONFIG
# ----------------------------
default_args = {
    "owner": "data-engineering",
    "retries": 2,
    "retry_delay": timedelta(minutes=5),
    "email_on_failure": False,
}


# ----------------------------
# DAG
# ----------------------------
dag = DAG(
    dag_id="sn_account_bronze_ingestion",
    default_args=default_args,
    start_date=datetime(2026, 5, 1),
    schedule="@daily",
    catchup=False,
    tags=["servicenow", "bronze", "ingestion", "multi-table"],
)


# ----------------------------
# TASK 1: EXTRACT + LOAD
# ----------------------------
def extract_and_load(sn_table, bronze_table, query_filter, fields=None, **context):
    """
    Single-flow ingestion:
    Extract from ServiceNow → Load directly into PostgreSQL bronze
    """

    print(f"[PIPELINE] Starting extraction for {sn_table}...")

    client = ServiceNowAPIClient()
    records = client.fetch_all_records(
        table=sn_table,
        query_filter=query_filter,
        fields=fields
    )

    print(f"[PIPELINE] Extracted {len(records)} records for {sn_table}")

    print(f"[PIPELINE] Loading into PostgreSQL bronze table {bronze_table}...")

    loader = PostgresJSONBLoader(host="postgres")

    loader.create_bronze_table(bronze_table)

    loaded = loader.load_records(
        records=records,
        source_table=sn_table,
        table_name=bronze_table,
        extraction_run_id=context["run_id"],
    )

    print(f"[PIPELINE] Loaded {loaded} records into bronze table {bronze_table}")


# ----------------------------
# TASK 2: VERIFY
# ----------------------------
def verify_load(bronze_table, **context):
    """
    Simple verification step
    """

    loader = PostgresJSONBLoader(host="postgres")

    count = loader.get_record_count(bronze_table)

    print(f"[VERIFY] Bronze table {bronze_table} contains {count} records")

    if count == 0:
        raise ValueError(f"No data found in bronze layer for {bronze_table}!")


# ----------------------------
# DEPENDENCIES (Dynamic Generation)
# ----------------------------
for sn_table, config in APIConfig.TABLES_CONFIG.items():
    bronze_table = config["bronze_table"]
    query_filter = config.get("query_filter")
    fields = config.get("fields")
    
    extract_load_task = PythonOperator(
        task_id=f"extract_and_load_{sn_table}",
        python_callable=extract_and_load,
        op_kwargs={
            "sn_table": sn_table,
            "bronze_table": bronze_table,
            "query_filter": query_filter,
            "fields": fields
        },
        dag=dag,
    )

    verify_task = PythonOperator(
        task_id=f"verify_{sn_table}_load",
        python_callable=verify_load,
        op_kwargs={
            "bronze_table": bronze_table
        },
        dag=dag,
    )

    extract_load_task >> verify_task
