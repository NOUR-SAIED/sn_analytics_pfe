"""
Gold layer schema and table configuration.

Defines table names, schemas, and column DDL for all gold objects.
"""


GOLD_SCHEMA = "gold"

# ── SLA definition names (from contract_sla) ───────────────────────────
RESPONSE_SLA_NAME = "TPA first reaction SLA"
RESOLUTION_SLA_NAME = "TPA case resolution SLA"

# ── dim_date range ─────────────────────────────────────────────────────
DATE_DIM_START = "2020-01-01"
DATE_DIM_END = "2030-12-31"

# ── Table column definitions ───────────────────────────────────────────

DATE_DIM_COLUMNS = [
    "date_key INTEGER PRIMARY KEY",
    "full_date DATE NOT NULL",
    "year INTEGER NOT NULL",
    "month INTEGER NOT NULL",
    "day INTEGER NOT NULL",
    "week INTEGER NOT NULL",
    "weekday INTEGER NOT NULL",
]

AGENT_DIM_COLUMNS = [
    "agent_sys_id TEXT PRIMARY KEY",
    "agent_name TEXT NOT NULL",
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
    "opened_date_key INTEGER REFERENCES gold.dim_date(date_key)",
    "assigned_date_key INTEGER REFERENCES gold.dim_date(date_key)",
    "first_response_date_key INTEGER REFERENCES gold.dim_date(date_key)",
    "resolved_date_key INTEGER REFERENCES gold.dim_date(date_key)",
    "closed_date_key INTEGER REFERENCES gold.dim_date(date_key)",
    "occurrence_date_key INTEGER REFERENCES gold.dim_date(date_key)",
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
    "assigned_to_sys_id TEXT REFERENCES gold.dim_agent(agent_sys_id)",
    "opened_by_sys_id TEXT REFERENCES gold.dim_agent(agent_sys_id)",
    "resolved_by_sys_id TEXT REFERENCES gold.dim_agent(agent_sys_id)",
    "owned_by_sys_id TEXT REFERENCES gold.dim_agent(agent_sys_id)",
    "last_assignee_sys_id TEXT REFERENCES gold.dim_agent(agent_sys_id)",
    # -- Assignment group FKs
    "assignment_group_sys_id TEXT REFERENCES gold.dim_assignment_group(assignment_group_sys_id)",
    "last_assignment_group_sys_id TEXT REFERENCES gold.dim_assignment_group(assignment_group_sys_id)",
    # -- Terminal FK
    "parking_terminal_sys_id TEXT REFERENCES gold.dim_terminal(terminal_sys_id)",
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
