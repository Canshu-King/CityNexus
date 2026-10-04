"""ORD-0520 wrap-up - the seven screen arms re-run against the CURRENT authoritative generation.

Landing is not the same as still being true: the arms below were first run on the generation that
introduced them. This receipt re-runs them, unchanged, against the tip, on this lane's own stack
(run-stamped database, four-part provenance in the companion receipt), and records the durable row
straight out of that sqlite file by rowid.

0 product bytes; it reads artifacts this run already wrote plus its own database.
"""

from __future__ import annotations

import glob
import hashlib
import io
import json
import os
import sqlite3
import subprocess
from pathlib import Path

LANE = Path(r"D:/moodle/_qoder_lane_ord0520_20260930")
TREE = LANE / "wt2"
REPORT = LANE / "tmp/glass_report_regress.json"
EVIDENCE = LANE / "tmp/glass_evidence_final_regress_placeholder"
OUT = TREE / "review/ord0520/ABORT_GLASS_REGRESSION_r1.json"
RUN_ID = os.environ.get("CITYNEXUS_E2E_RUN_ID", "")
DB = Path(os.environ.get("CITYNEXUS_DATABASE_URL", "").replace("sqlite:///", ""))


def git(*args: str) -> str:
    return subprocess.run(["git", "-C", str(TREE), *args], capture_output=True,
                          text=True, encoding="utf-8", errors="replace").stdout.strip()


def sha1(path: Path) -> str:
    return hashlib.sha1(path.read_bytes()).hexdigest()


def main() -> int:
    if not RUN_ID or not DB.exists():
        print("ABORT: the receipt names the run and the database it measured")
        return 2
    report = json.loads(io.open(REPORT, encoding="utf-8", errors="replace").read())
    stats = report.get("stats", {})

    arms: list[dict] = []

    def walk(node):
        for spec in node.get("specs", []):
            for test in spec.get("tests", []):
                res = (test.get("results") or [{}])[-1]
                arms.append({
                    "arm": spec.get("title", "").split("—")[0].strip(),
                    "status": res.get("status") or test.get("status"),
                    "duration_ms": res.get("duration"),
                })
        for child in node.get("suites", []):
            walk(child)

    for suite in report.get("suites", []):
        walk(suite)

    readings: dict[str, dict] = {}
    for path in sorted(glob.glob(str(LANE / "tmp/glass_evidence_regress/**/g*.json"), recursive=True)):
        body = json.loads(io.open(path, encoding="utf-8", errors="replace").read())
        readings[str(Path(path).name)] = {
            "arm": body.get("arm"),
            "verdict": body.get("verdict"),
            "run": body.get("run"),
            "head": body.get("head"),
            "sha1": sha1(Path(path)),
        }

    connection = sqlite3.connect("file:" + DB.as_posix() + "?mode=ro", uri=True)
    connection.row_factory = sqlite3.Row
    try:
        rows = connection.execute(
            "select rowid, id, status, aborted_at, abort_reason from journeys "
            "where aborted_at is not null order by rowid"
        ).fetchall()
        moved = [dict(r) for r in rows if r["status"] != "CANCELLED"]
        count = len(rows)
    finally:
        connection.close()

    receipt = {
        "generated_by": "89f2e2d6",
        "order": "ORD-0520 wrap-up: the glass arms on the landed generation",
        "measured_against_tip": git("rev-parse", "HEAD"),
        "authoritative_ref_read": git("ls-remote", "--refs", "origin",
                                      "refs/heads/mirror/integration-frontend-apple-pass1").split("\t")[0],
        "run_id": RUN_ID,
        "database_basename": DB.name,
        "database_bytes": DB.stat().st_size,
        "arms_expected": stats.get("expected"),
        "arms_unexpected": stats.get("unexpected"),
        "arms": arms,
        "per_arm_readings": readings,
        "durable_rows": {
            "aborted_rows_in_this_store": count,
            "rows_still_marked_planned_after_the_abort": moved,
            "reading": "arm 7's row keeps status moved off CANCELLED while aborted_at and abort_reason "
            "stay on it - the exclusion the screen shows comes from that column, not from status",
        },
        "provenance_receipt": "review/ord0520/ABORT_GLASS_PROVENANCE_%s.json" % RUN_ID,
        "verdict": "REGRESSION_GREEN" if stats.get("expected") == 7 and not stats.get("unexpected") else "REGRESSION_NOT_CLEAN",
    }
    OUT.write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("tip %s" % receipt["measured_against_tip"])
    print("arms expected %s unexpected %s" % (receipt["arms_expected"], receipt["arms_unexpected"]))
    print("evidence files %d" % len(readings))
    print("aborted rows %d, still-planned %s" % (count, [r["rowid"] for r in moved]))
    print("verdict %s" % receipt["verdict"])
    print("receipt %s" % OUT)
    print("receipt_sha1_8 %s" % sha1(OUT)[:8])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
