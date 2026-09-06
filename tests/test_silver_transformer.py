"""
Unit tests for etl_core.transformers.silver.SilverTransformer.

Chosen as the primary CI unit-test target because it's pure logic (no
network or database calls) that real ServiceNow data has actually broken
before -- ServiceNow's REST API returns {value, display_value} dicts for
reference/choice fields, durations arrive as either epoch-anchored
datetimes or raw seconds, and required-field handling decides whether a
malformed record is silently dropped. All three deserve real tests, not a
smoke test.
"""

from datetime import date, datetime

import pytest

from etl_core.config.silver_mappings import FieldMapping, SilverTableConfig
from etl_core.transformers.silver import SilverTransformer


def make_transformer(*fields: FieldMapping) -> SilverTransformer:
    config = SilverTableConfig(bronze_table="raw_incidents", fields=list(fields))
    return SilverTransformer(config)


# -- Field extraction: ServiceNow's {value, display_value} shape -------------


def test_extract_picks_value_by_default():
    transformer = make_transformer(FieldMapping(source="priority", column="priority_code"))
    out = transformer.transform([{"priority": {"value": "1", "display_value": "Critical"}}])
    assert out[0]["priority_code"] == "1"


def test_extract_picks_display_value_when_configured():
    transformer = make_transformer(
        FieldMapping(source="priority", column="priority_label", pick="display_value")
    )
    out = transformer.transform([{"priority": {"value": "1", "display_value": "Critical"}}])
    assert out[0]["priority_label"] == "Critical"


def test_extract_falls_back_to_display_value_when_value_missing():
    # ServiceNow occasionally omits "value" on a reference field, but not
    # "display_value" - the default "value" pick should still recover it.
    transformer = make_transformer(FieldMapping(source="priority", column="priority_code"))
    out = transformer.transform([{"priority": {"display_value": "Critical"}}])
    assert out[0]["priority_code"] == "Critical"


def test_extract_raw_preserves_dict_structure_when_type_is_jsonb():
    # pick="raw" skips the .get("value")/.get("display_value") extraction;
    # type="JSONB" is what then keeps _cast from stringifying the result
    # (every other type coerces to str/int/etc, collapsing the dict).
    transformer = make_transformer(
        FieldMapping(source="meta", column="meta_raw", pick="raw", type="JSONB")
    )
    out = transformer.transform([{"meta": {"value": "x", "display_value": "y"}}])
    assert out[0]["meta_raw"] == {"value": "x", "display_value": "y"}


def test_extract_raw_with_default_text_type_stringifies_dicts():
    # Documented as "for simple fields" - pairing pick="raw" with the
    # default TEXT type on a dict-shaped field stringifies it via
    # _cast's `str(value)` branch. Real configs never do this (grep
    # confirms pick="raw" isn't used anywhere in silver_mappings.py
    # today), but the behavior should stay predictable if it ever is.
    transformer = make_transformer(FieldMapping(source="meta", column="meta_raw", pick="raw"))
    out = transformer.transform([{"meta": {"value": "x", "display_value": "y"}}])
    assert out[0]["meta_raw"] == str({"value": "x", "display_value": "y"})


def test_extract_handles_plain_scalar_field():
    # Not every ServiceNow field is a {value, display_value} dict - simple
    # fields (e.g. a plain string column) come through as-is.
    transformer = make_transformer(FieldMapping(source="case_number", column="case_number"))
    out = transformer.transform([{"case_number": "CS0012345"}])
    assert out[0]["case_number"] == "CS0012345"


# -- Type casting --------------------------------------------------------------


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("42", 42),
        (42, 42),
        ("42.0", 42),
    ],
)
def test_cast_integer(raw, expected):
    transformer = make_transformer(FieldMapping(source="x", column="x", type="INTEGER"))
    out = transformer.transform([{"x": {"value": raw}}])
    assert out[0]["x"] == expected


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("true", True),
        ("1", True),
        ("yes", True),
        ("false", False),
        ("0", False),
        ("no", False),
    ],
)
def test_cast_boolean(raw, expected):
    transformer = make_transformer(FieldMapping(source="x", column="x", type="BOOLEAN"))
    out = transformer.transform([{"x": {"value": raw}}])
    assert out[0]["x"] is expected


