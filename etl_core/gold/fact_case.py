"""
Fact case table builder.

One row per customer service case with SLA metrics pivoted
directly into the fact row.
"""

from .config import RESPONSE_SLA_NAME, RESOLUTION_SLA_NAME

TRUNCATE_SQL = "TRUNCATE TABLE gold.fact_case"

INSERT_SQL = f"""
WITH sla_pivot AS (
    SELECT
        ts.task_sys_id,
        MAX(CASE WHEN cs.name = '{RESPONSE_SLA_NAME}'  THEN ts.duration END)
            AS response_sla_duration,
        MAX(CASE WHEN cs.name = '{RESPONSE_SLA_NAME}'  THEN ts.percentage END)
            AS response_sla_percentage,
        BOOL_OR(CASE WHEN cs.name = '{RESPONSE_SLA_NAME}'  THEN ts.has_breached END)
            AS response_sla_has_breached,
        MAX(CASE WHEN cs.name = '{RESOLUTION_SLA_NAME}' THEN ts.duration END)
            AS resolution_sla_duration,
        MAX(CASE WHEN cs.name = '{RESOLUTION_SLA_NAME}' THEN ts.percentage END)
            AS resolution_sla_percentage,
        BOOL_OR(CASE WHEN cs.name = '{RESOLUTION_SLA_NAME}' THEN ts.has_breached END)
            AS resolution_sla_has_breached
    FROM silver.task_sla ts
    JOIN silver.contract_sla cs ON ts.sla_sys_id = cs.sys_id
    WHERE cs.name IN ('{RESPONSE_SLA_NAME}', '{RESOLUTION_SLA_NAME}')
    GROUP BY ts.task_sys_id
)
INSERT INTO gold.fact_case (
    case_id,              sys_id,              case_number,
    opened_date_key,      assigned_date_key,   first_response_date_key,
    resolved_date_key,    closed_date_key,     occurrence_date_key,
    state_code,           state_label,         auto_close,
    approval_code,        approval_label,
    priority_code,        priority_label,      urgency_code,
    urgency_label,        impact_code,         impact_label,
    category_label,       subcategory_label,   u_sub_category,
    cause,                resolution_code,     resolution_code_label,
    sub_code,             sub_code_label,
    assigned_to_sys_id,   opened_by_sys_id,    resolved_by_sys_id,
    owned_by_sys_id,      last_assignee_sys_id,
    assignment_group_sys_id,                  last_assignment_group_sys_id,
    parking_terminal_sys_id,
    device_type_label,
    response_sla_duration,    response_sla_percentage,    response_sla_has_breached,
    resolution_sla_duration,  resolution_sla_percentage,  resolution_sla_has_breached,
    time_worked,              reassignment_count,
    sys_created_on,           sys_updated_on,
    loaded_at
)
SELECT
    c.sys_id,
    c.sys_id,
    c.case_number,

    do_.date_key,
    da_.date_key,
    dfr_.date_key,
    dr_.date_key,
    dc_.date_key,
    docc_.date_key,

    c.state_code,
    c.state_label,
    c.auto_close,
    c.approval_code,
    c.approval_label,

    c.priority_code,
    c.priority_label,
    c.urgency_code,
    c.urgency_label,
    c.impact_code,
    c.impact_label,

    c.category_label,
    c.subcategory_label,
    c.u_sub_category,
    c.cause,
    c.resolution_code,
    c.resolution_code_label,
    c.sub_code,
    c.sub_code_label,

    c.assigned_to_sys_id,
    c.opened_by_sys_id,
    c.resolved_by_sys_id,
    c.owned_by_sys_id,
    c.last_assignee_sys_id,

    c.assignment_group_sys_id,
    c.last_assignment_group_sys_id,
    c.parking_terminal_sys_id,

    c.device_type_label,

    sp.response_sla_duration,
    sp.response_sla_percentage,
    sp.response_sla_has_breached,
    sp.resolution_sla_duration,
    sp.resolution_sla_percentage,
    sp.resolution_sla_has_breached,

    c.time_worked,
    c.reassignment_count,

    c.sys_created_on,
    c.sys_updated_on,

    NOW()

FROM silver.sn_customerservice_case c
LEFT JOIN sla_pivot sp ON c.sys_id = sp.task_sys_id

LEFT JOIN gold.dim_date do_
    ON do_.full_date = c.opened_at::DATE
LEFT JOIN gold.dim_date da_
    ON da_.full_date = c.assigned_at::DATE
LEFT JOIN gold.dim_date dfr_
    ON dfr_.full_date = c.first_response_time::DATE
LEFT JOIN gold.dim_date dr_
    ON dr_.full_date = c.resolved_at::DATE
LEFT JOIN gold.dim_date dc_
    ON dc_.full_date = c.closed_at::DATE
LEFT JOIN gold.dim_date docc_
    ON docc_.full_date = c.u_date_of_occurrence
"""


def build() -> int:
    """Full refresh of fact_case. Returns inserted row count."""
    from .db import get_connection

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(TRUNCATE_SQL)
            cur.execute(INSERT_SQL)
            count = cur.rowcount
        conn.commit()
    return count
