-- gold_sla_breaches.sql
-- Detail view for SLA-breached cases (use in Superset table)
CREATE SCHEMA IF NOT EXISTS gold;

CREATE OR REPLACE VIEW gold.sla_breaches AS
SELECT
  sys_id,
  case_number,
  opened_at,
  resolved_at,
  closed_at,
  priority_label,
  assignment_group_name,
  assigned_to_name,
  resolved_by_name,
  parking_terminal_name,
  resolution_time_s,
  response_time_s,
  u_sla_breached,
  escalation_label,
  opened_date
FROM gold.case_fact
WHERE u_sla_breached = TRUE;
