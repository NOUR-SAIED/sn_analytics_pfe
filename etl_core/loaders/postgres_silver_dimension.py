"""
Silver dimension table loader.

Creates and upserts dimension/lookup tables derived from
silver fact tables (e.g., silver.incidents).
"""

import os
from typing import List, Dict, Any, Optional
import psycopg2
from psycopg2 import sql
from psycopg2.extras import execute_values

from etl_core.config.silver_dimensions import SilverDimensionConfig


class PostgresDimensionLoader:
    """
    Loads dimension records into PostgreSQL tables.

    Usage:
        config = get_dimension_config("users")
        loader = PostgresDimensionLoader()
        loader.ensure_table(config)
        loader.upsert_records(config, dimension_records)
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

    def ensure_table(self, config: SilverDimensionConfig) -> None:
        schema = config.target_schema
        table = config.target_table

        full_table = sql.SQL("{}.{}").format(
            sql.Identifier(schema),
            sql.Identifier(table)
        )

        col_defs = [
            "id BIGSERIAL PRIMARY KEY",
            "sys_id TEXT NOT NULL UNIQUE",
            "name TEXT",
            "source_silver_table TEXT NOT NULL DEFAULT ''",
            "loaded_at TIMESTAMPTZ DEFAULT NOW()",
            "extraction_run_id TEXT",
        ]

        create_sql = sql.SQL("""
            CREATE TABLE IF NOT EXISTS {} (
                {}
            )
        """).format(full_table, sql.SQL(", ").join(map(sql.SQL, col_defs)))

        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(sql.SQL("CREATE SCHEMA IF NOT EXISTS {}").format(
                    sql.Identifier(schema)
                ))
                cur.execute(create_sql)
                conn.commit()

        print(f"[INFO] Dimension table {schema}.{table} ready")

    def upsert_records(
        self,
        config: SilverDimensionConfig,
        records: List[Dict[str, Any]],
    ) -> int:
        if not records:
            return 0

        schema = config.target_schema
        table = config.target_table

        full_table = sql.SQL("{}.{}").format(
            sql.Identifier(schema),
            sql.Identifier(table)
        )

        columns = list(records[0].keys())
        if "sys_id" not in columns:
            columns.insert(0, "sys_id")
            for r in records:
                if "sys_id" not in r:
                    raise ValueError("Each record must have a sys_id for upsert")

        col_idents = [sql.Identifier(c) for c in columns]

        excluded_cols = [c for c in columns if c not in ("id", "loaded_at", "extraction_run_id")]
        set_clauses = sql.SQL(", ").join(
            sql.SQL("{} = EXCLUDED.{}").format(
                sql.Identifier(c), sql.Identifier(c)
            )
            for c in excluded_cols
        )

        set_clauses = sql.SQL(", ").join([
            set_clauses,
            sql.SQL("loaded_at = NOW()"),
            sql.SQL("extraction_run_id = EXCLUDED.extraction_run_id"),
        ]) if excluded_cols else sql.SQL("loaded_at = NOW()")

        insert_sql = sql.SQL("""
            INSERT INTO {} ({})
            VALUES %s
            ON CONFLICT (sys_id)
            DO UPDATE SET {}
        """).format(
            full_table,
            sql.SQL(", ").join(col_idents),
            set_clauses,
        )

        rows = [tuple(r.get(c) for c in columns) for r in records]

        with self._get_connection() as conn:
            with conn.cursor() as cur:
                execute_values(cur, insert_sql.as_string(conn), rows)
                conn.commit()

        print(f"[INFO] Upserted {len(rows)} records into {schema}.{table}")
        return len(rows)

    def get_record_count(self, config: SilverDimensionConfig) -> int:
        schema = config.target_schema
        table = config.target_table

        full_table = sql.SQL("{}.{}").format(
            sql.Identifier(schema),
            sql.Identifier(table)
        )

        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(sql.SQL("SELECT COUNT(*) FROM {}").format(full_table))
                return cur.fetchone()[0]

    def drop_table(self, config: SilverDimensionConfig) -> None:
        schema = config.target_schema
        table = config.target_table

        full_table = sql.SQL("{}.{}").format(
            sql.Identifier(schema),
            sql.Identifier(table)
        )

        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(sql.SQL("DROP TABLE IF EXISTS {} CASCADE").format(full_table))
                conn.commit()

        print(f"[INFO] Dropped dimension table {schema}.{table}")