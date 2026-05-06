import os
from typing import List, Dict, Any, Optional
import psycopg2
from psycopg2 import sql
from psycopg2.extras import Json, execute_values


class PostgresJSONBLoader:

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

    # -------------------------
    # FIXED: CREATE TABLE
    # -------------------------
    def create_bronze_table(self, table_name: str = "raw_incidents") -> None:
        schema = "bronze"
        table = table_name

        full_table = sql.SQL("{}.{}").format(
            sql.Identifier(schema),
            sql.Identifier(table)
        )

        # Index name must be a plain string literal, not a composed identifier
        index_name = sql.Identifier(f"idx_{table}_sys_id")

        create_sql = sql.SQL("""
            CREATE TABLE IF NOT EXISTS {} (
                id BIGSERIAL PRIMARY KEY,
                source_table TEXT NOT NULL DEFAULT 'sn_customerservice_case',
                sys_id TEXT NOT NULL UNIQUE,
                record_json JSONB NOT NULL,
                loaded_at TIMESTAMPTZ DEFAULT NOW(),
                extraction_run_id TEXT
            )
        """).format(full_table)

        index_sql = sql.SQL("""
            CREATE INDEX IF NOT EXISTS {} ON {} (sys_id)
        """).format(index_name, full_table)  # ← both positional, no named placeholders

        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("CREATE SCHEMA IF NOT EXISTS bronze")
                cur.execute(create_sql)
                cur.execute(index_sql)
                conn.commit()

        print(f"[INFO] Table bronze.{table_name} ready")
    # -------------------------
    # FIXED: LOAD DATA
    # -------------------------
    def load_records(
        self,
        records: List[Dict[str, Any]],
        table_name: str = "raw_incidents",
        extraction_run_id: Optional[str] = None,
    ) -> int:

        if not records:
            return 0

        schema = "bronze"
        table = table_name

        full_table = sql.SQL("{}.{}").format(
            sql.Identifier(schema),
            sql.Identifier(table)
        )

        rows = []

        for record in records:
            sys_id = record.get("sys_id")

            if isinstance(sys_id, dict):
                sys_id = sys_id.get("value") or sys_id.get("display_value")

            if not sys_id:
                continue

            rows.append((
                "sn_customerservice_case",
                str(sys_id),
                Json(record),
                extraction_run_id,
            ))

        insert_sql = sql.SQL("""
            INSERT INTO {} (
                source_table,
                sys_id,
                record_json,
                extraction_run_id
            ) VALUES %s
            ON CONFLICT (sys_id)
            DO UPDATE SET
                record_json = EXCLUDED.record_json,
                loaded_at = NOW(),
                extraction_run_id = EXCLUDED.extraction_run_id
        """).format(full_table)

        with self._get_connection() as conn:
            with conn.cursor() as cur:
                execute_values(cur, insert_sql.as_string(conn), rows)
                conn.commit()

        print(f"[INFO] Loaded {len(rows)} records into bronze.{table_name}")
        return len(rows)

    # -------------------------
    # FIXED: COUNT
    # -------------------------
    def get_record_count(self, table_name: str = "raw_incidents") -> int:

        schema = "bronze"
        table = table_name

        full_table = sql.SQL("{}.{}").format(
            sql.Identifier(schema),
            sql.Identifier(table)
        )

        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(sql.SQL("SELECT COUNT(*) FROM {}").format(full_table))
                return cur.fetchone()[0]