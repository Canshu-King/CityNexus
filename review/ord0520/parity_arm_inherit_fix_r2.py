"""Measure the patched state. The previous hand measured everything before applying the patch, so
its numbers are a second "before" reading, not an "after" one -- this is the after.

Same node, same six stamped runs, same whole-file pair, same counterexample, then the tool and the
test file are left exactly as the candidate intends: the test file patched, the tool untouched.
"""

from __future__ import annotations

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
TEST = BACKEND / "tests/test_qoder_ord0520_journey_abort.py"
TOOL = TREE / "tools/verify_openapi_parity.py"
ARM = ("tests/test_qoder_ord0520_journey_abort.py::"
       "test_the_parity_ruler_is_green_and_names_the_new_components_in_the_generated_client")
BEFORE = json.loads((LANE / "tmp/ORD0520_PARITY_ARM_INHERIT_r1.json").read_text(encoding="utf-8"))
OUT = LANE / "tmp/ORD0520_PARITY_ARM_INHERIT_r2.json"


def git(*args: str) -> tuple[int, str]:
    r = subprocess.run(["git", "-C", str(TREE), *args], capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    return r.returncode, (r.stdout or "").strip()


def run(nodes: list[str], stamp: bool) -> dict:
    env = dict(os.environ)
    env.pop("DEEPSEEK_API_KEY", None)
    for key in ("CITYNEXUS_E2E_RUN_ID", "CITYNEXUS_DATABASE_URL"):
        env.pop(key, None)
    env["PYTHONIOENCODING"] = "utf-8"
    run_id = ""
    if stamp:
        run_id = "paritypost-%s" % uuid.uuid4().hex[:8]
        db = LANE / "db" / ("_%s.db" % run_id)
        env["CITYNEXUS_DATABASE_URL"] = "sqlite:///" + db.as_posix()
        env["CITYNEXUS_E2E_RUN_ID"] = run_id
    proc = subprocess.run([str(PYTHON), "-X", "utf8", "-m", "pytest", "-q", "-p", "no:randomly"] + nodes,
                          cwd=str(BACKEND), env=env, capture_output=True, text=True,
                          encoding="utf-8", errors="replace", timeout=420)
    out = proc.stdout or ""
    summary = [l for l in out.splitlines() if re.search(r"\d+ (passed|failed|error)", l)]
    return {"stamp": stamp, "run_id": run_id or "(none)", "rc": proc.returncode,
            "summary": summary[-1].strip() if summary else "(no count line)",
            "refusal": "refuses to reopen" in out,
            "failed": sorted(n.split("::")[-1] for n in re.findall(r"FAILED (\S+)", out))}


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    src = TEST.read_text(encoding="utf-8")
    patched_present = "CITYNEXUS_E2E_RUN_ID" in src and "child_env" in src
    single = [run([ARM], True) for _ in range(6)]
    refusals = len([r for r in single if r["refusal"]])
    green = len([r for r in single if r["rc"] == 0])
    file_stamped = run([ARM.split("::")[0]], True)
    file_plain = run([ARM.split("::")[0]], False)

    tool_src = TOOL.read_text(encoding="utf-8")
    TOOL.write_text(tool_src.replace("def main(", "def main(*_forced):\n    raise SystemExit(1)\n\n\ndef _unused_main(", 1),
                    encoding="utf-8", newline="")
    counter = run([ARM], True)
    TOOL.write_text(tool_src, encoding="utf-8", newline="")
    tool_clean = git("status", "--porcelain", "tools/verify_openapi_parity.py")[1] or "(clean)"
    tool_blob = git("rev-parse", "HEAD:tools/verify_openapi_parity.py")[1]

    receipt = {"generated_by": "89f2e2d6", "state": "patched (candidate)",
               "tree_head": git("rev-parse", "HEAD")[1],
               "test_file_blob_at_head_before": BEFORE["test_file_blob_at_head"],
               "test_file_patched_blob": BEFORE["patched_blob"],
               "working_tree_blob": git("hash-object", str(TEST))[1],
               "patch_present_in_working_tree": patched_present,
               "single_arm_stamped_after": {"runs": 6, "refusals": refusals, "green": green,
                                            "rows": [{"rc": r["rc"], "refusal": r["refusal"],
                                                      "summary": r["summary"]} for r in single]},
               "whole_file_after": {"stamped": file_stamped, "plain": file_plain},
               "counterexample_after": {"arm_rc": counter["rc"], "failed": counter["failed"],
                                        "still_bites": bool(counter["rc"] != 0 and counter["failed"]),
                                        "tool_git_status": tool_clean, "tool_blob_at_head": tool_blob},
               "before_for_the_record": {"single_arm_refusals": BEFORE["before_rate_refusals"],
                                         "rechecked_refusals": BEFORE["after_single_arm_stamped"]["refusals"],
                                         "whole_file_stamped": BEFORE["after_whole_file"]["stamped"]["summary"],
                                         "whole_file_plain": BEFORE["after_whole_file"]["plain"]["summary"]},
               "judgement": ("ARM_NO_LONGER_SEES_THE_REFUSAL" if refusals == 0 and green == 6
                             else "STILL_REFUSED_AFTER_PATCH")}
    OUT.write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("patch present in working tree: %s" % patched_present)
    print("AFTER single-arm stamped: refusals %d/6, green %d/6 -> %s"
          % (refusals, green, receipt["judgement"]))
    print("AFTER whole file stamped=%-40s plain=%-30s" % (file_stamped["summary"], file_plain["summary"]))
    print("counterexample after patch: rc=%s still_bites=%s tool=%s"
          % (counter["rc"], receipt["counterexample_after"]["still_bites"], tool_clean))
    print("receipt %s" % OUT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
