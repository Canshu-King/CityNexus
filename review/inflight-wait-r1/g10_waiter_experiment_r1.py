"""Does the waiter my inventory prescribed actually close g10?  Measured, both arms, twelve each.

Phase A runs the arm as shipped.  Phase B rewrites the arm body the way the dispatch row told a lane
to ("take the operation id from the accepted POST, wait for the job's terminal state, then read the
door"), using the module's own `wait_for_operation`, and runs it again.  The file is put back
byte-for-byte at the end and the blob is compared with the tree's own, so nothing of the experiment
survives except the numbers.
"""

from __future__ import annotations

import json
import os
import pathlib
import re
import subprocess
import sys
import uuid

BACKEND = pathlib.Path(r"D:/moodle/_qoder_lane_ord0520_20260930/wt2/backend")
TREE = BACKEND.parent
TARGET = BACKEND / "tests/test_qoder_anywhere_provider_truth.py"
LANE = pathlib.Path(r"D:/moodle/_qoder_lane_ord0520_20260930")
PYTHON = pathlib.Path(r"D:/moodle/CityNexus/.venv/Scripts/python.exe")
ARM = "tests/test_qoder_anywhere_provider_truth.py::test_g10_every_normalised_place_carries_a_usable_coordinate_including_nodes"
OUT = LANE / "tmp/G10_WAITER_EXPERIMENT_r1.json"
NODES = 12

ORIGINAL = TARGET.read_text(encoding="utf-8")
ANCHOR = '    _require("POST /api/v1/catalog-hydrations", client.post(HYDRATIONS, json={"query": UNSEEN_COUNTY}))\n    # 上面这条受理之后才有得量：水合产出的地点集合必须逐 kind 有坐标。\n'
PATCHED = (
    '    from app.catalog_hydration_operations import wait_for_operation\n'
    '\n'
    '    submitted = client.post(HYDRATIONS, json={"query": UNSEEN_COUNTY})\n'
    '    _require("POST /api/v1/catalog-hydrations", submitted)\n'
    '    operation_id = submitted.json().get("operation_id")\n'
    '    landed = wait_for_operation(operation_id, deadline_seconds=30)\n'
    '    assert landed is not None, "the hydration job must reach a terminal state before the door is read"\n'
    '    # 上面那条等到终态之后才有得量：水合产出的地点集合必须逐 kind 有坐标。\n'
)


def git(*args: str) -> str:
    return subprocess.run(["git", "-C", str(TREE), *args], capture_output=True,
                          text=True, encoding="utf-8", errors="replace").stdout.strip()


def run_once() -> dict:
    run_id = "g10exp-%s-%s" % (datetime_stamp(), uuid.uuid4().hex[:6])
    db = LANE / "db" / ("_%s.db" % run_id)
    env = dict(os.environ)
    env.pop("DEEPSEEK_API_KEY", None)
    env.update({
        "CITYNEXUS_DATABASE_URL": "sqlite:///" + db.as_posix(),
        "CITYNEXUS_E2E_RUN_ID": run_id,
        "PYTHONIOENCODING": "utf-8",
    })
    env.pop("CITYNEXUS_AI_ENABLED", None)
    proc = subprocess.run([str(PYTHON), "-X", "utf8", "-m", "pytest", "-q", "-p", "no:randomly",
                           "--no-header", ARM], cwd=str(BACKEND), env=env,
                          capture_output=True, text=True, encoding="utf-8", errors="replace")
    tail = [l for l in (proc.stdout or "").splitlines() if re.search(r"\d+ (passed|failed|error)", l)]
    outcome = "passed" if proc.returncode == 0 else ("failed" if "failed" in " ".join(tail) else "error")
    message = ""
    for line in (proc.stdout or "").splitlines():
        if line.startswith("E   ") and "AssertionError" in line:
            message = line.strip()
        if line.startswith("E  ") and "期望" in line:
            message = line.strip()
    return {"run_id": run_id, "rc": proc.returncode, "outcome": outcome,
            "summary_tail": tail[-1] if tail else "(no count line)",
            "assertion_first_240": message[:240]}


def datetime_stamp() -> str:
    import datetime
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def phase(label: str) -> dict:
    rows = []
    for _ in range(NODES):
        rows.append(run_once())
    reds = len([r for r in rows if r["outcome"] != "passed"])
    return {"phase": label, "runs": NODES, "red": reds, "green": NODES - reds,
            "red_rate": "%.2f" % (reds / NODES), "rows": rows}


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    head_blob = git("rev-parse", "HEAD:backend/tests/test_qoder_anywhere_provider_truth.py")
    if ANCHOR not in ORIGINAL:
        print("ABORT: the shipped arm body is not what this experiment expects")
        return 2

    print("phase A: arm as shipped")
    a = phase("A_shipped")
    print("  red %d/%d" % (a["red"], a["runs"]))

    TARGET.write_text(ORIGINAL.replace(ANCHOR, PATCHED), encoding="utf-8", newline="")
    print("phase B: same arm, with the prescribed wait_for_operation")
    b = phase("B_with_waiter")
    print("  red %d/%d" % (b["red"], b["runs"]))

    TARGET.write_text(ORIGINAL, encoding="utf-8", newline="\n")
    restored = git("status", "--porcelain", "backend/tests/test_qoder_anywhere_provider_truth.py")
    after = subprocess.run(["git", "-C", str(TREE), "diff", "--stat", "--",
                            "backend/tests/test_qoder_anywhere_provider_truth.py"],
                           capture_output=True, text=True, encoding="utf-8", errors="replace").stdout.strip()
    same_bytes = TARGET.read_bytes() == ORIGINAL.encode("utf-8")

    verdict = ("WAITER_CLOSES_IT" if a["red"] and not b["red"]
               else "WAITER_DOES_NOT_CLOSE_IT" if a["red"] and b["red"]
               else "ARM_WAS_NOT_RED_TO_BEGIN_WITH")
    receipt = {
        "generated_by": "89f2e2d6",
        "order": "ORD-0520 inventory follow-up: g10's prescribed fix, tested instead of assumed",
        "tree_head": git("rev-parse", "HEAD"),
        "test_file_blob_at_head": head_blob,
        "restored_byte_identical": same_bytes,
        "git_status_for_the_file": (restored or "(clean)"),
        "diff_stat_after_restore": (after or "(empty)"),
        "phase_A_shipped": a,
        "phase_B_with_waiter": b,
        "waiter_used": "app.catalog_hydration_operations.wait_for_operation (the module's own; the "
                       "shipped test-side use is backend/tests/test_qoder_pending_destination_identity.py:234)",
        "verdict": verdict,
    }
    OUT.write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("verdict %s" % verdict)
    print("restored_byte_identical %s  git_status %r" % (same_bytes, restored or "(clean)"))
    print("receipt %s" % OUT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
