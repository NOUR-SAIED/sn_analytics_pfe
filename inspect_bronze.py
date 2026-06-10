import sys
from dotenv import load_dotenv
load_dotenv('C:\\pfe\\sn_analytics\\.env')
import os

sys.path.append('C:\\pfe\\sn_analytics')
from etl_core.loaders.postgres_jsonb import PostgresJSONBLoader
import json

loader = PostgresJSONBLoader(host="localhost", database="elt_sn_db", user="elt_user", password="1234", port=5432)

def print_keys(table):
    records = loader.fetch_records(table_name=table, limit=1)
    if records:
        print(f"\n--- Fields in {table} ---")
        keys = [k for k in records[0].keys() if k not in ('id', 'source_table', 'loaded_at', 'extraction_run_id')]
        print(json.dumps(keys, indent=2))
    else:
        print(f"No records found in {table}")

print_keys("raw_task_sla")
print_keys("raw_contract_sla")
