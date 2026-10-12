"""The second half of the re-check: my table's rows were measured in isolation, but the family it
describes is a batch symptom.  So every file that carries one of my rows is now run as a whole file,
and the two migration arms that actually go red in this batch are run alone.

Two outcomes per file: `red_isolated` (the named site alone) and the whole-file list of failures --
because a row that is green alone and green in batch is not a row a lane should be sent to fix.
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
OUT = LANE / "tmp/INFLIGHT_FILE_BATCH_r1.json"

FILES = [
    "tests/test_qoder_ord197_four_class_receipt.py",
    "tests/test_qoder_anywhere_gates.py",
    "tests/test_qoder_ord224_g3_generation_measurement.py",
    "tests/test_qoder_provider_identity_leg.py",
    "tests/test_qoder_pending_destination_identity.py",
    "tests/test_qoder_anywhere_provider_truth.py",
]
ALONE = [
    "tests/test_qoder_pending_destination_identity.py::test_g10_legacy_pending_rows_migrate_in_place_without_losing_their_ids",
    "tests/test_qoder_pending_destination_identity.py::test_g13_rerunning_the_schema_migration_never_duplicates_or_eats_a_row",
]


def run(args: list[str]) -> dict:
    run_id = "batchchk-%s-%s" % (datetime.datetime.now(datetime.timezone.utc).strftime("%H%M%S"),
                                uuid.uuid4().hex[:6])
    db = LANE / "db" / ("_%s.db" % run_id)
    env = dict(os.environ)
    env.pop("DEEPSEEK_API_KEY", None)
    env.update({"CITYNEXUS_DATABASE_URL": "sqlite:///" + db.as_posix(),
                "CITYNEXUS_E2E_RUN_ID": run_id, "PYTHONIOENCODING": "utf-8"})
    proc = subprocess.run([str(PYTHON), "-X", "utf8", "-m", "pytest", "-q", "-p", "no:randomly"] + args,
                          cwd=str(BACKEND), env=env, capture_output=True, text=True,
                          encoding="utf-8", errors="replace")
    out = proc.stdout or ""
    summary = [l for l in out.splitlines() if re.search(r"\d+ (passed|failed|error)", l)]
    failed = re.findall(r"FAILED (\S+::\S+)", out)
    errored = re.findall(r"ERROR (\S+)", out)
    return {"rc": proc.returncode, "run_id": run_id,
            "summary": summary[-1].strip() if summary else "(no count line)",
            "failed": failed, "errors": errored[:3]}


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    tip = subprocess.run(["git", "-C", str(TREE), "rev-parse", "HEAD"], capture_output=True,
                         text=True, encoding="utf-8").stdout.strip()
    receipt = {"generated_by": "89f2e2d6", "tree_head": tip, "whole_file": [], "the_two_named_alone": []}
    for f in FILES:
        r = run([f])
        blob = subprocess.run(["git", "-C", str(TREE), "rev-parse", "HEAD:%s" % ("backend/" + f)],
                              capture_output=True, text=True, encoding="utf-8").stdout.strip()
        receipt["whole_file"].append({"file": f, "file_blob_at_head": blob, **r})
        print("%-58s %s" % (f, r["summary"]))
        for nodeid in r["failed"]:
            print("      FAILED %s" % nodeid.split("::")[-1][:78])
    for nodeid in ALONE:
        r = run([nodeid])
        receipt["the_two_named_alone"].append({"nodeid": nodeid, **r})
        print("%-58s %s" % (nodeid.split("::")[-1][:56], r["summary"]))
    OUT.write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("receipt %s" % OUT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
