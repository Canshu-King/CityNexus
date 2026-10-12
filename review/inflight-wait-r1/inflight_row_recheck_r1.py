"""Re-check my own inventory table by running it, not by reading the AST again.

One row was already refuted by a real run (g10), so every prescription in that table is now a
hypothesis to be re-measured.  This hand takes each named site, runs it once against a fresh private
database on the current tip, and records whether it is red at all -- before anyone spends a turn
adding a waiter to something that is green, already landed, or red for another cause.
"""

from __future__ import annotations

import datetime
import json
import os
import pathlib
import re
import subprocess
import sys
import uuid

TREE = pathlib.Path(r"D:/moodle/_qoder_lane_ord0520_20260930/wt2")
BACKEND = TREE / "backend"
LANE = pathlib.Path(r"D:/moodle/_qoder_lane_ord0520_20260930")
PYTHON = pathlib.Path(r"D:/moodle/CityNexus/.venv/Scripts/python.exe")
TABLE = TREE / "review/inflight-wait-r1/INFLIGHT_WAIT_INVENTORY_r1.json"
OUT = LANE / "tmp/INFLIGHT_ROW_RECHECK_r1.json"
REF = "refs/heads/mirror/integration-frontend-apple-pass1"


def git(*args: str) -> tuple[int, str]:
    r = subprocess.run(["git", "-C", str(TREE), *args], capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    return r.returncode, (r.stdout or "").strip()


def run_once(nodeid: str) -> dict:
    run_id = "rowchk-%s-%s" % (datetime.datetime.now(datetime.timezone.utc).strftime("%H%M%S"),
                              uuid.uuid4().hex[:6])
    db = LANE / "db" / ("_%s.db" % run_id)
    env = dict(os.environ)
    env.pop("DEEPSEEK_API_KEY", None)
    env.update({"CITYNEXUS_DATABASE_URL": "sqlite:///" + db.as_posix(),
                "CITYNEXUS_E2E_RUN_ID": run_id, "PYTHONIOENCODING": "utf-8"})
    proc = subprocess.run([str(PYTHON), "-X", "utf8", "-m", "pytest", "-q", "-p", "no:randomly",
                           "--no-header", "-q", nodeid], cwd=str(BACKEND), env=env,
                          capture_output=True, text=True, encoding="utf-8", errors="replace")
    counts = [l for l in (proc.stdout or "").splitlines() if re.search(r"\d+ (passed|failed|error)", l)]
    first_e = ""
    for line in (proc.stdout or "").splitlines():
        if line.startswith("E   ") or line.startswith("E  "):
            first_e = line.strip()[:200]
            break
    return {"rc": proc.returncode,
            "outcome": "passed" if proc.returncode == 0 else "red",
            "count_line": counts[-1] if counts else "(no count line)",
            "assertion_first_200": first_e, "run_id": run_id}


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    tip_rc, tip = git("rev-parse", "HEAD")
    rows = json.loads(TABLE.read_text(encoding="utf-8"))["hand_verified_dispatch_table"]
    out = {"generated_by": "89f2e2d6",
           "order": "re-check of my own read-an-in-flight-job table, by running it",
           "tree_head": tip,
           "mirror_tip_read": git("-c", "http.proxy=false", "ls-remote", "--refs", "origin", REF)[1].split("\t")[0],
           "rows": []}
    for row in rows:
        site = row["site"]
        path = site.split(":")[0]
        line_no = site.split(":")[1]
        rel = path.replace("backend/", "")
        nodeid = "%s::%s" % (rel, row["function"])
        blob = git("rev-parse", "%s:%s" % (tip, path))[1]
        reading = run_once(nodeid)
        rec = {"site": site, "site_line_in_table": line_no, "nodeid": nodeid,
               "file_blob_at_head": blob, "prescription": row["fix_one_line"],
               "waiter_to_use": row["waiter_to_use"]}
        rec.update(reading)
        out["rows"].append(rec)
        print("%-72s %s  %s" % (site, rec["outcome"], rec["count_line"]))
    reds = len([r for r in out["rows"] if r["outcome"] != "passed"])
    out["summary"] = {"rows": len(out["rows"]), "still_red": reds, "already_green": len(out["rows"]) - reds}
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("summary %s" % json.dumps(out["summary"]))
    print("receipt %s" % OUT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
