"""Commander's independent re-run of lane F's ORD-0307 gate tests, written to an artifact.

Two readings are kept side by side on purpose: the complete-tree run (the honest one) and the partial
export I tried first (three reds caused by my own missing roots).  Publishing both is what makes the
attribution real - "the instrument was wrong, not the lane" has to be shown with the two denominators,
not asserted.
"""
import datetime
import hashlib
import io
import json
import os
import subprocess
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
TIP = "7856e03f6238da3000976eb6e690a448dfa39b9a"
TREE = "157554d0d431dffccc3f6e690668fd125995a35a"
GATE_TEST_BLOB = "408032e04fbbae6171df91dc1f2420a15dd9a38d"
PY = r"D:\moodle\CityNexus\.venv\Scripts\python.exe"
FULL = r"D:\moodle\_qoder_cmdr_ref_20260921\snap_fgate_full\backend"
PARTIAL = r"D:\moodle\_qoder_cmdr_ref_20260921\snap_fgate_1915\backend"
SPEC = "tests/test_qoder_ord0307_credential_gate.py"


def run(root, label):
    if not os.path.isdir(root):
        return {"label": label, "root": root, "error": "NO_SUCH_DIR"}
    p = subprocess.run([PY, "-m", "pytest", SPEC, "-q"], cwd=root, capture_output=True, text=True,
                       encoding="utf-8", errors="replace", timeout=900)
    out = (p.stdout or "") + (p.stderr or "")
    tail = [l for l in out.splitlines() if "passed" in l or "failed" in l or "error" in l]
    return {"label": label, "root": root, "exit_code": p.returncode,
            "summary_line": tail[-1] if tail else None,
            "failed_tests": sorted({l.split("::")[-1].split()[0] for l in out.splitlines()
                                    if l.startswith("FAILED")}),
            "output_tail": out.strip().splitlines()[-3:]}


test_blob = subprocess.run(["git", "-C", r"D:\moodle\CityNexus", "rev-parse", TIP + ":" + "backend/" + SPEC],
                           capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=120).stdout.strip()
runs = [run(FULL, "complete_tree_export"), run(PARTIAL, "partial_export_missing_frontend_and_handoff")]
out = {
    "schema": "CNX_CMDR_GATE_RERUN_V1",
    "at_local": (datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=8)).isoformat(timespec="seconds") + "+08",
    "interpreter": PY,
    "candidate": {"tip": TIP, "tree": TREE, "gate_test_blob_at_tip": test_blob,
                  "matches_lane_citation": test_blob == GATE_TEST_BLOB},
    "tool_sha1": hashlib.sha1(io.open(__file__, "rb").read()).hexdigest(),
    "how_recomputed": ["git -C D:/moodle/CityNexus archive " + TIP + " | tar -x -C <dir>",
                       "cd <dir>/backend && " + PY + " -m pytest " + SPEC + " -q"],
    "runs": runs,
    "decisions": {
        "complete_tree_green": runs[0].get("exit_code") == 0 and "10 passed" in (runs[0].get("summary_line") or ""),
        "partial_run_red_tests_are_instrument_shaped": bool(runs[1].get("failed_tests")) and all(
            n.startswith("test_C0") for n in runs[1].get("failed_tests", [])),
        "lane_cited_blob_is_the_one_i_ran": test_blob == GATE_TEST_BLOB},
    "attribution": ("The three reds in the partial export are mine: that export carried only backend/data/"
                    "contracts/tools, so the gate's own named roots could not see frontend/e2e or "
                    "qoder-handoff and it reported an empty hit list. The complete export answers 10 "
                    "passed. Neither reading is deleted - the wrong one is kept so the lesson is checkable."),
    "scope": "A commander's re-run of one test file on two export shapes. It is not a verdict on the "
             "gate's teeth (that is the lane's campaign plus the verifier's derivation) and it moves nothing."}
io.open("_cmdr_gate_rerun_1922.json", "w", encoding="utf-8").write(json.dumps(out, ensure_ascii=False, indent=1))
print(json.dumps(out["decisions"], ensure_ascii=False))
for r in runs:
    print(" ", r["label"], "rc", r.get("exit_code"), "|", r.get("summary_line"), "|", r.get("failed_tests"))
print("gate test blob at tip", test_blob, "matches citation", out["candidate"]["matches_lane_citation"])
