"""
Test script to verify ServiceNow extraction works correctly.
Fetches records and displays sample output.

Run:
    python dags/test_extraction.py
"""

import json
from etl_core.api.config import APIConfig
from etl_core.api.servicenow_api import ServiceNowAPIClient


def main():
    """Test extraction flow."""
    print("=" * 70)
    print("ServiceNow Account Extraction Test")
    print("=" * 70)

    # Validate and log config
    try:
        APIConfig.validate()
        APIConfig.log_config()
    except ValueError as e:
        print(f"[ERROR] Configuration Error: {e}")
        return

    # Create client and fetch records
    try:
        client = ServiceNowAPIClient()
        records = client.fetch_all_records(
            table=APIConfig.TABLE_NAME,
            account_query=APIConfig.ACCOUNT_QUERY
        )

        if not records:
            print("[WARNING] No records found. Check your account query.")
            return

        # Show summary
        print(f"\n[SUMMARY]")
        print(f"  Total Records: {len(records)}")

        # Show first record (full detail)
        print(f"\n[FIRST RECORD]")
        print(json.dumps(records[0], indent=2, default=str))

        # Show key fields from first 5 records
        print(f"\n[FIRST 5 RECORDS]")
        for i, rec in enumerate(records[:5], 1):
            sys_id = rec.get("sys_id")
            if isinstance(sys_id, dict):
                sys_id = sys_id.get("value")
            
            number = rec.get("number")
            if isinstance(number, dict):
                number = number.get("value")
            
            title = rec.get("short_description")
            if isinstance(title, dict):
                title = title.get("value")
            
            account = rec.get("account")
            if isinstance(account, dict):
                account = account.get("value")
            
            print(f"  {i}. [{number}] {title} (account: {account})")

        print("\n[SUCCESS] Extraction Test Successful!")
        return records

    except Exception as e:
        print(f"\n[ERROR] Extraction Failed: {e}")
        import traceback
        traceback.print_exc()
        return None


if __name__ == "__main__":
    main()
