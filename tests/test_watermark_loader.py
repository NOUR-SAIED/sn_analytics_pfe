"""
Unit tests for etl_core.loaders.postgres_watermark.PostgresWatermarkLoader.

The loader's actual SQL is exercised for real in the dbt/CI Postgres job
(it's what the extraction DAG runs against every day) - these tests cover
the decision logic around it without needing a live database: constructor
validation, and that get_watermark/set_watermark issue the right query
against a mocked connection.
"""

from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from etl_core.loaders.postgres_watermark import PostgresWatermarkLoader


def make_loader(**overrides):
    kwargs = dict(
        host="postgres",
        port=5432,
        database="elt_sn_db",
        user="elt_user",
        password="secret",
    )
    kwargs.update(overrides)
    return PostgresWatermarkLoader(**kwargs)


def test_missing_required_env_vars_raise_immediately(monkeypatch):
    for var in ("ELT_DATABASE_NAME", "ELT_DATABASE_USERNAME", "ELT_DATABASE_PASSWORD"):
        monkeypatch.delenv(var, raising=False)
    with pytest.raises(ValueError):
        PostgresWatermarkLoader(host="postgres", port=5432)


def _mock_connection(fetchone_result=None):
    """Build a MagicMock standing in for psycopg2's connection/cursor,
    supporting the `with conn:` / `with conn.cursor():` pattern the loader
    uses."""
    cursor = MagicMock()
    cursor.fetchone.return_value = fetchone_result
    cursor.__enter__.return_value = cursor
    cursor.__exit__.return_value = False

    conn = MagicMock()
    conn.cursor.return_value = cursor
    conn.__enter__.return_value = conn
    conn.__exit__.return_value = False
    return conn, cursor


@patch("etl_core.loaders.postgres_watermark.psycopg2.connect")
def test_get_watermark_returns_none_when_never_extracted(mock_connect):
    conn, cursor = _mock_connection(fetchone_result=None)
    mock_connect.return_value = conn

    loader = make_loader()
    result = loader.get_watermark("sn_customerservice_case")

    assert result is None
    # Must have looked in the right table for the right source_table.
    select_call = [c for c in cursor.execute.call_args_list if "SELECT" in c.args[0]][0]
    assert select_call.args[1] == ("sn_customerservice_case",)


@patch("etl_core.loaders.postgres_watermark.psycopg2.connect")
def test_get_watermark_returns_stored_timestamp(mock_connect):
    stored = datetime(2026, 7, 24, 9, 40, 43)
    conn, cursor = _mock_connection(fetchone_result=(stored,))
    mock_connect.return_value = conn

    loader = make_loader()
    result = loader.get_watermark("sn_customerservice_case")

    assert result == stored


@patch("etl_core.loaders.postgres_watermark.psycopg2.connect")
def test_set_watermark_upserts_and_commits(mock_connect):
    conn, cursor = _mock_connection()
    mock_connect.return_value = conn

    loader = make_loader()
    ts = datetime(2026, 9, 6, 9, 23, 17)
    loader.set_watermark("sn_customerservice_case", ts)

    upsert_call = [c for c in cursor.execute.call_args_list if "INSERT INTO" in c.args[0]][0]
    assert upsert_call.args[1] == ("sn_customerservice_case", ts)
    assert "ON CONFLICT" in upsert_call.args[0]
    assert conn.commit.called
