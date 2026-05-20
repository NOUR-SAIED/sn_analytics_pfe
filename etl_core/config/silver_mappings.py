"""
Silver layer table configurations.

Each SilverTableConfig defines:
- source: bronze table name
- target_schema / target_table: where to write
- source_table_name: ServiceNow table filter (optional)
- fields: list of field mappings from bronze JSONB -> silver column
- computed: list of derived fields (e.g. response_time_s)

Field mapping keys:
  source        -- field name in the bronze JSONB record_json
  column        -- target column name in the silver table
  type          -- TEXT, INTEGER, FLOAT, BOOLEAN, TIMESTAMP, DATE, DURATION
  pick          -- "value" | "display_value" | "raw" (default: "value")
                   ServiceNow API returns {value, display_value} dicts.
                   "raw" = use the value as-is (for simple fields).
  required      -- if True, records missing this field are skipped (default: False)
  default       -- default value when null (optional)
"""

from dataclasses import dataclass, field
from typing import List, Optional, Literal


FieldType = Literal["TEXT", "INTEGER", "FLOAT", "BOOLEAN", "TIMESTAMP", "DATE", "DURATION", "JSONB"]
PickValue = Literal["value", "display_value", "raw"]


@dataclass 
class FieldMapping:
    source: str
    column: str
    type: FieldType = "TEXT"
    pick: PickValue = "value"
    required: bool = False
    default: any = None


@dataclass
class SilverTableConfig:
    """Configuration for a single bronze -> silver transformation."""

    bronze_table: str
    target_schema: str = "silver"
    target_table: str = ""
    source_table_name: Optional[str] = None
    source_silver_table: Optional[str] = None
    fields: List[FieldMapping] = field(default_factory=list)

    def __post_init__(self):
        if not self.target_table:
            self.target_table = self.bronze_table
        if not self.source_table_name:
            self.source_table_name = self.bronze_table


# -- Helper shortcuts ----------------------------------------------------------

def f_text(source, column=None, pick="value", **kw):
    return FieldMapping(source, column or source, "TEXT", pick, **kw)

def f_int(source, column=None, pick="value", **kw):
    return FieldMapping(source, column or source, "INTEGER", pick, **kw)

def f_float(source, column=None, pick="value", **kw):
    return FieldMapping(source, column or source, "FLOAT", pick, **kw)

def f_bool(source, column=None, pick="value", **kw):
    return FieldMapping(source, column or source, "BOOLEAN", pick, **kw)

def f_ts(source, column=None, pick="value", **kw):
    return FieldMapping(source, column or source, "TIMESTAMP", pick, **kw)

def f_date(source, column=None, pick="value", **kw):
    return FieldMapping(source, column or source, "DATE", pick, **kw)

def f_duration(source, column=None, **kw):
    """Duration fields (epoch datetime -> seconds). pick is always 'value'."""
    return FieldMapping(source, column or source, "DURATION", "value", **kw)


def coded(source, code_type="TEXT", code_column=None, label_column=None):
    """
    Creates two field mappings for a coded field: one for code, one for label.

    Example:
        coded("priority", code_type="INTEGER")
        # -> [
        #      FieldMapping("priority", "priority_code", "INTEGER", "value"),
        #      FieldMapping("priority", "priority_label", "TEXT", "display_value"),
        #    ]
    """
    return [
        FieldMapping(source, code_column or f"{source}_code", code_type, "value"),
        FieldMapping(source, label_column or f"{source}_label", "TEXT", "display_value"),
    ]


# -- Table configurations ------------------------------------------------------

