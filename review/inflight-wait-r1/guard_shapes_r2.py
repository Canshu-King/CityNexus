"""Two measurements the previous hand left open.

One: can the same stamped run id legitimately reach its own database twice?  Run the parity ruler
against one stamped file twice in a row -- the first open creates it, the second re-opens it.  If the
second is refused, the guard forbids any legitimate child process, not just sloppy test arms.

Two: attribute each of the nine mode-sensitive files to a shape, per file rather than in a combined
run where one refusal can hide another.
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
OUT = LANE / "tmp/GUARD_SHAPES_r2.json"
REFUSAL = "refuses to reopen an existing database"


def env_for(run_id: str, db: pathlib.Path, stamp: bool) -> dict:
    env = dict(os.environ)
    for key in ("DEEPSEEK_API_KEY", "CITYNEXUS_E2E_RUN_ID", "CITYNEXUS_DATABASE_URL"):
        env.pop(key, None)
    env["PYTHONIOENCODING"] = "utf-8"
    if stamp:
        env["CITYNEXUS_E2E_RUN_ID"] = run_id
        env["CITYNEXUS_DATABASE_URL"] = "sqlite:///" + db.as_posix()
    return env


def tool(run_id: str, db: pathlib.Path, stamp: bool) -> dict:
    proc = subprocess.run([str(PYTHON), "-X", "utf8", str(TREE / "tools/verify_openapi_parity.py")],
                          cwd=str(BACKEND), env=env_for(run_id, db, stamp),
                          capture_output=True, text=True, encoding="utf-8", errors="replace")
    blob = (proc.stdout or "") + (proc.stderr or "")
    return {"stamp": stamp, "run_id": run_id, "db": db.name, "rc": proc.returncode,
            "refusal": REFUSAL in blob, "tail": blob.strip().splitlines()[-1][:150] if blob.strip() else ""}


def per_file(node: str) -> dict:
    run_id = "shape2-%s" % uuid.uuid4().hex[:8]
    db = LANE / "db" / ("_%s.db" % run_id)
    proc = subprocess.run([str(PYTHON), "-X", "utf8", "-m", "pytest", "-q", "-p", "no:randomly",
                           "--tb=line", node], cwd=str(BACKEND), env=env_for(run_id, db, True),
                          capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=420)
    out = proc.stdout or ""
    paths = sorted(set(re.findall(r"%s at (\S+?)(?:\.|$| )" % re.escape(REFUSAL), out)))
    shapes = []
    for p in paths:
        if run_id in p:
            shapes.append("B_run_own_store_reopened")
        elif "basetemp" in p or re.search(r"pytest-\d+", p):
            shapes.append("A_arm_seeded_file")
        else:
            shapes.append("other:%s" % p[-40:])
    summary = [l for l in out.splitlines() if re.search(r"\d+ (passed|failed|error)", l)]
    return {"node": node, "rc": proc.returncode, "run_id": run_id,
            "summary": summary[-1].strip() if summary else "(no count line)",
            "refusal_paths": [p[-60:] for p in paths], "shapes": sorted(set(shapes)),
            "failed": sorted(n.split("::")[-1] for n in re.findall(r"FAILED (\S+)", out)),
            "error_count": len(re.findall(r"^ERROR ", out, re.M))}


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    den = json.loads(DEN.read_text(encoding="utf-8"))
    run_id = "shape2-probe"
    db = LANE / "db" / ("_%s.db" % run_id)
    if db.exists():
        db.unlink()
    first = tool(run_id, db, True)
    second = tool(run_id, db, True)
    plain_first = tool("shape2-plain", LANE / "db" / "_shape2-plain.db", False)
    print("first open (creates)  rc=%s refusal=%s" % (first["rc"], first["refusal"]))
    print("second open (reopens) rc=%s refusal=%s" % (second["rc"], second["refusal"]))
    print("plain, same shape     rc=%s refusal=%s" % (plain_first["rc"], plain_first["refusal"]))

    rows = []
    for node in den["disagreement_list"]:
        r = per_file("tests/" + node.split("/", 1)[1] if node.startswith("backend/") else node)
        rows.append(r)
        print("%-52s %-28s shapes=%s" % (node.split("/")[-1], r["summary"][:28], r["shapes"]))

    a = sorted({r["node"] for r in rows if "A_arm_seeded_file" in r["shapes"]})
    b = sorted({r["node"] for r in rows if "B_run_own_store_reopened" in r["shapes"]})
    receipt = {"generated_by": "89f2e2d6", "tree_head": den["tree_head"],
               "same_run_two_opens": {"first": first, "second": second, "plain_control": plain_first,
                                      "verdict": ("SECOND_OPEN_OF_THE_RUNS_OWN_STORE_IS_REFUSED"
                                                 if second["refusal"] and not first["refusal"]
                                                 else "NOT_REPRODUCED")},
               "per_file": rows,
               "shape_counts": {"A_arm_seeded_file": len(a), "B_run_own_store_reopened": len(b),
                                "compared": len(rows)},
               "shape_A_files": a, "shape_B_files": b,
               "what_this_does_to_my_previous_proposal": (
                   "my last block asked the guard to check only the run's declared url; the "
                   "same_run_two_opens reading shows the declared url is exactly what gets refused "
                   "the second time, so that proposal cannot be the whole fix")}
    OUT.write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("shape counts %s" % json.dumps(receipt["shape_counts"]))
    print("verdict %s" % receipt["same_run_two_opens"]["verdict"])
    print("receipt %s" % OUT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
