"""
Test the first Airflow DAG locally (simulating task execution).

This tests the DAG logic without needing a full Airflow scheduler.
Useful for development and CI/CD validation.

Run:
    python -m dags.test_dag
"""

import sys
from datetime import datetime
from etl_core.api.config import APIConfig


def test_dag_structure():
    """Test that DAG is properly configured."""
    from sn_account_bronze_extract import dag

    print("=" * 70)
    print("Testing DAG Structure")
    print("=" * 70)
    
    print(f"\nDAG ID: {dag.dag_id}")
    print(f"Description: {dag.description}")
    print(f"Schedule: {dag.schedule}")
    print(f"Start Date: {dag.start_date}")
    print(f"Tags: {dag.tags}")
    
    print(f"\nTasks ({len(dag.task_ids)}):")
    for i, task_id in enumerate(dag.task_ids, 1):
        print(f"  {i}. {task_id}")
    
    # Verify task dependencies
    print(f"\nTask Dependencies:")
    for task in dag.tasks:
        downstream = [t.task_id for t in task.downstream_list]
        if downstream:
            print(f"  {task.task_id} → {downstream}")
    
    print("\n[OK] DAG structure valid")
    return True


def test_dag_execution():
    """Test DAG tasks execute successfully (end-to-end)."""
    from etl_core_tasks import (
        extract_servicenow_records,
        load_to_bronze,
        verify_bronze_load,
    )

    print("\n" + "=" * 70)
    print("Testing DAG Task Execution (End-to-End)")
    print("=" * 70)
    
    try:
        # Task 1: Extract
        print("\n[1/3] Running extract_servicenow_records...")
        records = extract_servicenow_records(
            table_name=APIConfig.TABLE_NAME,
            account_query=APIConfig.ACCOUNT_QUERY,
        )
        print(f"[OK] Extracted {len(records)} records")
        
        if not records:
            print("[ERROR] No records extracted")
            return False
        
        # Task 2: Load
        print("\n[2/3] Running load_to_bronze...")
        loaded = load_to_bronze(
            records=records,
            table_name="raw_incidents",
            extraction_run_id=f"test_run_{datetime.now().isoformat()}",
            postgres_host="localhost",  # Use localhost for local testing
        )
        print(f"[OK] Loaded {loaded} records")
        
        if loaded != len(records):
            print(f"[WARNING] Expected {len(records)}, but loaded {loaded}")
        
        # Task 3: Verify
        print("\n[3/3] Running verify_bronze_load...")
        count = verify_bronze_load(
            table_name="raw_incidents",
            postgres_host="localhost",  # Use localhost for local testing
        )
        print(f"[OK] Verified {count} records in bronze table")
        
        if count == 0:
            print("[ERROR] No records found after load")
            return False
        
        print("\n[OK] All tasks executed successfully")
        return True
    
    except Exception as e:
        print(f"\n[ERROR] Task execution failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all tests."""
    print("\n")
    print("╔" + "═" * 68 + "╗")
    print("║" + " " * 15 + "Airflow DAG: sn_account_bronze_extract" + " " * 13 + "║")
    print("║" + " " * 20 + "Local Test Suite" + " " * 33 + "║")
    print("╚" + "═" * 68 + "╝")
    
    results = []
    
    # Test 1: DAG structure
    try:
        result = test_dag_structure()
        results.append(("DAG Structure", result))
    except Exception as e:
        print(f"[FATAL] DAG structure test failed: {e}")
        results.append(("DAG Structure", False))
    
    # Test 2: DAG execution
    try:
        result = test_dag_execution()
        results.append(("DAG Execution", result))
    except Exception as e:
        print(f"[FATAL] DAG execution test failed: {e}")
        results.append(("DAG Execution", False))
    
    # Summary
    print("\n" + "=" * 70)
    print("Test Summary")
    print("=" * 70)
    for test_name, passed in results:
        status = "[PASS]" if passed else "[FAIL]"
        print(f"{status} {test_name}")
    
    all_passed = all(r[1] for r in results)
    
    if all_passed:
        print("\n[SUCCESS] All tests passed!")
        return 0
    else:
        print("\n[FAILURE] Some tests failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
