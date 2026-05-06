"""
03a_field_types.py
──────────────────
Classify every field in the saved snapshot by its true type.
Groups: FK_REF, DATETIME, DATE, BOOLEAN, CHOICE, DURATION, INTEGER, TEXT, EMPTY

Run after 01_fetch_sample.py has saved data to ./data/sn_data_*.json
"""

import sys, os, json, glob

sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from sn_helpers import profile_records

# ── Load ──────────────────────────────────────────────────────────────────────
project_root = os.path.dirname(os.path.dirname(__file__))
files = glob.glob(os.path.join(project_root, "data", "sn_data_*.json"))
if not files:
    raise FileNotFoundError("No data in ./data/sn_data_*.json — run 01_fetch_sample.py first")

latest = max(files, key=os.path.getmtime)
with open(latest, encoding="utf-8") as f:
    records = json.load(f)

# ── Profile every field across all records (shared logic) ────────────────────

stats, N, ALL_FIELDS = profile_records(records)

print(f"  Loaded {N} records | {len(ALL_FIELDS)} fields each\n")


# ── Group fields by category ──────────────────────────────────────────────────

groups = {
    "FK_REF":   [],
    "DATETIME": [],
    "DATE":     [],
    "BOOLEAN":  [],
    "CHOICE":   [],
    "DURATION": [],
    "INTEGER":  [],
    "TEXT":     [],
    "EMPTY":    [],
}

for field, s in stats.items():
    if s["fill_pct"] == 0:
        groups["EMPTY"].append(field)
    elif s["is_fk"]:
        groups["FK_REF"].append(field)
    else:
        groups.get(s["subtype"] or "TEXT", groups["TEXT"]).append(field)


# ── Print ─────────────────────────────────────────────────────────────────────

DESCRIPTIONS = {
    "FK_REF":   "Foreign keys — point to another ServiceNow table via link URL",
    "DATETIME": "Timestamps — basis for all duration KPIs (opened_at, resolved_at...)",
    "DATE":     "Date-only fields",
    "BOOLEAN":  "True/False flags",
    "CHOICE":   "Dropdown enums — fixed set of coded options",
    "DURATION": "Time durations stored as seconds with human display label",
    "INTEGER":  "Numeric counts",
    "TEXT":     "Free text fields",
    "EMPTY":    "Always empty in this dataset — exclude from raw table DDL",
}

HDR = f"  {'FIELD':<44} {'FILL':>5}  {'CARD':>5}  SAMPLE"

for group, fields in groups.items():
    if not fields:
        continue

    print(f"\n{'='*80}")
    print(f"  {group}  ({len(fields)} fields)")
    print(f"  {DESCRIPTIONS[group]}")
    print(f"{'='*80}")

    if group == "EMPTY":
        # Compact list, no detail needed
        for i in range(0, len(fields), 3):
            row = fields[i:i+3]
            print("  " + "   ".join(f"{f:<40}" for f in row))
        continue

    print(HDR)
    print(f"  {'-'*78}")

    for f in sorted(fields, key=lambda x: -stats[x]["fill_pct"]):
        s      = stats[f]
        fill   = s["fill_pct"]
        card   = s["cardinality"]
        raw_s  = str(s["sample_raw"] or "")[:28]
        disp_s = str(s["sample_disp"] or "")[:30]
        tbl    = s.get("link_table") or ""

        if group == "FK_REF":
            print(f"  {f:<44} {fill:>4}%  {card:>5}  display='{disp_s}'  → [{tbl}]")

        elif group == "CHOICE" and card <= 10:
            # Show all options inline for choice fields
            pairs = list(zip(s["unique_raw"], s["unique_disp"]))[:8]
            opts  = "  |  ".join(f"{r} → '{d}'" for r, d in pairs)
            print(f"  {f:<44} {fill:>4}%  {card:>5}  {opts}")

        elif group == "BOOLEAN":
            vals = sorted(s["unique_raw"])
            print(f"  {f:<44} {fill:>4}%         values: {vals}")

        else:
            sample = f"'{raw_s}'"
            if disp_s and disp_s != raw_s:
                sample += f"  →  '{disp_s}'"
            print(f"  {f:<44} {fill:>4}%  {card:>5}  {sample}")


# ── Summary ───────────────────────────────────────────────────────────────────
print(f"\n{'='*80}")
print("  SUMMARY")
print(f"{'='*80}")
print(f"  Total fields      : {len(ALL_FIELDS)}")
for group, fields in groups.items():
    bar = "█" * len(fields)
    print(f"  {group:<10} {len(fields):>3}  {bar}")
fk_tables = sorted(set(
    s["link_table"] for s in stats.values()
    if s.get("link_table")
))
print(f"\n  FK tables detected in this data:")
for t in fk_tables:
    fk_fields = [f for f, s in stats.items() if s.get("link_table") == t]
    print(f"    [{t}]  ←  {', '.join(fk_fields)}")