RAW_INCIDENTS_FLAT = SilverTableConfig(
    bronze_table="raw_incidents",
    target_schema="silver",
    target_table="incidents_flat",
    source_table_name="sn_customerservice_case",
    fields=[
        # -- Identity
        f_text("sys_id",                                     required=True),
        f_text("number",              column="case_number"),
        f_text("case",                column="case_title"),
        f_text("sys_class_name"),
        f_text("task_effective_number"),

        # -- Lifecycle
        *coded("state"),
        f_bool("active"),
        f_bool("auto_close"),
        *coded("escalation"),

        # -- Priority / Severity
        *coded("priority",            code_type="INTEGER"),
        *coded("urgency",             code_type="INTEGER"),
        *coded("impact",             code_type="INTEGER"),

        # -- Classification
        *coded("category"),
        *coded("subcategory"),
        f_text("u_sub_category",      pick="display_value"),
        f_text("contact_type",        pick="display_value"),

        # -- Resolution
        *coded("resolution_code"),
        *coded("u_sub_code",          code_column="sub_code",           label_column="sub_code_label"),
        f_text("cause"),
        f_text("close_notes"),

        # -- SLA
        f_bool("made_sla"),
        f_bool("u_sla_breached"),
        f_ts("sla_due"),

        # -- People FK sys_ids
        f_text("assigned_to",         column="assigned_to_sys_id"),
        f_text("assigned_to",        column="assigned_to_name",         pick="display_value"),
        f_text("opened_by",           column="opened_by_sys_id"),
        f_text("opened_by",           column="opened_by_name",          pick="display_value"),
        f_text("resolved_by",         column="resolved_by_sys_id"),
        f_text("resolved_by",         column="resolved_by_name",         pick="display_value"),
        f_text("u_owned_by",          column="owned_by_sys_id"),
        f_text("u_owned_by",          column="owned_by_name",            pick="display_value"),
        f_text("u_last_assignee",     column="last_assignee_sys_id"),
        f_text("u_last_assignee",     column="last_assignee_name",       pick="display_value"),
        f_text("contact",             column="contact_sys_id"),
        f_text("sys_created_by"),
        f_text("sys_updated_by"),

        # -- Teams
        f_text("assignment_group",          column="assignment_group_sys_id"),
        f_text("assignment_group",          column="assignment_group_name",   pick="display_value"),
        f_text("u_last_assignment_group",   column="last_assignment_group_sys_id"),
        f_text("u_last_assignment_group",   column="last_assignment_group_name", pick="display_value"),

        # -- Account
        f_text("account",             column="account_sys_id"),
        f_text("account",             column="account_name",            pick="display_value"),
        f_text("company",             column="company_sys_id"),
        f_text("company",             column="company_name",            pick="display_value"),

        # -- Timestamps
        f_ts("opened_at"),
        f_ts("closed_at"),
        f_ts("resolved_at"),
        f_ts("assigned_on",          column="assigned_at"),
        f_ts("first_response_time"),
        f_ts("sys_created_on"),
        f_ts("sys_updated_on"),
        f_date("u_date_of_occurrence"),

        # -- Effort & Workflow
        f_duration("time_worked"),
        f_int("reassignment_count"),
        f_int("sys_mod_count"),

        # -- Custom / Device
        f_text("u_tpl",              column="parking_terminal_sys_id"),
        f_text("u_tpl",              column="parking_terminal_name",    pick="display_value"),
        *coded("u_asset_device_type", code_column="device_type_code",  label_column="device_type_label"),
        f_text("u_asset_device_number", column="device_number"),
        *coded("u_fault_category",    code_column="fault_category_code", label_column="fault_category_label"),

        # -- Custom / Other
        *coded("u_financial_impact",  code_column="financial_impact_code",  label_column="financial_impact_label"),
        *coded("u_operational_impact",code_column="operational_impact_code",label_column="operational_impact_label"),
        f_text("u_service_window",    column="service_window_sys_id"),
        f_text("u_case_evaluation",   column="case_evaluation_sys_id"),

        # -- Flags
        f_bool("knowledge"),
        f_bool("proactive"),
        f_bool("needs_attention"),
        f_bool("u_best_practice_article", column="has_best_practice"),
        f_bool("u_has_incident",          column="has_incident"),
        f_bool("u_quality_check",         column="quality_check_done"),

        # -- Reference fields
        f_text("case_report",         column="case_report_sys_id"),
        *coded("approval"),
        *coded("notify"),
    ],
)


