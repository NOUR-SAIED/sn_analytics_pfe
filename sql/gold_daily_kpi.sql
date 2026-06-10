-- gold_daily_kpi.sql
-- Daily KPI materialized view for fast time-series charts
CREATE SCHEMA IF NOT EXISTS gold;

CREATE MATERIALIZED VIEW IF NOT EXISTS gold.daily_kpi AS
SELECT
  opened_date::date AS dt,
  COUNT(*) FILTER (WHERE opened_at IS NOT NULL)                            AS opened_cases,
  COUNT(*) FILTER (WHERE closed_at IS NOT NULL)                            AS closed_cases,
  COUNT(*) FILTER (WHERE active IS TRUE)                                   AS open_cases_current,
  COUNT(*) FILTER (WHERE resolved_at IS NOT NULL)                          AS resolved_cases,
  AVG(resolution_time_s) FILTER (WHERE resolution_time_s IS NOT NULL)       AS avg_resolution_s,
  AVG(response_time_s) FILTER (WHERE response_time_s IS NOT NULL)           AS avg_response_s,
  SUM(CASE WHEN u_sla_breached THEN 1 ELSE 0 END)::BIGINT                  AS sla_breach_count,
  SUM(CASE WHEN escalation_label IS NOT NULL AND escalation_label <> 'Normal' THEN 1 ELSE 0 END)::BIGINT AS escalation_count,
  COUNT(*)::BIGINT                                                         AS total_cases
FROM gold.case_fact
GROUP BY 1
ORDER BY 1;
