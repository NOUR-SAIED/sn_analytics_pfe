"""
Terminal dimension builder.

Source: distinct parking terminals referenced in the case table.
"""

TRUNCATE_SQL = "TRUNCATE TABLE gold.dim_terminal CASCADE"

INSERT_SQL = """
INSERT INTO gold.dim_terminal (terminal_sys_id, terminal_name)
SELECT DISTINCT parking_terminal_sys_id, parking_terminal_name
FROM silver.sn_customerservice_case
WHERE parking_terminal_sys_id IS NOT NULL
"""


def build() -> int:
    """Full refresh of dim_terminal. Returns inserted row count."""
    from .db import get_connection

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(TRUNCATE_SQL)
            cur.execute(INSERT_SQL)
            count = cur.rowcount
        conn.commit()
    return count
