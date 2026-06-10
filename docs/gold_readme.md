# Gold layer — workflow, goals, and decisions

This folder defines the first gold layer for Superset. The goal is to expose case-level facts and a few dashboard-ready aggregates on top of `silver` so Superset can consume stable, business-friendly datasets instead of raw ServiceNow tables.

## Goals

- Give Superset a clean `gold` schema with one row per case plus rollups for charts and tables.
- Centralize the KPI logic in SQL so dashboards reuse the same definitions.
- Keep the pipeline simple and reproducible for local development.

## What we built

- `sql/gold_case_fact.sql` — one-row-per-case view with derived durations in seconds.
- `sql/gold_daily_kpi.sql` — daily KPI materialized view for time-series charts.
- `sql/gold_assignment_group_daily.sql` — daily KPI materialized view by assignment group.
- `sql/gold_agent_daily.sql` — daily KPI materialized view by agent.
- `sql/gold_sla_breaches.sql` — detail view for SLA-breached cases.
- `dags/gold_refresh_mviews.py` — Airflow DAG that creates the gold objects.

## Decisions we took

- The SQL in `sql/` is the source of truth. The DAG reads those files instead of duplicating SQL inline.
- The DAG does not use an Airflow Postgres connection id. It connects with the existing ELT environment variables and `psycopg2`, which matches the rest of this project.
- `gold.case_fact` is built from `silver.incidents` plus lookup joins to `silver.users`, `silver.assignment_groups`, and `silver.terminals` so the fact stays FK-oriented and Superset can still show readable names.
- Materialized views are created, but automatic refresh was removed for now. We only wanted the first runnable draft, not a refresh policy yet.

## Exact workflow

1. Raw ServiceNow data lands in Bronze.
2. Bronze is transformed into `silver.incidents_flat`, then `silver.incidents` is populated from that flattened source and lookup tables like `silver.users` and `silver.assignment_groups` are derived from it.
3. The gold DAG reads the SQL files from `sql/`.
4. The DAG creates `gold.case_fact` first.
5. After that, it creates `gold.daily_kpi`, `gold.assignment_group_daily`, and `gold.agent_daily`.
6. Superset connects to the `gold` schema and builds datasets on top of those views and materialized views.

## Current runtime behavior

- `gold.case_fact` is created by the DAG and was successfully run in Airflow.
- The DAG is idempotent for creation: it uses `CREATE SCHEMA IF NOT EXISTS`, `CREATE OR REPLACE VIEW`, and `CREATE MATERIALIZED VIEW IF NOT EXISTS`.
- Refresh jobs are not scheduled yet.

## How Superset should use it

- Use `gold.case_fact` for record-level tables, drilldowns, and detailed filters.
- Use `gold.daily_kpi` for trend charts and KPI tiles.
- Use `gold.assignment_group_daily` for team performance views.
- Use `gold.agent_daily` for agent performance views.
- Use `gold.sla_breaches` for SLA breach tables and audits.

## Why this structure

- It keeps business logic in one place.
- It makes the dashboard layer easier to maintain.
- It avoids repeating SQL in both docs and code.
- It gives us a path to add refresh logic later without redesigning the datasets.

## Verification

Run these checks against the ELT database:

```sql
\d+ gold.case_fact
SELECT COUNT(*) FROM gold.case_fact;
SELECT COUNT(*) FROM gold.daily_kpi;
SELECT COUNT(*) FROM gold.assignment_group_daily;
SELECT COUNT(*) FROM gold.agent_daily;
```

## Next step

When the dashboards need fresh numbers on a schedule, we can add a dedicated refresh task for the materialized views. For now, the focus is the stable first draft and Superset dataset setup.
