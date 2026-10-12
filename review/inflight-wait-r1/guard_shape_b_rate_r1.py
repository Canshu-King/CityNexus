"""Rate the shape-B case that is mine: my own ORD-0520 parity arm, run alone, stamped, six times.

One sample said no refusal, an earlier one said refusal -- so the difference is order, and the only
honest way to put it in a shape is to count.  The receipt r3 is still lane-local (never published),
so writing the count into it changes no published reading.
"""

from __future__ import annotations

import json
import os
import pathlib
import subprocess
import sys
import uuid

TREE = pathlib.Path(r"D:/moodle/_qoder_lane_ord0520_20260930/wt2")
BACKEND = TREE / "backend"
LANE = pathlib.Path(r"D:/moodle/_qoder_lane_ord0520_20260930")
PYTHON = pathlib.Path(r"D:/moodle/CityNexus/.venv/Scripts/python.exe")
R3 = LANE / "tmp/GUARD_SHAPES_r3.json"
NODE = ("tests/test_qoder_ord0520_journey_abort.py::"
        "test_the_parity_ruler_is_green_and_names_the_new_components_in_the_generated_client")
RUNS = 6


def once() -> dict:
    run_id = "shapeB-%s" % uuid.uuid4().hex[:8]
    db = LANE / "db" / ("_%s.db" % run_id)
    env = dict(os.environ)
    env.pop("DEEPSEEK_API_KEY", None)
    env.update({"CITYNEXUS_E2E_RUN_ID": run_id,
                "CITYNEXUS_DATABASE_URL": "sqlite:///" + db.as_posix(),
                "PYTHONIOENCODING": "utf-8"})
    proc = subprocess.run([str(PYTHON), "-X", "utf8", "-m", "pytest", "-q", "-p", "no:randomly", NODE],
                          cwd=str(BACKEND), env=env, capture_output=True, text=True,
                          encoding="utf-8", errors="replace", timeout=300)
    out = proc.stdout or ""
    return {"run_id": run_id, "rc": proc.returncode, "refusal": "refuses to reopen" in out,
            "names_the_run_store": ("_%s.db" % run_id) in out}


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    rows = [once() for _ in range(RUNS)]
    refusals = len([r for r in rows if r["refusal"]])
    r3 = json.loads(R3.read_text(encoding="utf-8"))
    mine = "tests/test_qoder_ord0520_journey_abort.py"
    r3["shape_of_the_nine"]["B_run_own_store_reopened"] = sorted(
        set(r3["shape_of_the_nine"]["B_run_own_store_reopened"]) | {mine})
    r3["shape_counts"] = {k: len(v) for k, v in r3["shape_of_the_nine"].items()}
    r3["files_accounted"] = sum(r3["shape_counts"].values())
    r3.pop("unattributed", None)
    r3["shape_B_rate_for_my_own_arm"] = {"node": NODE, "runs": RUNS, "refusals": refusals,
                                         "rate": "%.2f" % (refusals / RUNS), "rows": rows,
                                         "note": "the single sample in r3 that showed no refusal is "
                                                 "why this was counted rather than believed"}
    R3.write_text(json.dumps(r3, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("my own parity arm, stamped, alone: refusals %d of %d" % (refusals, RUNS))
    print("shape counts %s files_accounted %d"
          % (json.dumps(r3["shape_counts"]), r3["files_accounted"]))
    print("receipt %s" % R3)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