INCIDENTS = SilverTableConfig(
    bronze_table="raw_incidents",
    target_schema="silver",
    target_table="incidents",
    source_table_name="sn_customerservice_case",
    source_silver_table="incidents_flat",
    fields=[
        # -- Identity
        f_text("sys_id",                                     required=True),
        f_text("number",              column="case_number"),
        f_text("case",                column="case_title"),
        f_text("sys_class_name"),

        # -- Lifecycle
        *coded("state"),
        f_bool("active"),
        f_bool("auto_close"),
        *coded("escalation"),

        # -- Priority / Severity
        *coded("priority",            code_type="INTEGER"),
        *coded("urgency",             code_type="INTEGER"),
        *coded("impact",             code_type="INTEGER"),

        # -- Classification
        *coded("category"),
        *coded("subcategory"),
        f_text("u_sub_category",      pick="display_value"),
        f_text("contact_type",        pick="display_value"),

        # -- Resolution
        *coded("resolution_code"),
        *coded("u_sub_code",          code_column="sub_code",           label_column="sub_code_label"),
        f_text("cause"),
        f_text("close_notes"),

        # -- SLA
        f_bool("made_sla"),
        f_bool("u_sla_breached"),
        f_ts("sla_due"),

        # -- People FK
        f_text("assigned_to",         column="assigned_to_sys_id"),
        f_text("opened_by",           column="opened_by_sys_id"),
        f_text("resolved_by",         column="resolved_by_sys_id"),
        f_text("u_owned_by",          column="owned_by_sys_id"),
        f_text("u_last_assignee",     column="last_assignee_sys_id"),
        f_text("contact",             column="contact_sys_id"),
        f_text("sys_created_by"),
        f_text("sys_updated_by"),

        # -- Teams FK
        f_text("assignment_group",          column="assignment_group_sys_id"),
        f_text("u_last_assignment_group",   column="last_assignment_group_sys_id"),

        # -- Account FK
        f_text("account",             column="account_sys_id"),
        f_text("company",             column="company_sys_id"),

        # -- Timestamps
        f_ts("opened_at"),
        f_ts("closed_at"),
        f_ts("resolved_at"),
        f_ts("assigned_on",          column="assigned_at"),
        f_ts("first_response_time"),
        f_ts("sys_created_on"),
        f_ts("sys_updated_on"),
        f_date("u_date_of_occurrence"),

        # -- Effort & Workflow
        f_duration("time_worked"),
        f_int("reassignment_count"),
        f_int("sys_mod_count"),

        # -- Device FK
        f_text("u_tpl",              column="parking_terminal_sys_id"),
        *coded("u_asset_device_type", code_column="device_type_code",  label_column="device_type_label"),
        f_text("u_asset_device_number", column="device_number"),
        *coded("u_fault_category",    code_column="fault_category_code", label_column="fault_category_label"),

        # -- Impact
        *coded("u_financial_impact",  code_column="financial_impact_code",  label_column="financial_impact_label"),
        *coded("u_operational_impact",code_column="operational_impact_code",label_column="operational_impact_label"),
        f_text("u_service_window",    column="service_window_sys_id"),
        f_text("u_case_evaluation",   column="case_evaluation_sys_id"),

        # -- Flags
        f_bool("knowledge"),
        f_bool("proactive"),
        f_bool("needs_attention"),
        f_bool("u_best_practice_article", column="has_best_practice"),
        f_bool("u_has_incident",          column="has_incident"),
        f_bool("u_quality_check",         column="quality_check_done"),

        # -- Reference fields
        f_text("case_report",         column="case_report_sys_id"),
        *coded("approval"),
        *coded("notify"),
    ],
)


# -- Registry -- add new configs here ------------------------------------------

REGISTRY: dict[str, SilverTableConfig] = {
    "raw_incidents_flat": RAW_INCIDENTS_FLAT,
    "raw_incidents": INCIDENTS,
}


def get_config(bronze_table: str) -> SilverTableConfig:
    """Look up config by bronze table name."""
    config = REGISTRY.get(bronze_table)
    if not config:
        raise KeyError(
            f"No silver config registered for bronze table '{bronze_table}'. "
            f"Available: {list(REGISTRY.keys())}"
        )
    return config


def register_config(config: SilverTableConfig) -> None:
    """Register a new silver table config at runtime."""
    REGISTRY[config.bronze_table] = config
