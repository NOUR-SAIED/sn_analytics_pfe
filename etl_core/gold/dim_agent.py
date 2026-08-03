"""
Agent dimension builder.

Source: distinct agent sys_ids referenced in the case table, enriched
with name/email/phone from silver.sys_user when available.
"""

TRUNCATE_SQL = "TRUNCATE TABLE gold.dim_agent CASCADE"

# ── Schema migration: add columns that didn't exist at table creation ─────
MIGRATE_SQL = [
    "ALTER TABLE gold.dim_agent ADD COLUMN IF NOT EXISTS email TEXT",
    "ALTER TABLE gold.dim_agent ADD COLUMN IF NOT EXISTS mobile_phone TEXT",
]

INSERT_SQL = """
INSERT INTO gold.dim_agent (agent_sys_id, agent_name, email, mobile_phone)
SELECT DISTINCT
    a.sys_id,
    CASE
        WHEN u.name IS NOT NULL AND u.name !~ '^[0-9a-f]{32}$' THEN u.name
        WHEN a.name IS NOT NULL AND a.name !~ '^[0-9a-f]{32}$' THEN a.name
        ELSE COALESCE(u.name, a.name, a.sys_id)
    END AS agent_name,
    u.email,
    u.mobile_phone
FROM (
    SELECT assigned_to_sys_id AS sys_id, assigned_to_name AS name
    FROM silver.sn_customerservice_case
    WHERE assigned_to_sys_id IS NOT NULL
    UNION
    SELECT opened_by_sys_id, opened_by_name
    FROM silver.sn_customerservice_case
    WHERE opened_by_sys_id IS NOT NULL
    UNION
    SELECT resolved_by_sys_id, resolved_by_name
    FROM silver.sn_customerservice_case
    WHERE resolved_by_sys_id IS NOT NULL
    UNION
    SELECT owned_by_sys_id, owned_by_name
    FROM silver.sn_customerservice_case
    WHERE owned_by_sys_id IS NOT NULL
    UNION
    SELECT last_assignee_sys_id, last_assignee_name
    FROM silver.sn_customerservice_case
    WHERE last_assignee_sys_id IS NOT NULL
) a
LEFT JOIN silver.sys_user u ON a.sys_id = u.sys_id
"""


def build() -> int:
    """Full refresh of dim_agent. Returns inserted row count."""
    from .db import get_connection

    with get_connection() as conn:
        with conn.cursor() as cur:
            for stmt in MIGRATE_SQL:
                cur.execute(stmt)
            cur.execute(TRUNCATE_SQL)
            cur.execute(INSERT_SQL)
            count = cur.rowcount
        conn.commit()
    return count