def test_cast_boolean_unparseable_falls_back_to_default():
    transformer = make_transformer(
        FieldMapping(source="x", column="x", type="BOOLEAN", default=False)
    )
    out = transformer.transform([{"x": {"value": "maybe"}}])
    assert out[0]["x"] is False


@pytest.mark.parametrize(
    "raw,expected_fmt_ok",
    [
        ("2026-07-24 09:40:43", True),
        ("2026-07-24T09:40:43", True),
        ("2026-07-24T09:40:43Z", True),
        ("24/07/2026 09:40:43", True),
        ("not-a-date", False),
    ],
)
def test_cast_timestamp_accepts_all_known_servicenow_formats(raw, expected_fmt_ok):
    transformer = make_transformer(
        FieldMapping(source="x", column="x", type="TIMESTAMP", default=None)
    )
    out = transformer.transform([{"x": {"value": raw}}])
    if expected_fmt_ok:
        assert isinstance(out[0]["x"], datetime)
    else:
        assert out[0].get("x") is None


def test_cast_date():
    transformer = make_transformer(FieldMapping(source="x", column="x", type="DATE"))
    out = transformer.transform([{"x": {"value": "2026-07-24"}}])
    assert out[0]["x"] == date(2026, 7, 24)


def test_cast_missing_value_uses_default():
    transformer = make_transformer(
        FieldMapping(source="x", column="x", type="INTEGER", default=0)
    )
    out = transformer.transform([{"x": {"value": None}}])
    assert out[0]["x"] == 0


def test_cast_unparseable_number_falls_back_to_default_without_raising():
    transformer = make_transformer(
        FieldMapping(source="x", column="x", type="INTEGER", default=-1)
    )
    out = transformer.transform([{"x": {"value": "not-a-number"}}])
    assert out[0]["x"] == -1


# -- Duration parsing: the two real ServiceNow shapes --------------------------


@pytest.mark.parametrize(
    "raw,expected_seconds",
    [
        ("1970-01-01 00:15:00", 900),  # epoch-anchored datetime -> 900s
        ("900", 900),  # raw seconds as a string
        (900, 900),  # raw seconds as a number
        ("-30", -30),  # negative durations are passed through, not rejected
    ],
)
def test_duration_parsing_handles_both_servicenow_shapes(raw, expected_seconds):
    transformer = make_transformer(FieldMapping(source="x", column="x", type="DURATION"))
    out = transformer.transform([{"x": {"value": raw}}])
    assert out[0]["x"] == expected_seconds


def test_duration_unparseable_falls_back_to_default():
    transformer = make_transformer(
        FieldMapping(source="x", column="x", type="DURATION", default=0)
    )
    out = transformer.transform([{"x": {"value": "garbage"}}])
    assert out[0]["x"] == 0


# -- Required-field handling: a malformed record must be dropped, not crash ----


def test_record_missing_required_field_is_dropped():
    transformer = make_transformer(
        FieldMapping(source="sys_id", column="sys_id", required=True),
        FieldMapping(source="case_number", column="case_number"),
    )
    records = [
        {"sys_id": {"value": "abc123"}, "case_number": "CS001"},
        {"case_number": "CS002"},  # missing sys_id -> must be dropped
    ]
    out = transformer.transform(records)
    assert len(out) == 1
    assert out[0]["case_number"] == "CS001"


def test_record_missing_optional_field_is_kept_with_default():
    transformer = make_transformer(
        FieldMapping(source="sys_id", column="sys_id", required=True),
        FieldMapping(source="priority", column="priority_label", default="Unknown"),
    )
    out = transformer.transform([{"sys_id": {"value": "abc123"}}])
    assert len(out) == 1
    assert out[0]["priority_label"] == "Unknown"


def test_transform_preserves_bookkeeping_columns():
    transformer = make_transformer(FieldMapping(source="case_number", column="case_number"))
    out = transformer.transform(
        [{"id": 7, "source_table": "raw_incidents", "extraction_run_id": "run-1", "case_number": "CS001"}]
    )
    assert out[0]["bronze_id"] == 7
    assert out[0]["source_table"] == "raw_incidents"
    assert out[0]["extraction_run_id"] == "run-1"
