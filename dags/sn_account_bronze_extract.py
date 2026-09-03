from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.models import Param

from etl_core.api.servicenow_api import ServiceNowAPIClient
from etl_core.loaders.postgres_jsonb import PostgresJSONBLoader
from etl_core.loaders.postgres_watermark import PostgresWatermarkLoader
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

# ServiceNow encoded-query datetime format (instance local time).
SN_QUERY_DATETIME_FMT = "%Y-%m-%d %H:%M:%S"


def _field_value(record: dict, field: str):
    """
    ServiceNow returns fields as {"value": ..., "display_value": ...} when
    sysparm_display_value=all (which this client always sets), not as plain
    scalars. Unwrap that shape; fall back to the raw value for safety.
    """
    raw = record.get(field)
    if isinstance(raw, dict):
        return raw.get("value") or raw.get("display_value")
    return raw


def _max_sys_updated_on(records):
    """Highest sys_updated_on across a batch, or None if none parse."""
    best = None
    for record in records:
        raw = _field_value(record, "sys_updated_on")
        if not raw:
            continue
        try:
            ts = datetime.strptime(raw, SN_QUERY_DATETIME_FMT)
        except ValueError:
            continue
        if best is None or ts > best:
            best = ts
    return best


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
    params={
        "full_resync": Param(
            False,
            type="boolean",
            description="Ignore the stored watermark and re-pull every record for "
                        "every table. The watermark is still advanced afterward, "
                        "so the next scheduled run goes back to incremental.",
        ),
    },
)


# ----------------------------
# TASK 1: EXTRACT + LOAD
# ----------------------------
def extract_and_load(sn_table, bronze_table, query_filter, fields=None, **context):
    """
    Single-flow ingestion:
    Extract from ServiceNow → Load directly into PostgreSQL bronze

    Incremental by default: scopes the query to records updated since this
    table's last successful run. Pass full_resync=True (DAG param, settable at
    trigger time) to ignore the watermark for one run and pull everything -
    the watermark still advances afterward, so the next scheduled run goes
    back to incremental automatically.
    """

    watermark_loader = PostgresWatermarkLoader(host="postgres")
    full_resync = bool(context.get("params", {}).get("full_resync", False))

    effective_query = query_filter
    watermark = None if full_resync else watermark_loader.get_watermark(sn_table)

    if watermark is not None:
        cutoff = watermark.strftime(SN_QUERY_DATETIME_FMT)
        effective_query = f"{query_filter}^sys_updated_on>={cutoff}" if query_filter else f"sys_updated_on>={cutoff}"
        print(f"[PIPELINE] Incremental extraction for {sn_table}: records updated since {cutoff}")
    else:
        reason = "full_resync requested" if full_resync else "no watermark yet"
        print(f"[PIPELINE] Full extraction for {sn_table} ({reason})")

    client = ServiceNowAPIClient()
    records = client.fetch_all_records(
        table=sn_table,
        query_filter=effective_query,
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

    # Advance the watermark only after a successful load, and only if we saw
    # records with a parseable sys_updated_on - an empty/partial batch leaves
    # it untouched so the next run safely re-covers the same window.
    new_high_water = _max_sys_updated_on(records)
    if new_high_water is not None:
        watermark_loader.set_watermark(sn_table, new_high_water)
    else:
        print(f"[PIPELINE] No parseable sys_updated_on in this batch; watermark for {sn_table} unchanged")


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
