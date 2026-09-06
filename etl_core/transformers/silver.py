"""
Silver layer transformer.

Takes bronze/silver raw records and a SilverTableConfig,
returns typed flat dicts ready for silver table insertion.

Computed fields (response_time_s, resolution_time_s, etc.)
are deferred to the gold layer — documented in docs/gold_computed_fields.md
"""

from datetime import datetime, date
from typing import List, Dict, Any, Optional

from etl_core.config.silver_mappings import SilverTableConfig, FieldMapping


class SilverTransformer:
    """
    Transforms bronze/silver raw records into typed silver records.

    Usage:
        config = get_config("raw_incidents_flat")
        transformer = SilverTransformer(config)
        silver_records = transformer.transform(bronze_records)
    """

    def __init__(self, config: SilverTableConfig):
        self.config = config
        self._output_columns = {f.column for f in config.fields}

    def transform(self, records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Transform a list of bronze/silver records into silver records."""
        result = []
        for record in records:
            transformed = self._transform_one(record)
            if transformed is not None:
                result.append(transformed)
        return result

    def _transform_one(self, record: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Transform a single record. Returns None if required field missing."""
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

        return out

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