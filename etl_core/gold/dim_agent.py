"""
Agent dimension builder.

Source: silver.sys_user, extended with any agent sys_id referenced
by the case table that may not appear in sys_user.
"""

TRUNCATE_SQL = "TRUNCATE TABLE gold.dim_agent CASCADE"

INSERT_SQL = """
INSERT INTO gold.dim_agent (agent_sys_id, agent_name)
SELECT u.sys_id, COALESCE(u.name, u.sys_id)
FROM silver.sys_user u

UNION

SELECT a.sys_id, COALESCE(u.name, a.sys_id)
FROM (
    SELECT assigned_to_sys_id AS sys_id FROM silver.sn_customerservice_case WHERE assigned_to_sys_id IS NOT NULL
    UNION
    SELECT opened_by_sys_id   FROM silver.sn_customerservice_case WHERE opened_by_sys_id IS NOT NULL
    UNION
    SELECT resolved_by_sys_id FROM silver.sn_customerservice_case WHERE resolved_by_sys_id IS NOT NULL
    UNION
    SELECT owned_by_sys_id    FROM silver.sn_customerservice_case WHERE owned_by_sys_id IS NOT NULL
    UNION
    SELECT last_assignee_sys_id FROM silver.sn_customerservice_case WHERE last_assignee_sys_id IS NOT NULL
) a
LEFT JOIN silver.sys_user u ON a.sys_id = u.sys_id
"""


def build() -> int:
    """Full refresh of dim_agent. Returns inserted row count."""
    from .db import get_connection

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(TRUNCATE_SQL)
            cur.execute(INSERT_SQL)
            count = cur.rowcount
        conn.commit()
    return count
