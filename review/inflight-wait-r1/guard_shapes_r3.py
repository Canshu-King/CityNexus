"""Finish the taxonomy: every one of the nine mode-sensitive files gets a named shape, from a run.

Shapes:
A - the arm seeds its own sqlite file, then asks the app to open it (file was never the run's store).
B - the run's own declared store is opened a second time (by a child process or a later engine), and
    the guard refuses it.
C - the arm asserts the ambient process carries NO run id, so stamping the process breaks it by design.
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
R2 = LANE / "tmp/GUARD_SHAPES_r2.json"
OUT = LANE / "tmp/GUARD_SHAPES_r3.json"
REFUSAL = "refuses to reopen an existing database"
SPECIAL = [
    "tests/test_e2e_provenance.py::test_an_unstamped_process_is_left_alone",
    "tests/test_e2e_provenance.py::test_health_does_not_claim_a_run_id_it_was_never_given",
    "tests/test_qoder_ord0520_journey_abort.py::test_the_parity_ruler_is_green_and_names_the_new_components_in_the_generated_client",
]


def stamped_run(node: str) -> dict:
    run_id = "shape3-%s" % uuid.uuid4().hex[:8]
    db = LANE / "db" / ("_%s.db" % run_id)
    env = dict(os.environ)
    for key in ("DEEPSEEK_API_KEY",):
        env.pop(key, None)
    env.update({"CITYNEXUS_E2E_RUN_ID": run_id,
                "CITYNEXUS_DATABASE_URL": "sqlite:///" + db.as_posix(),
                "PYTHONIOENCODING": "utf-8"})
    proc = subprocess.run([str(PYTHON), "-X", "utf8", "-m", "pytest", "-q", "-p", "no:randomly",
                           "--tb=line", node], cwd=str(BACKEND), env=env,
                          capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=420)
    out = proc.stdout or ""
    fail_lines = [l.strip() for l in out.splitlines() if re.match(r"^[A-Za-z]:.*:\d+: ", l)]
    return {"node": node, "rc": proc.returncode, "run_id": run_id,
            "refusal_present": REFUSAL in out,
            "refusal_names_the_run_store": ("_%s.db" % run_id) in out,
            "failure_line": (fail_lines[0][:200] if fail_lines else "(none)"),
            "asserts_absence_of_stamp": bool(re.search(r"must not carry a run id|== ''", out))}


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    r2 = json.loads(R2.read_text(encoding="utf-8"))
    per_file = {row["node"]: row for row in r2["per_file"]}
    special = {}
    for node in SPECIAL:
        special[node] = stamped_run(node)
        print("%-72s refusal=%s names_run_store=%s asserts_absence=%s"
              % (node.split("::")[-1][:70], special[node]["refusal_present"],
                 special[node]["refusal_names_the_run_store"], special[node]["asserts_absence_of_stamp"]))

    shapes = {"A_arm_seeds_its_own_file": [], "B_run_own_store_reopened": [],
              "C_arm_asserts_no_stamp": []}
    for node, row in per_file.items():
        if "A_arm_seeded_file" in row["shapes"]:
            shapes["A_arm_seeds_its_own_file"].append(node)
        elif "B_run_own_store_reopened" in row["shapes"]:
            shapes["B_run_own_store_reopened"].append(node)
        elif node == "tests/test_e2e_provenance.py" or "test_e2e_provenance" in node:
            shapes["C_arm_asserts_no_stamp"].append(node)
    if special[SPECIAL[2]]["refusal_names_the_run_store"]:
        shapes["B_run_own_store_reopened"].append("tests/test_qoder_ord0520_journey_abort.py")
    for key in shapes:
        shapes[key] = sorted(set(shapes[key]))

    total = sum(len(v) for v in shapes.values())
    receipt = {"generated_by": "89f2e2d6", "tree_head": r2["tree_head"],
               "same_run_two_opens": r2["same_run_two_opens"],
               "shape_of_the_nine": shapes, "shape_counts": {k: len(v) for k, v in shapes.items()},
               "files_accounted": total, "files_compared": r2["shape_counts"]["compared"],
               "special_runnings": special,
               "correction_to_my_own_proposal": (
                   "the last block asked for the guard to check only the run's declared database url; "
                   "same_run_two_opens shows the declared url is precisely what gets refused the "
                   "second time, so that proposal cannot be the whole fix -- shape B needs either a "
                   "run identity written into the store, or the standing rule to say children and "
                   "second openers must not inherit CITYNEXUS_E2E_RUN_ID")}
    if total != r2["shape_counts"]["compared"]:
        receipt["unattributed"] = sorted(set(per_file) - {f for v in shapes.values() for f in v})
    OUT.write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("shape counts %s files_accounted %d of %d"
          % (json.dumps(receipt["shape_counts"]), total, r2["shape_counts"]["compared"]))
    print("unattributed %s" % json.dumps(receipt.get("unattributed", []), ensure_ascii=False))
    print("receipt %s" % OUT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
