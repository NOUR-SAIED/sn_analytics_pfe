"""
Silver layer transformer.

Takes bronze records (JSONB dicts from ServiceNow API format) and a
SilverTableConfig, returns typed flat dicts ready for silver table insertion.
"""

from datetime import datetime, date, timezone
from typing import List, Dict, Any, Optional, Callable

from etl_core.config.silver_mappings import SilverTableConfig, FieldMapping, ComputedField


EPOCH = datetime(1970, 1, 1, tzinfo=timezone.utc)


class SilverTransformer:
    """
    Transforms bronze JSONB records into typed silver records.

    Usage:
        config = get_config("raw_incidents")
        transformer = SilverTransformer(config)
        silver_records = transformer.transform(bronze_records)
    """

    def __init__(self, config: SilverTableConfig):
        self.config = config
        self._output_columns = {f.column for f in config.fields}
        self._computed_cols = {c.column for c in config.computed}

    # -- Public API ----------------------------------------------------------

    def transform(self, bronze_records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Transform a list of bronze JSONB records into silver records."""
        result = []
        for record in bronze_records:
            transformed = self._transform_one(record)
            if transformed is not None:
                result.append(transformed)
        return result

    def derive_silver_ddl(self) -> List[str]:
        """Generate CREATE TABLE column definitions from config (for reference)."""
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
        cols = []
        for f in self.config.fields:
            pg_type = type_map.get(f.type, "TEXT")
            nullable = "" if f.required else ""
            cols.append(f"    {f.column} {pg_type}{nullable}")
        for c in self.config.computed:
            pg_type = type_map.get(c.type, "BIGINT")
            cols.append(f"    {c.column} {pg_type}")
        return cols

    # -- Internals -----------------------------------------------------------

    def _transform_one(self, record: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Transform a single bronze record. Returns None if required field missing."""
        out: Dict[str, Any] = {}

        out["bronze_id"] = record.get("id")
        out["source_table"] = record.get("source_table", self.config.source_table_name or "")
        out["extraction_run_id"] = record.get("extraction_run_id")

        for field_cfg in self.config.fields:
            value = self._extract_field(record, field_cfg)

            if value is None and field_cfg.required:
                return None

            typed = self._cast(value, field_cfg.type, field_cfg.default)
            if typed is not None:
                out[field_cfg.column] = typed

        self._compute_derived(out)

        return out

    _COMPUTED_HANDLERS: Dict[str, Callable] = {}

    @classmethod
    def _register_computed(cls, name: str, handler: Callable):
        cls._COMPUTED_HANDLERS[name] = handler

    def _compute_derived(self, out: Dict[str, Any]) -> None:
        for cf in self.config.computed:
            handler = self._COMPUTED_HANDLERS.get(cf.column)
            if handler:
                result = handler(out)
                if result is not None:
                    out[cf.column] = result

    def _extract_field(
        self,
        record: Dict[str, Any],
        cfg: FieldMapping,
    ) -> Any:
        raw = record.get(cfg.source)

        if isinstance(raw, dict):
            if cfg.pick == "raw":
                return raw
            if cfg.pick == "display_value":
                return raw.get("display_value") or raw.get("value")
            return raw.get("value") or raw.get("display_value")

        if cfg.pick == "raw":
            return raw
        return raw

    def _cast(self, value: Any, target_type: str, default: Any = None) -> Any:
        """Cast a value to the target type."""
        if value is None or value == "" or value == []:
            return default

        try:
            if target_type == "TEXT":
                return str(value)

            if target_type == "INTEGER":
                return int(float(str(value).strip()))

            if target_type == "FLOAT":
                return float(str(value).strip())

            if target_type == "BOOLEAN":
                if isinstance(value, bool):
                    return value
                s = str(value).strip().lower()
                if s in ("true", "1", "yes"):
                    return True
                if s in ("false", "0", "no"):
                    return False
                return default

            if target_type == "TIMESTAMP":
                if isinstance(value, datetime):
                    return value
                s = str(value).strip()
                for fmt in (
                    "%Y-%m-%d %H:%M:%S",
                    "%Y-%m-%dT%H:%M:%S",
                    "%Y-%m-%dT%H:%M:%SZ",
                    "%d/%m/%Y %H:%M:%S",
                    "%Y-%m-%d",
                ):
                    try:
                        return datetime.strptime(s, fmt)
                    except ValueError:
                        continue
                return default

            if target_type == "DATE":
                if isinstance(value, date):
                    return value
                s = str(value).strip()[:10]
                for fmt in ("%Y-%m-%d", "%d/%m/%Y"):
                    try:
                        return datetime.strptime(s, fmt).date()
                    except ValueError:
                        continue
                return default

            if target_type == "DURATION":
                return self._parse_duration(value, default)

            return value

        except (ValueError, TypeError, AttributeError):
            return default

    @staticmethod
    def _parse_duration(value: Any, default: Any = None) -> Optional[int]:
        """
        Parse ServiceNow duration fields to seconds.

        Handles two formats:
        - Epoch datetime: "1970-01-01 00:15:00" -> 900 seconds
        - Raw seconds:    "900" -> 900 seconds
        """
        if isinstance(value, (int, float)):
            return int(value)
        s = str(value).strip()
        if not s:
            return default
        if s.isdigit() or (s.startswith("-") and s[1:].isdigit()):
            return int(s)
        try:
            dt = datetime.strptime(s[:19], "%Y-%m-%d %H:%M:%S")
            return int((dt - datetime(1970, 1, 1)).total_seconds())
        except ValueError:
            pass
        try:
            return int(float(s))
        except (ValueError, TypeError):
            return default


# -- Register computed field handlers ------------------------------------------

def _duration_diff(out, end_field, start_field):
    end = out.get(end_field)
    start = out.get(start_field)
    if end and start and isinstance(end, datetime) and isinstance(start, datetime):
        return int((end - start).total_seconds())
    return None

SilverTransformer._register_computed("response_time_s",
    lambda o: _duration_diff(o, "first_response_time", "opened_at"))
SilverTransformer._register_computed("resolution_time_s",
    lambda o: _duration_diff(o, "resolved_at", "opened_at"))
SilverTransformer._register_computed("assign_time_s",
    lambda o: _duration_diff(o, "assigned_at", "opened_at"))
SilverTransformer._register_computed("closure_lag_s",
    lambda o: _duration_diff(o, "closed_at", "resolved_at"))
