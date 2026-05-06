"""
03c_record_view.py
──────────────────
For each record: show only populated fields in a clean table.
Also formats record #1 as a full numbered reference table.

Use this to understand what one case actually looks like end to end.
"""

import sys, os, json, glob, argparse
from datetime import datetime

sys.path.append(os.path.dirname(os.path.dirname(__file__)))

# ── Args — optionally view a specific record index ────────────────────────────
parser = argparse.ArgumentParser()
parser.add_argument("--record", type=int, default=None,
                    help="Show only this record index (0-based). Default: show record 0.")
parser.add_argument("--full",   action="store_true",
                    help="Show full reference table for record #1")
args = parser.parse_args()

# ── Load ──────────────────────────────────────────────────────────────────────
project_root = os.path.dirname(os.path.dirname(__file__))
files = glob.glob(os.path.join(project_root, "data", "sn_data_*.json"))
if not files:
    raise FileNotFoundError("No data in ./data/sn_data_*.json")

latest = max(files, key=os.path.getmtime)
with open(latest, encoding="utf-8") as f:
    records = json.load(f)

N          = len(records)
ALL_FIELDS = list(records[0].keys())


# ── Helpers ───────────────────────────────────────────────────────────────────

def parse_cell(value):
    if isinstance(value, dict):
        link    = value.get("link")
        raw     = value.get("value", "")
        display = value.get("display_value", "")
        if not link and not str(raw).strip() and not str(display).strip():
            return "NULL", "", "", None
        return ("FK_REF" if link else "SIMPLE"), raw, display, link
    if value is None:
        return "NULL", "", "", None
    if isinstance(value, str) and not value.strip():
        return "NULL", "", "", None
    return "SIMPLE", str(value), str(value), None


def detect_subtype(raw, display, is_fk):
    if is_fk:
        return "FK_REF"
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
    if s.isdigit():
        return "INTEGER"
    if raw != display and display:
        return "CHOICE"
    return "TEXT"


def fk_table(link):
    if not link:
        return ""
    parts = link.split("/table/")
    return parts[1].split("/")[0] if len(parts) > 1 else ""


def print_record(idx, rec, numbered=False):
    rows = []
    for field, value in rec.items():
        kind, raw, display, link = parse_cell(value)
        if kind == "NULL":
            continue
        is_fk   = kind == "FK_REF"
        subtype = detect_subtype(raw, display, is_fk)
        tbl     = fk_table(link)
        rows.append((field, subtype, raw, display, tbl))

    case_num = rec.get("number", {})
    case_num = case_num.get("value", f"record_{idx}") if isinstance(case_num, dict) else str(case_num)

    print(f"\n{'='*90}")
    print(f"  Record #{idx}  —  {case_num}  —  {len(rows)} populated / {len(ALL_FIELDS)} total fields")
    print(f"{'='*90}")

    if numbered:
        print(f"  {'#':<4} {'FIELD':<42} {'TYPE':<10} {'RAW VALUE':<30} {'DISPLAY VALUE':<30} FK_TABLE")
        print(f"  {'-'*115}")
        for i, (field, subtype, raw, display, tbl) in enumerate(rows, 1):
            raw_s  = str(raw)[:28]
            disp_s = str(display)[:28] if display and display != raw else ""
            print(f"  {i:<4} {field:<42} {subtype:<10} {raw_s:<30} {disp_s:<30} {tbl}")
    else:
        print(f"  {'FIELD':<42} {'TYPE':<10} {'RAW VALUE':<30} {'DISPLAY VALUE':<30} FK_TABLE")
        print(f"  {'-'*112}")
        for field, subtype, raw, display, tbl in rows:
            raw_s  = str(raw)[:28]
            disp_s = str(display)[:28] if display and display != raw else ""
            print(f"  {field:<42} {subtype:<10} {raw_s:<30} {disp_s:<30} {tbl}")


# ── Main ──────────────────────────────────────────────────────────────────────

if args.record is not None:
    # Single record mode
    if args.record >= N:
        print(f"Only {N} records available (0-based index).")
    else:
        print_record(args.record, records[args.record], numbered=True)

elif args.full:
    # Full numbered reference table for record #1
    print_record(0, records[0], numbered=True)

else:
    # Default: show only the first record in compact view
    print(f"  {N} records loaded from {latest}\n")
    print("  Run with --record N  to inspect a specific record")
    print("  Run with --full      to get the full numbered reference table for record #1\n")

    print_record(0, records[0], numbered=False)