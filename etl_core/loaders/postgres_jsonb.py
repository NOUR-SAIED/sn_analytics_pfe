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
                source_table TEXT NOT NULL,
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
        source_table: str,
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
                source_table,
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

    # -------------------------
    # READ: fetch bronze records
    # -------------------------
    def fetch_records(
        self,
        table_name: str = "raw_incidents",
        source_table: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """
        Fetch records from a bronze table, returning them as dicts
        with record_json unfolded alongside envelope columns.

        Args:
            table_name: Bronze table name (e.g. 'raw_incidents')
            source_table: Optional filter by source_table column
            limit: Optional row limit

        Returns:
            List of dicts combining envelope columns + record_json contents
        """
        schema = "bronze"

        full_table = sql.SQL("{}.{}").format(
            sql.Identifier(schema),
            sql.Identifier(table_name)
        )

        query = sql.SQL("""
            SELECT id, source_table, sys_id, record_json, loaded_at, extraction_run_id
            FROM {}
        """).format(full_table)

        conditions = []
        if source_table:
            conditions.append(sql.SQL("source_table = {}").format(sql.Literal(source_table)))

        if conditions:
            query = sql.SQL("{} WHERE {}").format(
                query, sql.SQL(" AND ").join(conditions)
            )

        query = sql.SQL("{} ORDER BY id ASC").format(query)

        if limit:
            query = sql.SQL("{} LIMIT {}").format(query, sql.Literal(limit))

        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query)
                rows = cur.fetchall()
                columns = [desc[0] for desc in cur.description]

        records = []
        for row in rows:
            d = dict(zip(columns, row))
            record_json = d.pop("record_json", {})
            if isinstance(record_json, dict):
                d.update(record_json)
            records.append(d)

        print(f"[INFO] Read {len(records)} records from bronze.{table_name}")
        return records