"""
Gold layer schema and table configuration.

Defines table names, schemas, and column DDL for all gold objects.
"""


GOLD_SCHEMA = "gold"

# ── SLA definition names (from contract_sla) ───────────────────────────
RESPONSE_SLA_NAME = "TPA first reaction SLA"
RESOLUTION_SLA_NAME = "TPA case resolution SLA"

# ── Table column definitions ───────────────────────────────────────────
#
# dim_date is NOT defined here anymore - it moved to dbt (the first table
# migrated in the etl_core/gold -> dbt migration, see
# docs/dbt_onboarding.md). Its date range now lives as vars.date_dim_start/
# date_dim_end in dbt/dbt_project.yml, and its columns are just whatever
# dbt/models/gold/dim_date.sql selects - dbt creates the table from that,
# no DDL list needed the way the still-Python-owned tables below require.

AGENT_DIM_COLUMNS = [
    "agent_sys_id TEXT PRIMARY KEY",
    "agent_name TEXT NOT NULL",
    "email TEXT",
    "mobile_phone TEXT",
]

ASSIGNMENT_GROUP_DIM_COLUMNS = [
    "assignment_group_sys_id TEXT PRIMARY KEY",
    "assignment_group_name TEXT NOT NULL",
]

TERMINAL_DIM_COLUMNS = [
    "terminal_sys_id TEXT PRIMARY KEY",
    "terminal_name TEXT",
]

FACT_CASE_COLUMNS = [
    "case_id TEXT PRIMARY KEY",
    "sys_id TEXT NOT NULL UNIQUE",
    "case_number TEXT",
    # -- Date foreign keys
    # No REFERENCES gold.dim_date(date_key) here (was removed): dim_date is
    # now built by dbt/models/gold/dim_date.sql, which - like every plain
    # dbt `table` materialization - doesn't emit a PRIMARY KEY, so a hard FK
    # to it would fail if fact_case is ever created fresh. Row-level
    # integrity here is covered by dbt tests instead (see
    # dbt/models/gold/_gold.yml) once fact_case itself migrates to dbt.
    "opened_date_key INTEGER",
    "assigned_date_key INTEGER",
    "first_response_date_key INTEGER",
    "resolved_date_key INTEGER",
    "closed_date_key INTEGER",
    "occurrence_date_key INTEGER",
    # -- Workflow
    "state_code TEXT",
    "state_label TEXT",
    "auto_close BOOLEAN",
    "approval_code TEXT",
    "approval_label TEXT",
    # -- Classification
    "priority_code INTEGER",
    "priority_label TEXT",
    "urgency_code INTEGER",
    "urgency_label TEXT",
    "impact_code INTEGER",
    "impact_label TEXT",
    "category_label TEXT",
    "subcategory_label TEXT",
    "u_sub_category TEXT",
    "cause TEXT",
    "resolution_code TEXT",
    "resolution_code_label TEXT",
    "sub_code TEXT",
    "sub_code_label TEXT",
    # -- Agent FKs
    # No REFERENCES gold.dim_agent(agent_sys_id) here (was removed): same
    # reason as the date FKs above - dim_agent is now built by
    # dbt/models/gold/dim_agent.sql, which has no PRIMARY KEY, so a hard FK
    # to it would fail on a fresh fact_case create. Covered by dbt tests
    # instead once fact_case itself migrates (dbt/models/gold/_gold.yml).
    "assigned_to_sys_id TEXT",
    "opened_by_sys_id TEXT",
    "resolved_by_sys_id TEXT",
    "owned_by_sys_id TEXT",
    "last_assignee_sys_id TEXT",
    # -- Assignment group FKs
    # No REFERENCES gold.dim_assignment_group(...) here (was removed) - same
    # reason as the agent/date FKs above: dim_assignment_group is now dbt-
    # built, no PRIMARY KEY. Covered by dbt tests instead once fact_case
    # itself migrates (dbt/models/gold/_gold.yml).
    "assignment_group_sys_id TEXT",
    "last_assignment_group_sys_id TEXT",
    # -- Terminal FK
    # No REFERENCES gold.dim_terminal(...) here (was removed) - same reason
    # as every other gold dim FK above: dim_terminal is now dbt-built, no
    # PRIMARY KEY. Covered by dbt tests instead once fact_case itself
    # migrates (dbt/models/gold/_gold.yml).
    "parking_terminal_sys_id TEXT",
    # -- Device (kept in fact)
    "device_type_label TEXT",
    # -- SLA metrics
    "response_sla_duration BIGINT",
    "response_sla_percentage NUMERIC",
    "response_sla_has_breached BOOLEAN",
    "resolution_sla_duration BIGINT",
    "resolution_sla_percentage NUMERIC",
    "resolution_sla_has_breached BOOLEAN",
    # -- Operational
    "time_worked BIGINT",
    "reassignment_count INTEGER",
    # -- Audit
    "sys_created_on TIMESTAMPTZ",
    "sys_updated_on TIMESTAMPTZ",
    "loaded_at TIMESTAMPTZ DEFAULT NOW()",
]
