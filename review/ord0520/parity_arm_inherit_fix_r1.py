"""Fix my own arm, not the guard: the parity arm hands its child the run stamp it has no use for.

`backend/tests/test_qoder_ord0520_journey_abort.py` shells out to `tools/verify_openapi_parity.py`,
a pure file reader.  Inheriting CITYNEXUS_E2E_RUN_ID + CITYNEXUS_DATABASE_URL makes that child
re-open the run's own store, which the fresh-database guard refuses -- so my delivered ORD-0520 test
file reads as one red arm in any stamped run.  The arm's assertions are untouched; only the child's
environment changes.

Measured: the stamped single-arm rate before (from the published receipt) and after (this run), the
whole file in both modes, and a counterexample that the arm still bites when parity is broken.
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
OUT = LANE / "tmp/ORD0520_PARITY_ARM_INHERIT_r1.json"
STAMP_KEYS = ("CITYNEXUS_E2E_RUN_ID", "CITYNEXUS_DATABASE_URL")

OLD = '    env = dict(os.environ, PYTHONIOENCODING="utf-8")\n'
NEW = ('    # The parity tool only reads the contract and the generated client; handing it this run\'s\n'
       '    # stamp would make it re-open the store the guard already saw created, and be refused.\n'
       '    child_env = {k: v for k, v in os.environ.items() if k not in ("CITYNEXUS_E2E_RUN_ID",\n'
       '                                                              "CITYNEXUS_DATABASE_URL")}\n'
       '    env = dict(child_env, PYTHONIOENCODING="utf-8")\n')


def git(*args: str) -> tuple[int, str]:
    r = subprocess.run(["git", "-C", str(TREE), *args], capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    return r.returncode, (r.stdout or "").strip()


def run(nodes: list[str], stamp: bool, timeout: int = 420) -> dict:
    env = dict(os.environ)
    env.pop("DEEPSEEK_API_KEY", None)
    for key in STAMP_KEYS:
        env.pop(key, None)
    env["PYTHONIOENCODING"] = "utf-8"
    run_id = ""
    if stamp:
        run_id = "parityfix-%s" % uuid.uuid4().hex[:8]
        db = LANE / "db" / ("_%s.db" % run_id)
        env["CITYNEXUS_DATABASE_URL"] = "sqlite:///" + db.as_posix()
        env["CITYNEXUS_E2E_RUN_ID"] = run_id
    proc = subprocess.run([str(PYTHON), "-X", "utf8", "-m", "pytest", "-q", "-p", "no:randomly"] + nodes,
                          cwd=str(BACKEND), env=env, capture_output=True, text=True,
                          encoding="utf-8", errors="replace", timeout=timeout)
    out = proc.stdout or ""
    summary = [l for l in out.splitlines() if re.search(r"\d+ (passed|failed|error)", l)]
    return {"stamp": stamp, "run_id": run_id or "(none)", "rc": proc.returncode,
            "summary": summary[-1].strip() if summary else "(no count line)",
            "refusal": "refuses to reopen" in out,
            "failed": sorted(n.split("::")[-1] for n in re.findall(r"FAILED (\S+)", out))}


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    src = TEST.read_text(encoding="utf-8")
    if OLD not in src:
        raise SystemExit("ABORT: the arm no longer builds the child env the way this hand expects")
    tip_blob = git("rev-parse", "HEAD:backend/tests/test_qoder_ord0520_journey_abort.py")[1]
    tool_blob_before = git("rev-parse", "HEAD:tools/verify_openapi_parity.py")[1]

    after_single = [run([ARM], True) for _ in range(6)]
    single_refusals = len([r for r in after_single if r["refusal"]])
    single_green = len([r for r in after_single if r["rc"] == 0])
    after_file_stamped = run([ARM.split("::")[0]], True)
    after_file_plain = run([ARM.split("::")[0]], False)

    # counterexample: break parity in the tool the child runs, and require the arm to notice
    tool_src = TOOL.read_text(encoding="utf-8")
    mutated = tool_src.replace("def main(", "def main(*_forced):\n    raise SystemExit(1)\n\n\ndef _unused_main(", 1)
    if mutated == tool_src:
        raise SystemExit("ABORT: could not build the parity counterexample")
    TOOL.write_text(mutated, encoding="utf-8", newline="")
    counter = run([ARM], True)
    TOOL.write_text(tool_src, encoding="utf-8", newline="")
    tool_blob_after = git("rev-parse", ":tools/verify_openapi_parity.py")[1]
    tool_restored = (TOOL.read_text(encoding="utf-8") == tool_src)
    dirty_tool = git("status", "--porcelain", "tools/verify_openapi_parity.py")[1]

    TEST.write_text(src.replace(OLD, NEW), encoding="utf-8", newline="")
    patched_blob = subprocess.run(["git", "-C", str(TREE), "hash-object", "-w", str(TEST)],
                                  capture_output=True, text=True).stdout.strip()

    receipt = {"generated_by": "89f2e2d6", "order": "ORD-0520 wrap-up, second defect: my own parity arm inherited the run stamp",
               "tree_head": git("rev-parse", "HEAD")[1],
               "test_file_blob_at_head": tip_blob, "patched_blob": patched_blob,
               "before_published_receipt": "review/inflight-wait-r1/GUARD_SHAPES_r3.json",
               "before_rate_refusals": 6, "before_rate_runs": 6,
               "after_single_arm_stamped": {"runs": 6, "refusals": single_refusals,
                                            "green": single_green,
                                            "rows": [{"rc": r["rc"], "refusal": r["refusal"],
                                                      "summary": r["summary"], "run_id": r["run_id"]}
                                                     for r in after_single]},
               "after_whole_file": {"stamped": after_file_stamped, "plain": after_file_plain},
               "counterexample": {"what_was_broken": "tools/verify_openapi_parity.py forced to exit 1",
                                  "arm_answer": counter,
                                  "arm_still_bites": bool(counter["rc"] != 0 and counter["failed"]),
                                  "tool_restored_byte_identical": tool_restored,
                                  "tool_blob_before": tool_blob_before, "tool_blob_after_restore": tool_blob_after,
                                  "git_status_for_the_tool": dirty_tool or "(clean)"},
               "what_this_does_not_fix": "the guard itself (shapes A and C remain; this is only the "
                                        "one file this lane owns and only the child-env leg)",
               "assertions_unchanged": src.count("assert") == TEST.read_text(encoding="utf-8").count("assert")}
    OUT.write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("after single-arm stamped: refusals %d/6, green %d/6" % (single_refusals, single_green))
    print("after whole file  stamped=%-38s plain=%-30s" % (after_file_stamped["summary"], after_file_plain["summary"]))
    print("counterexample: rc=%s failed=%s still_bites=%s"
          % (counter["rc"], counter["failed"], receipt["counterexample"]["arm_still_bites"]))
    print("tool restored byte-identical=%s blob %s git=%s"
          % (tool_restored, tool_blob_after[:12], dirty_tool or "(clean)"))
    print("assertions unchanged=%s  patched blob %s" % (receipt["assertions_unchanged"], patched_blob))
    print("receipt %s" % OUT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
