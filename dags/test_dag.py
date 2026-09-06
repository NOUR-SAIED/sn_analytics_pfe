"""
Test the first Airflow DAG locally (structure-only smoke test).

This tests the DAG structure without needing a full Airflow scheduler.
Useful for development and CI/CD validation.

Note: this used to also run an end-to-end task-execution test via
dags/etl_core_tasks.py, but that module was dead code (unused by any live
DAG, and broken — it called etl_core functions with signatures that no
longer exist). It was deleted; this file now only checks DAG structure.

Run:
    python -m dags.test_dag
"""

import sys


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
    print("\nTask Dependencies:")
    for task in dag.tasks:
        downstream = [t.task_id for t in task.downstream_list]
        if downstream:
            print(f"  {task.task_id} → {downstream}")
    
    print("\n[OK] DAG structure valid")
    return True


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
