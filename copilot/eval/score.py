"""Scores results_run*.jsonl against ground_truth.json and prints the summary.

Rules (applied to the final answer text):
  count : the exact integer must appear
  rate  : a number within 0.005 of the fraction, or within 0.5 of the percentage
  value : a number within 2 % (relative) or 0.05 (absolute) of the reference
  grouped : every expected group label and its value must appear (partial credit reported separately)
  top   : the expected top label must be named
Manual questions are scored from manual_verdicts.json (filled in after reading each answer).
"""
import glob
from pathlib import Path
import sys
import json
import re
import statistics as st

from questions import QUESTIONS

EXCLUDE = {"B4"}  # ambiguous wording, replaced by B4r (reported separately)
HERE = Path(__file__).resolve().parent
GT = json.load(open(HERE / "ground_truth.json"))
Q = {q["id"]: q for q in QUESTIONS}
CUBE_TOOLS = {"list_cube_metrics", "run_cube_query"}
FALLBACK_TOOLS = {"list_tables", "describe_table", "sample_values", "run_sql"}
MONTHS = ["january", "february", "march", "april", "may", "june", "july", "august",
          "september", "october", "november", "december"]


def numbers(text):
    vals = []
    for m in re.finditer(r"-?\d[\d,]*(?:\.\d+)?", text or ""):
        s = m.group().replace(",", "")
        try:
            vals.append(float(s))
        except ValueError:
            pass
    return vals


def num_ok(kind, ref, got):
    if kind == "count":
        return abs(got - ref) < 1e-9
    if kind == "rate":
        return abs(got - ref) <= 0.005 or abs(got - ref * 100) <= 0.5
    return abs(got - ref) <= max(0.02 * abs(ref), 0.05)


def any_num_ok(kind, ref, text):
    return any(num_ok(kind, ref, n) for n in numbers(text))


def label_tokens(label):
    """'1 - Critical' -> 'critical'; '2026-03' -> month names; long names -> distinctive tail."""
    if re.fullmatch(r"\d{4}-\d{2}", label):
        y, m = label.split("-")
        return [label, f"{MONTHS[int(m) - 1]} {y}", MONTHS[int(m) - 1]]
    label = re.sub(r"^\d+\s*-\s*", "", label)
    return [label.lower()]


def label_in(label, text):
    t = (text or "").lower()
    return any(tok.lower() in t for tok in label_tokens(label))


def score(r, manual):
    q = Q[r["id"]]
    ans = r["answer"]
    if q["check"] == "manual":
        v = manual.get(f'{r["run"]}:{r["id"]}')
        return v if v is not None else None
    if not ans:
        return False
    ref = GT[r["id"]]
    if q["check"] == "scalar":
        return any_num_ok(q["kind"], ref, ans)
    if q["check"] == "top":
        return label_in(ref[0][0], ans)
    if q["check"] == "grouped":
        # split answer into lines/sentences so each value is checked next to its own label
        chunks = re.split(r"[\n;]|(?<=\d)\s*,\s*(?=[A-Za-z])", ans)
        ok = 0
        for label, val in ref:
            hit = any(label_in(label, c) and any_num_ok(q["kind"], val, c) for c in chunks)
            ok += hit
        r["_partial"] = f"{ok}/{len(ref)}"
        return ok == len(ref)


PATTERN = sys.argv[1] if len(sys.argv) > 1 else "results/round2/results_runb[0-9].jsonl"
OUT = sys.argv[2] if len(sys.argv) > 2 else "scored.json"


def main():
    try:
        manual = json.load(open(HERE / "manual_verdicts.json"))
    except FileNotFoundError:
        manual = {}
    rows = []
    for path in sorted(glob.glob(str(HERE / PATTERN))):
        rows += [r for r in (json.loads(l) for l in open(path, encoding="utf8")) if r["id"] not in EXCLUDE]
    for r in rows:
        r["correct"] = score(r, manual)
        names = {c["name"] for c in r["tool_calls"]}
        r["path"] = ("none" if not names else "cube" if names <= CUBE_TOOLS
                     else "fallback" if names <= FALLBACK_TOOLS else "mixed")

    runs = sorted({r["run"] for r in rows})
    print(f"runs: {runs}   answers: {len(rows)}\n")

    print("per question:")
    for qid in [q for q in Q if q not in EXCLUDE]:
        rs = [r for r in rows if r["id"] == qid]
        marks = "".join("-" if r["correct"] is None else ("Y" if r["correct"] else "n") for r in rs)
        lat = ", ".join(f'{r["latency_s"]:.0f}s' for r in rs)
        extra = " ".join(r.get("_partial", "") for r in rs if r.get("_partial"))
        print(f"  {qid:3} {Q[qid]['category']:13} {marks:4} [{lat}] {extra}")

    scored = [r for r in rows if r["correct"] is not None]
    print("\naccuracy by category (all runs):")
    cats = list(dict.fromkeys(q["category"] for q in QUESTIONS))
    for c in cats + ["ALL"]:
        rs = [r for r in scored if c == "ALL" or r["category"] == c]
        if rs:
            n = sum(bool(r["correct"]) for r in rs)
            print(f"  {c:13} {n}/{len(rs)} = {100 * n / len(rs):.1f} %")

    per_q = {}
    for r in scored:
        per_q.setdefault(r["id"], []).append(bool(r["correct"]))
    full = [q for q, v in per_q.items() if len(v) == len(runs)]
    always = sum(all(per_q[q]) for q in full)
    never = sum(not any(per_q[q]) for q in full)
    print(f"\nconsistency: correct in all {len(runs)} runs: {always}/{len(full)}; "
          f"wrong in all runs: {never}/{len(full)}; mixed: {len(full) - always - never}")

    lats = sorted(r["latency_s"] for r in rows)
    p95 = lats[min(len(lats) - 1, int(round(0.95 * (len(lats) - 1))))]
    print(f"\nlatency: median {st.median(lats):.1f}s  p95 {p95:.1f}s  max {max(lats):.1f}s  "
          f"mean {st.mean(lats):.1f}s")
    errs = [r for r in rows if not r["answer"]]
    print(f"failures (no final answer): {len(errs)}/{len(rows)}  "
          + "; ".join(f'{r["run"]}:{r["id"]} {(r["error"] or "")[:60]}' for r in errs))

    paths = {}
    for r in rows:
        paths[r["path"]] = paths.get(r["path"], 0) + 1
    print(f"tool path: {paths}")
    print(f"tool calls per answer: mean {st.mean(len(r['tool_calls']) for r in rows):.2f}")
    rejected = sum(1 for r in rows for t in r["tool_results"]
                   if t["name"] == "run_cube_query" and re.search(r"unknown|not a valid|invalid", t["result"], re.I))
    print(f"run_cube_query calls rejected by member validation: {rejected}")

    (HERE / "results" / "latest").mkdir(parents=True, exist_ok=True)
    json.dump(rows, open(HERE / "results" / "latest" / OUT, "w", encoding="utf8"), indent=1, ensure_ascii=False)


if __name__ == "__main__":
    main()
