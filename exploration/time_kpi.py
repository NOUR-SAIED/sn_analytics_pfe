"""
03e_time_kpis.py
─────────────────
Calculate the core time KPIs from datetime fields in the case table.
Shows the math explicitly — so you understand what dbt will compute.

KPIs:
  1. First Response Duration  = first_response_time - opened_at
  2. Time to Assign           = assigned_on - opened_at
  3. Resolution Duration      = resolved_at - opened_at
  4. Case Lifetime            = closed_at - opened_at
  5. Post-Resolution Time     = closed_at - resolved_at
"""

import sys, os, json, glob
from datetime import datetime

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


# ── Helpers ───────────────────────────────────────────────────────────────────

def get_val(rec, field):
    """Get the raw value from a field regardless of dict or scalar."""
    v = rec.get(field)
    if isinstance(v, dict):
        return v.get("value", "")
    return str(v) if v else ""


def get_disp(rec, field):
    v = rec.get(field)
    if isinstance(v, dict):
        return v.get("display_value", "")
    return str(v) if v else ""


def parse_dt(s):
    """Parse a ServiceNow UTC datetime string. Returns None if unparseable."""
    if not s:
        return None
    try:
        return datetime.strptime(s[:19], "%Y-%m-%d %H:%M:%S")
    except:
        return None


def diff_minutes(t1, t2):
    """Minutes between two datetimes. Returns None if either is missing."""
    if t1 is None or t2 is None:
        return None
    delta = t2 - t1
    return round(delta.total_seconds() / 60, 1)


def fmt_duration(minutes):
    """Format minutes into a human-readable string."""
    if minutes is None:
        return "—"
    if minutes < 0:
        return f"NEGATIVE ({minutes} min) ← data issue"
    if minutes < 60:
        return f"{minutes:.0f} min"
    if minutes < 1440:
        return f"{minutes/60:.1f} hrs"
    return f"{minutes/1440:.1f} days"


# ── All datetime fields present in the data ───────────────────────────────────

DATETIME_FIELDS = [
    "opened_at",
    "first_response_time",
    "assigned_on",
    "resolved_at",
    "closed_at",
    "sys_created_on",
    "sys_updated_on",
    "u_date_of_occurrence",
]

# ── Print all timestamps per record first ─────────────────────────────────────

print(f"\n{'='*90}")
print(f"  DATETIME FIELD VALUES — all timestamp fields across {N} records")
print(f"{'='*90}")
print(f"  All times are UTC (value field). Display_value is local time shown in SN UI.\n")

print(f"  {'FIELD':<30} " + "  ".join(f"REC_{i+1:<12}" for i in range(N)))
print(f"  {'-'*88}")

for field in DATETIME_FIELDS:
    vals = [get_val(rec, field)[:16] or "—" for rec in records]
    print(f"  {field:<30} " + "  ".join(f"{v:<14}" for v in vals))


# ── Calculate KPIs per record ─────────────────────────────────────────────────

print(f"\n\n{'='*90}")
print(f"  TIME KPIs — calculated from timestamps (all in minutes unless noted)")
print(f"{'='*90}\n")

kpi_results = []

for idx, rec in enumerate(records):
    opened   = parse_dt(get_val(rec, "opened_at"))
    first    = parse_dt(get_val(rec, "first_response_time"))
    assigned = parse_dt(get_val(rec, "assigned_on"))
    resolved = parse_dt(get_val(rec, "resolved_at"))
    closed   = parse_dt(get_val(rec, "closed_at"))

    kpis = {
        "number":               get_val(rec, "number"),
        "priority":             get_disp(rec, "priority"),
        "made_sla":             get_val(rec, "made_sla"),
        "first_response_min":   diff_minutes(opened, first),
        "time_to_assign_min":   diff_minutes(opened, assigned),
        "resolution_min":       diff_minutes(opened, resolved),
        "lifetime_min":         diff_minutes(opened, closed),
        "post_resolution_min":  diff_minutes(resolved, closed),
    }
    kpi_results.append(kpis)

    print(f"  Case: {kpis['number']}  |  Priority: {kpis['priority']}  |  SLA Met: {kpis['made_sla']}")
    print(f"  {'opened_at':<28}: {get_val(rec, 'opened_at')}")
    print(f"  {'first_response_time':<28}: {get_val(rec, 'first_response_time') or '—'}")
    print(f"  {'assigned_on':<28}: {get_val(rec, 'assigned_on') or '—'}")
    print(f"  {'resolved_at':<28}: {get_val(rec, 'resolved_at') or '—'}")
    print(f"  {'closed_at':<28}: {get_val(rec, 'closed_at') or '—'}")
    print(f"  ── KPIs ──────────────────────────────────────────")
    print(f"  First Response Duration  : {fmt_duration(kpis['first_response_min']):<15}  (first_response_time - opened_at)")
    print(f"  Time to Assign           : {fmt_duration(kpis['time_to_assign_min']):<15}  (assigned_on - opened_at)")
    print(f"  Resolution Duration      : {fmt_duration(kpis['resolution_min']):<15}  (resolved_at - opened_at)")
    print(f"  Full Case Lifetime       : {fmt_duration(kpis['lifetime_min']):<15}  (closed_at - opened_at)")
    print(f"  Post-Resolution Wait     : {fmt_duration(kpis['post_resolution_min']):<15}  (closed_at - resolved_at)")
    print()


# ── Aggregate summary ─────────────────────────────────────────────────────────

print(f"\n{'='*90}")
print(f"  AGGREGATE SUMMARY  (across {N} records)")
print(f"{'='*90}\n")

def safe_avg(values):
    vals = [v for v in values if v is not None and v >= 0]
    return sum(vals) / len(vals) if vals else None

def safe_min(values):
    vals = [v for v in values if v is not None and v >= 0]
    return min(vals) if vals else None

def safe_max(values):
    vals = [v for v in values if v is not None and v >= 0]
    return max(vals) if vals else None

kpi_keys = [
    ("first_response_min",  "First Response Duration"),
    ("time_to_assign_min",  "Time to Assign"),
    ("resolution_min",      "Resolution Duration"),
    ("lifetime_min",        "Full Case Lifetime"),
    ("post_resolution_min", "Post-Resolution Wait"),
]

print(f"  {'KPI':<30} {'AVG':>12}  {'MIN':>12}  {'MAX':>12}")
print(f"  {'-'*72}")

for key, label in kpi_keys:
    vals = [r[key] for r in kpi_results]
    print(
        f"  {label:<30} "
        f"{fmt_duration(safe_avg(vals)):>12}  "
        f"{fmt_duration(safe_min(vals)):>12}  "
        f"{fmt_duration(safe_max(vals)):>12}"
    )

# SLA
sla_met = sum(1 for r in kpi_results if r["made_sla"].lower() == "true")
print(f"\n  SLA Met Rate : {sla_met}/{N} = {sla_met/N*100:.0f}%")
print(f"""
  NOTE: These durations are calendar time (wall clock), not business hours.
  ServiceNow's task_sla table stores business-hours-adjusted durations.
  For accurate SLA compliance reporting you will need that table.
  For volume and trend reporting, calendar durations from this table are fine.
""")