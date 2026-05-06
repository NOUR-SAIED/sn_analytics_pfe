from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator

from etl_core.api.servicenow_api import ServiceNowAPIClient
from etl_core.loaders.postgres_jsonb import PostgresJSONBLoader


# ----------------------------
# CONFIG
# ----------------------------
TABLE_NAME = "sn_customerservice_case"
BRONZE_TABLE = "raw_incidents"


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
    tags=["servicenow", "bronze", "ingestion"],
)


# ----------------------------
# TASK 1: EXTRACT + LOAD (combined logic inside task)
# ----------------------------
def extract_and_load(**context):
    """
    Single-flow ingestion:
    Extract from ServiceNow → Load directly into PostgreSQL bronze
    """

    print("[PIPELINE] Starting extraction...")

    client = ServiceNowAPIClient()
    records = client.fetch_all_records(
        table=TABLE_NAME,
        account_query=None
    )

    print(f"[PIPELINE] Extracted {len(records)} records")

    print("[PIPELINE] Loading into PostgreSQL bronze...")

    loader = PostgresJSONBLoader(host="postgres")

    loader.create_bronze_table(BRONZE_TABLE)

    loaded = loader.load_records(
        records=records,
        table_name=BRONZE_TABLE,
        extraction_run_id=context["run_id"],
        #truncate_first=False
    )

    print(f"[PIPELINE] Loaded {loaded} records into bronze")


extract_load_task = PythonOperator(
    task_id="extract_and_load",
    python_callable=extract_and_load,
    dag=dag,
)


# ----------------------------
# TASK 2: VERIFY
# ----------------------------
def verify_load(**context):
    """
    Simple verification step
    """

    loader = PostgresJSONBLoader(host="postgres")

    count = loader.get_record_count(BRONZE_TABLE)

    print(f"[VERIFY] Bronze table contains {count} records")

    if count == 0:
        raise ValueError("No data found in bronze layer!")


verify_task = PythonOperator(
    task_id="verify_bronze_load",
    python_callable=verify_load,
    dag=dag,
)


# ----------------------------
# DEPENDENCIES
# ----------------------------
extract_load_task >> verify_task