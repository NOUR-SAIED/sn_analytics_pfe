"""
Quick script to inspect silver layer quality issues.
"""
import json, sys
sys.path.insert(0, ".")
from etl_core.config.silver_mappings import get_config
from etl_core.transformers.silver import SilverTransformer

with open("data/sn_data_2026-05-02.json") as f:
    data = json.load(f)

silver = SilverTransformer(get_config("raw_incidents")).transform(data)

print("=== Problem 1: duration fields (time_worked) ===")
for i in range(3):
    tw = data[i]["time_worked"]
    sv = silver[i].get("time_worked")
    print(f"  Rec {i}:")
    print(f"    raw value={tw['value']!r} display={tw['display_value']!r}")
    print(f"    silver stores={sv!r}")

print("\n=== Problem 2: priority/urgency/impact store codes, not labels ===")
for i in range(3):
    for f in ["priority", "urgency", "impact"]:
        sv = silver[i].get(f)
        rv = data[i][f]["value"]
        rd = data[i][f]["display_value"]
        print(f"  Rec {i}, {f}: code={rv!r} label={rd!r} -> silver={sv!r}")

print("\n=== Problem 3: state picks display_value, is that the right pattern? ===")
for i in range(3):
    for f in ["state", "escalation", "category", "contact_type"]:
        sv = silver[i].get(f)
        rv = data[i][f]["value"]
        rd = data[i][f]["display_value"]
        print(f"  Rec {i}, {f}: code={rv!r} -> silver stores label={sv!r} (display={rd!r})")

print("\n=== Problem 4: null/empty handling ===")
nulls = {}
for r in silver:
    for k, v in r.items():
        if v is None or v == "":
            nulls[k] = nulls.get(k, 0) + 1
print("Fields with any null/empty in silver:")
for k, c in sorted(nulls.items(), key=lambda x: -x[1]):
    print(f"  {k}: {c}/{len(silver)} records")
