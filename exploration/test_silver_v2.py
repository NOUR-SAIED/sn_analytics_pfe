"""
Test the updated silver transformer with the new config.
"""
import json, sys
sys.path.insert(0, ".")

from etl_core.config.silver_mappings import get_config
from etl_core.transformers.silver import SilverTransformer

with open("data/sn_data_2026-05-02.json") as f:
    data = json.load(f)

config = get_config("raw_incidents")
transformer = SilverTransformer(config)
silver = transformer.transform(data)

r = silver[0]

print("=== KEY FIXES VERIFIED ===")
print()

# 1. time_worked fix
tw_raw = data[0]["time_worked"]
print(f"1. time_worked:")
print(f"   raw value = {tw_raw['value']!r}")
print(f"   silver    = {r.get('time_worked')!r} (seconds)")
print()

# 2. Code + Label pairs
print("2. Code + Label pairs:")
for fld in ["priority", "urgency", "impact", "state", "category", "resolution_code", "escalation"]:
    code = r.get(f"{fld}_code")
    label = r.get(f"{fld}_label")
    print(f"   {fld}: code={code!r}, label={label!r}")
print()

# 3. Computed durations
print("3. Computed durations:")
for cf in ["response_time_s", "resolution_time_s", "assign_time_s", "closure_lag_s"]:
    val = r.get(cf)
    if val is not None:
        print(f"   {cf}: {val}s ({val/60:.1f} min)")
    else:
        print(f"   {cf}: None")
print()

# 4. Quick stats
null_count = sum(1 for v in r.values() if v is None or v == "")
print(f"4. Stats: {len(config.fields)} fields + {len(config.computed)} computed = {len(r)} columns, {null_count} null/empty")

# 5. time_worked across all records
print()
print("5. time_worked across all records:")
for i, rec in enumerate(silver):
    tw = rec.get("time_worked")
    print(f"   Rec {i}: {tw} seconds", end="")
    if tw:
        print(f" ({tw/60:.1f} min)", end="")
    print()

# 6. All records duration summary
print()
print("6. Duration metrics across all records:")
for cf in ["response_time_s", "resolution_time_s", "assign_time_s", "closure_lag_s"]:
    vals = [rec.get(cf) for rec in silver if rec.get(cf) is not None]
    if vals:
        avg = sum(vals) / len(vals)
        print(f"   {cf}: avg={avg:.0f}s ({avg/60:.1f}min), min={min(vals)}s, max={max(vals)}s")
    else:
        print(f"   {cf}: no data")
