"""
Date dimension builder.

Generates one row per calendar day from 2020-01-01 to 2030-12-31.
Idempotent — uses INSERT … ON CONFLICT DO NOTHING.
"""

from .config import DATE_DIM_START, DATE_DIM_END

BUILD_SQL = f"""
INSERT INTO gold.dim_date (date_key, full_date, year, month, day, week, weekday)
SELECT
    EXTRACT(YEAR FROM d.d) * 10000
    + EXTRACT(MONTH FROM d.d) * 100
    + EXTRACT(DAY FROM d.d) AS date_key,
    d.d::DATE                          AS full_date,
    EXTRACT(YEAR FROM d.d)::INTEGER    AS year,
    EXTRACT(MONTH FROM d.d)::INTEGER   AS month,
    EXTRACT(DAY FROM d.d)::INTEGER     AS day,
    EXTRACT(WEEK FROM d.d)::INTEGER    AS week,
    EXTRACT(DOW FROM d.d)::INTEGER     AS weekday
FROM generate_series(
    '{DATE_DIM_START}'::DATE,
    '{DATE_DIM_END}'::DATE,
    '1 day'::INTERVAL
) AS d(d)
WHERE NOT EXISTS (
    SELECT 1 FROM gold.dim_date t
    WHERE t.full_date = d.d::DATE
)
"""


def build() -> int:
    """Populate dim_date with missing days. Returns inserted row count."""
    from .db import get_connection

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(BUILD_SQL)
            count = cur.rowcount
        conn.commit()
    return count
