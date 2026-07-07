# gold.dim_assignment_group

Assignment group lookup table for the teams that handled cases.

## Fields
- `assignment_group_sys_id`: ServiceNow sys_id and primary key.
- `assignment_group_name`: Display name for the group.

## How to use it
- Join from `fact_case.assignment_group_sys_id` or `fact_case.last_assignment_group_sys_id`.
- Use this table for team-level reporting, routing analysis, and workload summaries.
- If you need historical assignment behavior, compare the current and last assignment group fields in the fact.
