import os
from datetime import datetime
from typing import Optional

import psycopg2


class PostgresWatermarkLoader:
    """
    Tracks per-table extraction watermarks in etl_control.extraction_watermarks.

    One row per ServiceNow source table. Read before extraction to scope the
    query to records updated since the last successful run; written after
    extraction succeeds, and only then - a failed run leaves the watermark
    where it was, so the next run safely re-covers the same window instead of
    silently skipping records.
    """

    def __init__(
        self,
        host: Optional[str] = None,
        port: Optional[int] = None,
        database: Optional[str] = None,
        user: Optional[str] = None,
        password: Optional[str] = None,
    ):
        self.host = host or os.getenv("POSTGRES_CONN_HOST", "postgres")
        self.port = int(port or os.getenv("POSTGRES_CONN_PORT", "5432"))
        self.database = database or os.getenv("ELT_DATABASE_NAME")
        self.user = user or os.getenv("ELT_DATABASE_USERNAME", "elt_user")
        self.password = password or os.getenv("ELT_DATABASE_PASSWORD")

        if not all([self.database, self.user, self.password]):
            raise ValueError("Missing PostgreSQL env vars")

    def _get_connection(self):
        return psycopg2.connect(
            host=self.host,
            port=self.port,
            dbname=self.database,
            user=self.user,
            password=self.password,
        )

    def ensure_table(self) -> None:
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("CREATE SCHEMA IF NOT EXISTS etl_control")
                cur.execute(
                    """
                    CREATE TABLE IF NOT EXISTS etl_control.extraction_watermarks (
                        source_table       TEXT PRIMARY KEY,
                        last_extracted_at  TIMESTAMP NOT NULL,
                        updated_at         TIMESTAMP NOT NULL DEFAULT now()
                    )
                    """
                )
                conn.commit()

    def get_watermark(self, source_table: str) -> Optional[datetime]:
        """Return the stored high-water mark for this table, or None if it has
        never been extracted incrementally yet (caller should do a full pull)."""
        self.ensure_table()
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT last_extracted_at FROM etl_control.extraction_watermarks "
                    "WHERE source_table = %s",
                    (source_table,),
                )
                row = cur.fetchone()
                return row[0] if row else None

    def set_watermark(self, source_table: str, ts: datetime) -> None:
        self.ensure_table()
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO etl_control.extraction_watermarks
                        (source_table, last_extracted_at, updated_at)
                    VALUES (%s, %s, now())
                    ON CONFLICT (source_table) DO UPDATE
                        SET last_extracted_at = EXCLUDED.last_extracted_at,
                            updated_at = now()
                    """,
                    (source_table, ts),
                )
                conn.commit()

        print(f"[WATERMARK] {source_table} advanced to {ts}")
