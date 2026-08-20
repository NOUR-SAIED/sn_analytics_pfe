"""
Gold layer configuration.

All 5 gold tables (dim_date, dim_agent, dim_assignment_group, dim_terminal,
fact_case) are now built by dbt (dbt/models/gold/) - see
docs/dbt_onboarding.md for the full per-table migration log. This file used
to hold column DDL lists for each Python-built table plus the SLA
definition name constants; both are gone now. dbt creates its own tables
from each model's SELECT output (no DDL list needed), and the SLA names
moved to vars.response_sla_name/resolution_sla_name in dbt/dbt_project.yml
(referenced in dbt/models/gold/fact_case.sql via {{ var(...) }}).

What's left is genuinely still needed by Python/Airflow: GOLD_SCHEMA, used
by etl_core/gold/loader.py for the schema-exists check and the
copilot_reader grants - neither of which is a dbt concern.
"""

GOLD_SCHEMA = "gold"
