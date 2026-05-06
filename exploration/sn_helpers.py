"""
sn_helpers.py
─────────────
Shared helpers for ServiceNow data analysis.

Provides:
  - parse_cell: break ServiceNow field values into (kind, raw, display, link)
  - detect_subtype: classify raw values as DATETIME, BOOLEAN, CHOICE, INTEGER, TEXT, EMPTY, etc.
    - profile_records: build per-field stats (fill rate, cardinality, samples, FK table)
"""

from datetime import datetime


def parse_cell(value):
    """
    Break any ServiceNow field value into its parts.

    Returns (kind, raw, display, link):
      FK_REF  — dict with 'link' key  → true foreign key, value is a sys_id
      SIMPLE  — dict without 'link'   → choice/boolean/datetime wrapped by display_value
      NULL    — empty or None
    """
    if isinstance(value, dict):
        link    = value.get("link")
        raw     = value.get("value", "")
        display = value.get("display_value", "")
        # Treat empty dict shells with no link and no value/display as NULL
        if not link and not str(raw).strip() and not str(display).strip():
            return "NULL", "", "", None
        return ("FK_REF" if link else "SIMPLE"), raw, display, link
    if value is None or value == "":
        return "NULL", "", "", None
    return "SIMPLE", str(value), str(value), None


def detect_subtype(raw, display):
    """
    Classify a raw value into its semantic type.

    Returns one of: EMPTY, DATETIME, DATE, BOOLEAN, CHOICE, DURATION, INTEGER, TEXT
    """
    s = str(raw).strip()
    if not s:
        return "EMPTY"
    try:
        datetime.strptime(s[:19], "%Y-%m-%d %H:%M:%S")
        return "DATETIME"
    except:
        pass
    if len(s) == 10 and s[4] == "-" and s[7] == "-":
        return "DATE"
    if s.lower() in ("true", "false"):
        return "BOOLEAN"
    # ✅ CHOICE before INTEGER — if raw differs from display, it's a coded dropdown
    # even if the code happens to be a number like "3" or "1001"
    if raw != display and display:
        return "CHOICE"
    if s.isdigit():
        return "INTEGER"
    d = str(display).lower()
    if any(w in d for w in ("second", "minute", "hour")) and s.lstrip("-").isdigit():
        return "DURATION"
    return "TEXT"


def profile_records(records):
    """
    Profile all fields across records using the shared parse and subtype logic.

    Returns:
      stats: dict keyed by field name with profiling metadata
      n_records: total number of records
      all_fields: field list from the snapshot schema
    """
    if not records:
        return {}, 0, []

    n_records = len(records)
    all_fields = list(records[0].keys())
    stats = {}

    for rec in records:
        for field in all_fields:
            value = rec.get(field)
            kind, raw, disp, link = parse_cell(value)

            if field not in stats:
                stats[field] = {
                    "is_fk": False,
                    "link_table": None,
                    "subtype": None,
                    "null_count": 0,
                    "unique_raw": set(),
                    "unique_disp": set(),
                    "sample_raw": None,
                    "sample_disp": None,
                }

            s = stats[field]

            if kind == "NULL":
                s["null_count"] += 1
                continue

            if link:
                s["is_fk"] = True
                parts = link.split("/table/")
                if len(parts) > 1:
                    s["link_table"] = parts[1].split("/")[0]

            if raw:
                s["unique_raw"].add(raw)
                if s["sample_raw"] is None:
                    s["sample_raw"] = raw

            if disp and disp != raw:
                s["unique_disp"].add(disp)
                if s["sample_disp"] is None:
                    s["sample_disp"] = disp

            if s["subtype"] is None and not s["is_fk"]:
                s["subtype"] = detect_subtype(raw, disp)

    for field, s in stats.items():
        s["fill_pct"] = round((n_records - s["null_count"]) / n_records * 100)
        s["cardinality"] = len(s["unique_raw"])

    return stats, n_records, all_fields
