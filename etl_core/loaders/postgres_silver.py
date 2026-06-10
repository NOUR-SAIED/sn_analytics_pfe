"""
Silver layer PostgreSQL loader.

Creates silver tables from a SilverTableConfig and upserts transformed records.
Uses the same connection pattern as PostgresJSONBLoader.
"""

import os
from typing import List, Dict, Any, Optional
import psycopg2
from psycopg2 import sql
from psycopg2.extras import execute_values

from etl_core.config.silver_mappings import SilverTableConfig, FieldMapping


class PostgresSilverLoader:
    """
    Loads transformed (silver) records into typed PostgreSQL tables.

    Usage:
        config = get_config("raw_incidents")
        loader = PostgresSilverLoader()
        loader.ensure_table(config)
        loader.upsert_records(config, silver_records)
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

    # -------------------------
    # CREATE TABLE
    # -------------------------
    def ensure_table(self, config: SilverTableConfig) -> None:
        """
        Create the silver table if it does not exist.
        Schema is derived from the field mappings in the config.
        """
        schema = config.target_schema
        table = config.target_table

        full_table = sql.SQL("{}.{}").format(
            sql.Identifier(schema),
            sql.Identifier(table)
        )

        type_map = {
            "TEXT": "TEXT",
            "INTEGER": "BIGINT",
            "FLOAT": "NUMERIC",
            "BOOLEAN": "BOOLEAN",
            "TIMESTAMP": "TIMESTAMPTZ",
            "DATE": "DATE",
            "DURATION": "BIGINT",
            "JSONB": "JSONB",
        }

        base_cols = {"id", "bronze_id", "source_table", "sys_id", "loaded_at", "extraction_run_id"}

        col_defs = [
            "id BIGSERIAL PRIMARY KEY",
            "bronze_id BIGINT",
            "source_table TEXT NOT NULL DEFAULT ''",
            "sys_id TEXT NOT NULL UNIQUE",
        ]

        for f in config.fields:
            if f.column in base_cols:
                continue
            pg_type = type_map.get(f.type, "TEXT")
            nullable = " NOT NULL" if f.required else ""
            col_defs.append(f"{f.column} {pg_type}{nullable}")

        col_defs.extend([
            "loaded_at TIMESTAMPTZ DEFAULT NOW()",
            "extraction_run_id TEXT",
        ])

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

        print(f"[INFO] Silver table {schema}.{table} ready")

    # -------------------------
    # UPSERT
    # -------------------------
    def upsert_records(
        self,
        config: SilverTableConfig,
        records: List[Dict[str, Any]],
    ) -> int:
        """
        Upsert transformed records into the silver table.
        Matching is done on sys_id column.
        """
        if not records:
            return 0

        schema = config.target_schema
        table = config.target_table

        full_table = sql.SQL("{}.{}").format(
            sql.Identifier(schema),
            sql.Identifier(table)
        )

        # Determine columns from the first record
        columns = list(records[0].keys())
        # Always include sys_id
        if "sys_id" not in columns:
            columns.insert(0, "sys_id")
            for r in records:
                if "sys_id" not in r:
                    raise ValueError("Each record must have a sys_id for upsert")

        # Build column identifiers
        col_idents = [sql.Identifier(c) for c in columns]

        # Build value placeholders
        values_placeholder = sql.SQL("({})").format(
            sql.SQL(", ").join(sql.Placeholder() * len(columns))
        )

        # Build ON CONFLICT SET clause for non-id columns
        excluded_cols = [c for c in columns if c not in ("id", "sys_id", "bronze_id", "loaded_at", "extraction_run_id")]
        set_clauses = sql.SQL(", ").join(
            sql.SQL("{} = EXCLUDED.{}").format(
                sql.Identifier(c), sql.Identifier(c)
            )
            for c in excluded_cols
        )

        # Always update loaded_at and extraction_run_id
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

        rows = []
        for r in records:
            rows.append(tuple(r.get(c) for c in columns))

        with self._get_connection() as conn:
            with conn.cursor() as cur:
                execute_values(cur, insert_sql.as_string(conn), rows)
                conn.commit()

        print(f"[INFO] Upserted {len(rows)} records into {schema}.{table}")
        return len(rows)

    # -------------------------
    # COUNT
    # -------------------------
    def get_record_count(self, config: SilverTableConfig) -> int:
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

    # -------------------------
    # DROP TABLE
    # -------------------------
    def drop_table(self, config: SilverTableConfig) -> None:
        """Drop the silver table if it exists (used for schema migration)."""
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

        print(f"[INFO] Dropped table {schema}.{table}")

    # -------------------------
    # DELETE (for refresh)
    # -------------------------
    def truncate(self, config: SilverTableConfig) -> None:
        schema = config.target_schema
        table = config.target_table

        full_table = sql.SQL("{}.{}").format(
            sql.Identifier(schema),
            sql.Identifier(table)
        )

        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(sql.SQL("TRUNCATE TABLE {}").format(full_table))
                conn.commit()

        print(f"[INFO] Truncated {schema}.{table}")
