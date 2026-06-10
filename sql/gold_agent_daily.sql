-- gold_agent_daily.sql
-- Daily KPIs grouped by agent (resolved_by preferred)
CREATE SCHEMA IF NOT EXISTS gold;

CREATE MATERIALIZED VIEW IF NOT EXISTS gold.agent_daily AS
SELECT
  opened_date::date AS dt,
  COALESCE(resolved_by_name, assigned_to_name, 'Unknown') AS agent_name,
  COUNT(*) FILTER (WHERE resolved_at IS NOT NULL) AS resolved_cases,
  AVG(resolution_time_s) FILTER (WHERE resolution_time_s IS NOT NULL) AS avg_resolution_s,
  SUM(CASE WHEN u_sla_breached THEN 1 ELSE 0 END)::BIGINT AS sla_breach_count,
  COUNT(*)::BIGINT AS total_cases
FROM gold.case_fact
GROUP BY 1,2;
