-- gold_case_fact.sql
-- One-row-per-case view for Superset consumption
CREATE SCHEMA IF NOT EXISTS gold;

CREATE OR REPLACE VIEW gold.case_fact AS
SELECT
  s.sys_id,
  s.case_number,
  s.case_title,
  s.opened_at,
  s.first_response_time,
  s.assigned_at,
  s.resolved_at,
  s.closed_at,
  date_trunc('day', s.opened_at)::date AS opened_date,
  s.assignment_group_sys_id,
  ag.name AS assignment_group_name,
  s.assigned_to_sys_id,
  u_assigned.name AS assigned_to_name,
  s.resolved_by_sys_id,
  u_resolved.name AS resolved_by_name,
  s.opened_by_sys_id,
  u_opened.name AS opened_by_name,
  s.owned_by_sys_id,
  u_owned.name AS owned_by_name,
  s.last_assignee_sys_id,
  u_last_assignee.name AS last_assignee_name,
  s.account_sys_id,
  s.parking_terminal_sys_id,
  t.name AS parking_terminal_name,
  s.priority_code,
  s.priority_label,
  s.category_label,
  s.subcategory_label,
  s.escalation_label,
  s.made_sla,
  s.u_sla_breached,
  s.active,
  s.time_worked,
  -- Derived measures (seconds)
  EXTRACT(EPOCH FROM (first_response_time - opened_at))::BIGINT AS response_time_s,
  EXTRACT(EPOCH FROM (resolved_at - opened_at))::BIGINT AS resolution_time_s,
  EXTRACT(EPOCH FROM (assigned_at - opened_at))::BIGINT AS assign_time_s,
  EXTRACT(EPOCH FROM (closed_at - resolved_at))::BIGINT AS closure_lag_s
FROM silver.incidents s
LEFT JOIN silver.assignment_groups ag
  ON s.assignment_group_sys_id = ag.sys_id
LEFT JOIN silver.users u_assigned
  ON s.assigned_to_sys_id = u_assigned.sys_id
LEFT JOIN silver.users u_resolved
  ON s.resolved_by_sys_id = u_resolved.sys_id
LEFT JOIN silver.users u_opened
  ON s.opened_by_sys_id = u_opened.sys_id
LEFT JOIN silver.users u_owned
  ON s.owned_by_sys_id = u_owned.sys_id
LEFT JOIN silver.users u_last_assignee
  ON s.last_assignee_sys_id = u_last_assignee.sys_id
LEFT JOIN silver.terminals t
  ON s.parking_terminal_sys_id = t.sys_id
WHERE s.opened_at IS NOT NULL;
