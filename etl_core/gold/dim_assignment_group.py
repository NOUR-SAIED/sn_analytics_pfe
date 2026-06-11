"""
Assignment group dimension builder.

Source: distinct assignment groups referenced in the case table.
"""

TRUNCATE_SQL = "TRUNCATE TABLE gold.dim_assignment_group CASCADE"

INSERT_SQL = """
INSERT INTO gold.dim_assignment_group (assignment_group_sys_id, assignment_group_name)
SELECT DISTINCT sys_id, name
FROM (
    SELECT assignment_group_sys_id AS sys_id, assignment_group_name AS name
    FROM silver.sn_customerservice_case
    WHERE assignment_group_sys_id IS NOT NULL

    UNION

    SELECT last_assignment_group_sys_id AS sys_id, last_assignment_group_name AS name
    FROM silver.sn_customerservice_case
    WHERE last_assignment_group_sys_id IS NOT NULL
) combined
"""


def build() -> int:
    """Full refresh of dim_assignment_group. Returns inserted row count."""
    from .db import get_connection

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(TRUNCATE_SQL)
            cur.execute(INSERT_SQL)
            count = cur.rowcount
        conn.commit()
    return count
