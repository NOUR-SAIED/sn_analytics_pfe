import sys
import os
import json

sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from etl.client import ServiceNowClient

TABLE = "sn_customerservice_case"
QUERY = os.getenv("SN_ACCOUNT_QUERY")

client = ServiceNowClient()

records = client.fetch_records(table=TABLE, query=QUERY, limit=10)

print(f"\nFetched {len(records)} records")

if records:
    client.save_data_to_json(records)
    print("\n--- FIRST RECORD (raw) ---")
    print(json.dumps(records[0], indent=2))