# gold.dim_terminal

Lookup table for parking terminals referenced by cases.

## Fields
- `terminal_sys_id`: ServiceNow sys_id and primary key.
- `terminal_name`: Human-readable terminal name, when present.

## How to use it
- Join from `fact_case.parking_terminal_sys_id`.
- Use it when analyzing where a case was parked or held up in the workflow.
- This dimension is intentionally small and acts as a label lookup only.
