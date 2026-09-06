"""
End-to-end test: Extract from API → Load as JSONB to PostgreSQL.

Run:
    python -m dags.test_e2e_load
"""

from etl_core.api.config import APIConfig
from etl_core.api.servicenow_api import ServiceNowAPIClient
from etl_core.loaders.postgres_jsonb import PostgresJSONBLoader


def main():
    """Test full extraction and loading pipeline."""
    print("=" * 70)
    print("E2E Test: Extract API → Load PostgreSQL JSONB")
    print("=" * 70)

    # Step 1: Validate config
    try:
        APIConfig.validate()
        APIConfig.log_config()
        print()
    except ValueError as e:
        print(f"[ERROR] Config validation failed: {e}")
        return

    # Step 2: Extract from API
    try:
        print("\n[STEP 1] Extracting from ServiceNow API...")
        client = ServiceNowAPIClient()
        records = client.fetch_all_records(
            table=APIConfig.TABLE_NAME,
            account_query=APIConfig.ACCOUNT_QUERY
        )

        if not records:
            print("[ERROR] No records extracted")
            return

    except Exception as e:
        print(f"[ERROR] Extraction failed: {e}")
        import traceback
        traceback.print_exc()
        return

    # Step 3: Load to PostgreSQL
    try:
        print("\n[STEP 2] Loading to PostgreSQL (bronze.raw_incidents)...")
        # For local testing on Windows, use localhost; for Docker use 'postgres'
        loader = PostgresJSONBLoader(host="localhost")
        
        # Create bronze table if not exists
        loader.create_bronze_table("raw_incidents")
        
        # Load records
        loaded = loader.load_records(
            records=records,
            table_name="raw_incidents",
            extraction_run_id=None,  # Can add run_id from Airflow later
            truncate_first=False,    # Use upsert (ON CONFLICT) for idempotency
        )

        # Step 4: Verify
        print("\n[STEP 3] Verifying load...")
        total_in_db = loader.get_record_count("raw_incidents")
        print(f"[INFO] Total records in bronze.raw_incidents: {total_in_db}")

        if loaded > 0:
            print("\n[SUCCESS] E2E test passed!")
            print(f"  - Extracted: {len(records)} records")
            print(f"  - Loaded: {loaded} records")
            print(f"  - Total in DB: {total_in_db} records")
        else:
            print("[WARNING] No records were loaded")

    except Exception as e:
        print(f"\n[ERROR] Load failed: {e}")
        import traceback
        traceback.print_exc()
        return


if __name__ == "__main__":
    main()
