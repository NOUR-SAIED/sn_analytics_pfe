# gold.fact_case

Core case fact table. One row per customer service case, with the main workflow, classification, SLA, and audit fields flattened for analysis.

## Keys and joins
- `case_id`: Business key for the case, used as the primary key.
- `sys_id`: Unique ServiceNow identifier for the same case record.
- Date keys: `opened_date_key`, `assigned_date_key`, `first_response_date_key`, `resolved_date_key`, `closed_date_key`, `occurrence_date_key` join to `gold.dim_date`. **These are `INTEGER` surrogate keys in `YYYYMMDD` form (e.g. `20250115`), not date/timestamp values** — they cannot be compared directly to `CURRENT_DATE`, intervals, or timestamps (that raises `operator does not exist: integer >= timestamp`). For relative-date filtering, join to `gold.dim_date` and filter on its `full_date` column instead, e.g.:
  ```sql
  SELECT COUNT(*) FROM gold.fact_case f
  JOIN gold.dim_date d ON f.opened_date_key = d.date_key
  WHERE d.full_date >= CURRENT_DATE - INTERVAL '30 days'
  ```
- Agent keys: `assigned_to_sys_id`, `opened_by_sys_id`, `resolved_by_sys_id`, `owned_by_sys_id`, `last_assignee_sys_id` join to `gold.dim_agent`.
- Group keys: `assignment_group_sys_id`, `last_assignment_group_sys_id` join to `gold.dim_assignment_group`.
- Terminal key: `parking_terminal_sys_id` joins to `gold.dim_terminal`.

## Main fields
- Workflow: `state_code`, `state_label`, `auto_close`, `approval_code`, `approval_label`.
- Priority: `priority_code`, `priority_label`, `urgency_code`, `urgency_label`, `impact_code`, `impact_label`.
- Classification: `category_label`, `subcategory_label`, `u_sub_category`, `cause`, `resolution_code`, `resolution_code_label`, `sub_code`, `sub_code_label`.
- Device: `device_type_label`.
- SLA: `response_sla_duration`, `response_sla_percentage`, `response_sla_has_breached`, `resolution_sla_duration`, `resolution_sla_percentage`, `resolution_sla_has_breached`.
- Operations: `time_worked`, `reassignment_count`.
- Audit: `sys_created_on`, `sys_updated_on`, `loaded_at`.

## How to use it
- Start here for case-level analysis, then join to the dimensions for labels.
- Use the SLA fields to separate fast cases from breached cases.
- Use `occurrence_date_key` for event-time analysis and `closed_date_key` for outcome reporting.
- Treat `loaded_at` as the warehouse load timestamp, not the case event time.
