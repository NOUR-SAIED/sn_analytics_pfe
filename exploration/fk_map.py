"""
03b_fk_map.py
─────────────
Focus exclusively on FK_REF fields.
For each one: which SN table it links to, fill rate, unique sys_ids seen,
and all display values (human-readable names) found in the sample.

This output = your table access request to the stakeholder.
"""

import sys, os, json, glob
from collections import defaultdict

sys.path.append(os.path.dirname(os.path.dirname(__file__)))

# ── Load ──────────────────────────────────────────────────────────────────────
project_root = os.path.dirname(os.path.dirname(__file__))
files = glob.glob(os.path.join(project_root, "data", "sn_data_*.json"))
if not files:
    raise FileNotFoundError("No data in ./data/sn_data_*.json")

latest = max(files, key=os.path.getmtime)
with open(latest, encoding="utf-8") as f:
    records = json.load(f)

N = len(records)


# ── Parse FK fields only ──────────────────────────────────────────────────────

fk_stats = {}   # field → {link_table, null_count, sys_ids, displays, sample_link}

for rec in records:
    for field, value in rec.items():
        if not isinstance(value, dict):
            continue
        link = value.get("link")
        if not link:
            continue   # not a true FK

        raw     = value.get("value", "")
        display = value.get("display_value", "")

        if field not in fk_stats:
            # Extract table name from the link URL
            parts      = link.split("/table/")
            link_table = parts[1].split("/")[0] if len(parts) > 1 else "UNKNOWN"

            fk_stats[field] = {
                "link_table":   link_table,
                "null_count":   0,
                "sys_ids":      set(),
                "displays":     set(),
                "sample_link":  link,
            }

        s = fk_stats[field]

        if not raw and not display:
            s["null_count"] += 1
        else:
            if raw:
                s["sys_ids"].add(raw)
            if display:
                s["displays"].add(display)

# Compute fill rate
for s in fk_stats.values():
    s["fill_pct"] = round((N - s["null_count"]) / N * 100)

# Group fields by the table they point to
by_table = defaultdict(list)
for field, s in fk_stats.items():
    by_table[s["link_table"]].append(field)


# ── Print ─────────────────────────────────────────────────────────────────────

print(f"  {N} records  |  {len(fk_stats)} FK fields found\n")

for table in sorted(by_table.keys()):
    fields = by_table[table]
    print(f"\n{'='*80}")
    print(f"  TARGET TABLE: [{table}]")
    print(f"  Fields that reference it: {len(fields)}")
    print(f"  Sample link: {fk_stats[fields[0]]['sample_link'][:90]}")
    print(f"{'='*80}")
    print(f"  {'FIELD':<40} {'FILL':>5}  {'UNIQUE IDS':>10}  DISPLAY VALUES SEEN")
    print(f"  {'-'*78}")

    for field in sorted(fields, key=lambda x: -fk_stats[x]["fill_pct"]):
        s        = fk_stats[field]
        fill     = s["fill_pct"]
        uid      = len(s["sys_ids"])
        displays = sorted(s["displays"])[:5]   # show up to 5 unique display values
        disp_str = "  |  ".join(f"'{d}'" for d in displays) if displays else "— (empty)"
        print(f"  {field:<40} {fill:>4}%  {uid:>10}  {disp_str}")


# ── Access request summary ────────────────────────────────────────────────────

print(f"\n{'='*80}")
print("  TABLES TO REQUEST ACCESS TO")
print(f"{'='*80}\n")

priority_map = {
    "sys_user":       "HIGH  — resolves assigned_to, resolved_by, opened_by → agent names",
    "sys_user_group": "HIGH  — resolves assignment_group → team names",
    "core_company":   "HIGH  — resolves account/company → customer details",
    "task_sla":       "HIGH  — SLA compliance detail per case",
    "metric_instance":"MED   — pre-calculated durations (resolution, first response)",
}

detected_tables = sorted(by_table.keys())
for t in detected_tables:
    fields_for_t = by_table[t]
    fill_rates   = [fk_stats[f]["fill_pct"] for f in fields_for_t]
    max_fill     = max(fill_rates)
    note         = priority_map.get(t, "LOW   — check if needed for your reports")
    print(f"  [{t}]")
    print(f"    Priority    : {note}")
    print(f"    Referenced by fields: {', '.join(fields_for_t)}")
    print(f"    Max fill rate in sample: {max_fill}%")
    print()