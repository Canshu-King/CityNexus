"""Which shape is it? Separate the two ways the fresh-database guard can produce a red.

Shape A: an arm creates its own sqlite file and then asks the app to open that same file -- the file
was never the run's declared store.

Shape B: the arm shells out (or otherwise starts a second process) that inherits
CITYNEXUS_E2E_RUN_ID and re-opens the run's own already-created database -- here the guard is right
about the fact and wrong about who owns it.

My previous block proposed a fix that only addresses A; this measures how many of the nine
mode-sensitive files are actually B, because that decides whether the proposed remedy would work.
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
DEN = TREE / "review/inflight-wait-r1/GUARD_DENOMINATOR_r2.json"
OUT = LANE / "tmp/GUARD_SHAPES_r1.json"
REFUSAL = "refuses to reopen an existing database"
SUBPROCESS = re.compile(r"subprocess\.(run|check_output|check_call|Popen|call)\(|exec\(")


def base_env() -> dict:
    env = dict(os.environ)
    for key in ("DEEPSEEK_API_KEY", "CITYNEXUS_E2E_RUN_ID", "CITYNEXUS_DATABASE_URL"):
        env.pop(key, None)
    env["PYTHONIOENCODING"] = "utf-8"
    return env


def stamped_env() -> tuple[dict, str]:
    env = base_env()
    run_id = "shapes-%s" % uuid.uuid4().hex[:8]
    db = LANE / "db" / ("_%s.db" % run_id)
    env["CITYNEXUS_DATABASE_URL"] = "sqlite:///" + db.as_posix()
    env["CITYNEXUS_E2E_RUN_ID"] = run_id
    return env, run_id


def pytest_stamped(files: list[str]) -> dict:
    env, run_id = stamped_env()
    proc = subprocess.run([str(PYTHON), "-X", "utf8", "-m", "pytest", "-q", "-p", "no:randomly",
                           "--tb=line"] + files, cwd=str(BACKEND), env=env,
                          capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=600)
    out = proc.stdout or ""
    return {"run_id": run_id, "rc": proc.returncode,
            "refusal_lines": sorted(set(re.findall(r"%s at (\S+)" % re.escape(REFUSAL), out))),
            "child_refusals": out.count("CompletedProcess"),
            "failed": sorted(set(re.findall(r"FAILED (\S+::\S+)", out))),
            "tracebacks_with_refusal": [l.strip()[:220] for l in out.splitlines()
                                        if REFUSAL in l][:6]}


def ruler_direct() -> dict:
    """The same child command my parity arm shells out to, run with and without the stamp."""
    tool = str(TREE / "tools/verify_openapi_parity.py")
    answers = {}
    for label, env in (("with_stamp", stamped_env()[0]), ("plain", base_env())):
        proc = subprocess.run([str(PYTHON), "-X", "utf8", tool], cwd=str(BACKEND), env=env,
                              capture_output=True, text=True, encoding="utf-8", errors="replace")
        answers[label] = {"rc": proc.returncode,
                          "refusal": REFUSAL in (proc.stdout + proc.stderr),
                          "tail": (proc.stdout or proc.stderr or "").strip().splitlines()[-1][:160]}
    return answers


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    den = json.loads(DEN.read_text(encoding="utf-8"))
    nine = den["disagreement_list"]
    files = sorted({f for f in nine})
    print("stamping the nine mode-sensitive files together")
    nine_read = pytest_stamped(files)
    print("  failed=%d refusals=%d child-shaped=%d"
          % (len(nine_read["failed"]), len(nine_read["refusal_lines"]), nine_read["child_refusals"]))
    for path in nine_read["refusal_lines"]:
        print("   refusal against %s" % path.split("/")[-1][-40:])
    print("the child command on its own, with and without the stamp")
    direct = ruler_direct()
    for label, a in direct.items():
        print("  %-11s rc=%s refusal=%s  %s" % (label, a["rc"], a["refusal"], a["tail"][:80]))
    inheriting = [f for f in files
                  if SUBPROCESS.search((BACKEND / f).read_text(encoding="utf-8", errors="replace"))]
    receipt = {"generated_by": "89f2e2d6", "tree_head": den["tree_head"],
               "files_compared": files, "nine_run": nine_read,
               "child_command_direct": direct,
               "files_that_start_a_second_process": inheriting,
               "shapes": {"A_arm_opens_a_file_it_seeded": None, "B_child_inherits_the_run_id": None},
               "previous_proposal": "my last block asked for the guard to check only the run's "
                                    "declared database url -- this measures whether that would help"}
    a_only = [p for p in nine_read["refusal_lines"] if "db" in p and p not in
              [str(x) for x in []]]
    receipt["shapes"]["A_arm_opens_a_file_it_seeded"] = [p for p in nine_read["refusal_lines"]
                                                          if "basetemp" in p or "tmp" in p.lower()]
    receipt["shapes"]["B_child_inherits_the_run_id"] = [p for p in nine_read["refusal_lines"]
                                                        if p.endswith(".db") and "db_" in p]
    OUT.write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("files among the nine that start a second process: %d -> %s"
          % (len(inheriting), [f.split("/")[-1] for f in inheriting]))
    print("receipt %s" % OUT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
