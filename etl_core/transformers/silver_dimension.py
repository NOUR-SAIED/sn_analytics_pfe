"""
Silver dimension transformer.

Extracts unique entity records from existing silver fact tables
(e.g., silver.incidents) and prepares them for dimension table insertion.
"""

from typing import List, Dict, Any, Optional, Set

from etl_core.config.silver_dimensions import SilverDimensionConfig


class SilverDimensionTransformer:
    """
    Extracts and deduplicates dimension entities from silver fact tables.

    Usage:
        config = get_dimension_config("users")
        transformer = SilverDimensionTransformer(config)
        dimension_records = transformer.extract_from_silver(silver_incidents_records)
    """

    def __init__(self, config: SilverDimensionConfig):
        self.config = config

    def extract_from_silver(
        self,
        silver_records: List[Dict[str, Any]],
        run_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Extract unique dimension entities from silver fact records.
        For each unique sys_id found in source_sys_id_field:
            - pick the first non-empty name from source_name_fields (priority order)
            - dedupe by sys_id
            - tag with source table and run_id
        """
        seen: Set[str] = set()
        results: List[Dict[str, Any]] = []

        for record in silver_records:
            sys_id = self._extract_sys_id(record)
            if not sys_id or sys_id in seen:
                continue

            seen.add(sys_id)
            name = self._derive_name(record)

            out: Dict[str, Any] = {
                "sys_id": sys_id,
                "name": name,
                "source_silver_table": self.config.source_silver_table,
                "extraction_run_id": run_id or "",
            }

            results.append(out)

        return results

    def _extract_sys_id(self, record: Dict[str, Any]) -> Optional[str]:
        field = self.config.source_sys_id_field
        value = record.get(field)
        if isinstance(value, dict):
            return value.get("value") or value.get("display_value") or None
        return value or None

    def _derive_name(self, record: Dict[str, Any]) -> Optional[str]:
        for field in self.config.source_name_fields:
            raw = record.get(field)
            if isinstance(raw, dict):
                name = raw.get("display_value") or raw.get("value")
            else:
                name = raw
            if name and str(name).strip():
                return str(name).strip()
        return self._extract_sys_id(record)