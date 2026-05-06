"""
Airflow task wrappers for DAG orchestration.

These callables wrap etl_core business logic for use in Airflow DAGs.
Kept in dags/ folder so Airflow can access them directly.
"""

from typing import List, Dict, Any

from etl_core.api.servicenow_api import ServiceNowAPIClient
from etl_core.loaders.postgres_jsonb import PostgresJSONBLoader


def extract_servicenow_records(
    table_name: str = "sn_customerservice_case",
    account_query: str = None
) -> List[Dict[str, Any]]:
    """Extract records from ServiceNow API (etl_core wrapped)."""
    print(f"[EXTRACT] Fetching from {table_name}...")
    client = ServiceNowAPIClient()
    records = client.fetch_all_records(
        table=table_name,
        account_query=account_query
    )
    print(f"[EXTRACT] Fetched {len(records)} records")
    return records


def load_to_bronze(
    records: List[Dict[str, Any]],
    table_name: str = "raw_incidents",
    extraction_run_id: str = None,
    postgres_host: str = "postgres"
) -> int:
    """Load records to PostgreSQL bronze layer (etl_core wrapped)."""
    print(f"[LOAD] Loading {len(records)} records to bronze.{table_name}...")
    
    loader = PostgresJSONBLoader(host=postgres_host)
    loader.create_bronze_table(table_name)
    
    loaded = loader.load_records(
        records=records,
        table_name=table_name,
        extraction_run_id=extraction_run_id,
        truncate_first=False
    )
    
    print(f"[LOAD] Loaded {loaded} records")
    return loaded


def verify_bronze_load(
    table_name: str = "raw_incidents",
    postgres_host: str = "postgres"
) -> int:
    """Verify records in bronze table (etl_core wrapped)."""
    print(f"[VERIFY] Checking bronze.{table_name}...")
    
    loader = PostgresJSONBLoader(host=postgres_host)
    count = loader.get_record_count(table_name)
    
    print(f"[VERIFY] Found {count} records in bronze.{table_name}")
    return count
