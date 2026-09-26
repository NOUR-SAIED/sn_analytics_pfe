"""Sends every question to the Copilot backend and records what happens.

Usage: python run_eval.py <run_number> [question_id ...]
Each question gets a fresh thread_id (no shared conversation memory).
Results are appended to results/latest/results_run<N>.jsonl after every question, and
questions already present in that file are skipped, so a run can be resumed.
"""
import json
import sys
import time
import uuid
from pathlib import Path

import requests

from questions import QUESTIONS

URL = "http://localhost:8000/api/ask"
CLIENT_TIMEOUT = 600  # server enforces its own 480 s budget


def ask(question: str) -> dict:
    events, t0 = [], time.monotonic()
    first_event_s = None
    try:
        with requests.post(URL, json={"question": question, "thread_id": str(uuid.uuid4())},
                           stream=True, timeout=CLIENT_TIMEOUT) as r:
            r.raise_for_status()
            for line in r.iter_lines(decode_unicode=True):
                if line and line.startswith("data: "):
                    if first_event_s is None:
                        first_event_s = time.monotonic() - t0
                    events.append(json.loads(line[6:]))
    except Exception as exc:  # network / client timeout
        events.append({"type": "error", "error": f"client: {exc}"})
    total_s = time.monotonic() - t0

    final = next((e["answer"] for e in events if e["type"] == "final"), None)
    error = next((e["error"] for e in events if e["type"] == "error"), None)
    calls = [e for e in events if e["type"] == "tool_call"]
    return dict(answer=final, error=error, latency_s=round(total_s, 2),
                first_event_s=round(first_event_s, 2) if first_event_s else None,
                tool_calls=[{"name": c["name"], "arguments": c.get("arguments")} for c in calls],
                tool_results=[{"name": e["name"], "result": str(e.get("result"))[:2000]}
                              for e in events if e["type"] == "tool_result"])


def main():
    run = sys.argv[1]
    only = set(sys.argv[2:])
    out_dir = Path(__file__).resolve().parent / "results" / "latest"
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"results_run{run}.jsonl"
    try:
        done = {json.loads(l)["id"] for l in open(path, encoding="utf8")}
    except FileNotFoundError:
        done = set()
    todo = [q for q in QUESTIONS if q["id"] not in done and (not only or q["id"] in only)]
    for i, q in enumerate(todo, 1):
        res = ask(q["question"])
        res.update(id=q["id"], category=q["category"], question=q["question"], run=run)
        with open(path, "a", encoding="utf8") as f:
            f.write(json.dumps(res, ensure_ascii=False) + "\n")
        status = "ERROR" if res["error"] and not res["answer"] else "ok"
        tools = ",".join(c["name"] for c in res["tool_calls"])
        print(f"[run {run}] {i}/{len(todo)} {q['id']} {status} {res['latency_s']}s tools={tools}", flush=True)


if __name__ == "__main__":
    main()
