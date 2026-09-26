"""Runs each question's reference SQL directly against gold.* and saves ground_truth.json."""
import json
import subprocess
from pathlib import Path

from questions import QUESTIONS

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]  # repo root (docker compose runs from there)


def psql(sql: str) -> list[list[str]]:
    cmd = ["docker", "compose", "exec", "-T", "postgres", "sh", "-c",
           'psql -U "$POSTGRES_USER" -d elt_sn_db -At -F "\t" -v ON_ERROR_STOP=1']
    out = subprocess.run(cmd, input=sql + ";\n", capture_output=True, text=True, cwd=REPO, check=True)
    return [line.split("\t") for line in out.stdout.strip().splitlines() if line]


gt = {}
for q in QUESTIONS:
    if not q["gt_sql"]:
        continue
    rows = psql(q["gt_sql"])
    if q["check"] == "scalar":
        gt[q["id"]] = float(rows[0][0])
    else:
        gt[q["id"]] = [[r[0], float(r[1])] for r in rows]
    print(q["id"], gt[q["id"]])

json.dump(gt, open(HERE / "ground_truth.json", "w"), indent=2)
