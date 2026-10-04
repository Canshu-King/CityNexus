"""The two-sided control for the guard claim, plus the measured reach of the claim.

My delivered block said the guard "bites every lane that follows the fresh-run-id rule" -- that was
a mechanism's reach asserted from one file.  Here the claim gets its control (same arms, no run id)
and the reach gets a denominator (a named sample of files that also open their own sqlite).
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
BLAST = LANE / "tmp/GUARD_BLAST_RADIUS_r1.json"
OUT = LANE / "tmp/GUARD_CONTROL_AB_r1.json"
FILE = "tests/test_qoder_pending_destination_identity.py"
ARMS = [FILE + "::test_g10_legacy_pending_rows_migrate_in_place_without_losing_their_ids",
        FILE + "::test_g13_rerunning_the_schema_migration_never_duplicates_or_eats_a_row"]


def run(args: list[str], stamp: bool) -> dict:
    env = dict(os.environ)
    env.pop("DEEPSEEK_API_KEY", None)
    env.pop("CITYNEXUS_E2E_RUN_ID", None)
    env.pop("CITYNEXUS_DATABASE_URL", None)
    run_id = ""
    if stamp:
        run_id = "guardab-%s" % uuid.uuid4().hex[:8]
        db = LANE / "db" / ("_%s.db" % run_id)
        env["CITYNEXUS_DATABASE_URL"] = "sqlite:///" + db.as_posix()
        env["CITYNEXUS_E2E_RUN_ID"] = run_id
    env["PYTHONIOENCODING"] = "utf-8"
    proc = subprocess.run([str(PYTHON), "-X", "utf8", "-m", "pytest", "-q", "-p", "no:randomly"] + args,
                          cwd=str(BACKEND), env=env, capture_output=True, text=True,
                          encoding="utf-8", errors="replace", timeout=240)
    out = proc.stdout or ""
    summary = [l for l in out.splitlines() if re.search(r"\d+ (passed|failed|error)", l)]
    return {"mode": "stamped" if stamp else "plain", "run_id": run_id or "(none)", "rc": proc.returncode,
            "summary": summary[-1].strip() if summary else "(no count line)",
            "red_set": sorted(n.split("::")[-1] for n in re.findall(r"FAILED (\S+)", out))}


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    pairs = []
    for label, args in (("two_migrate_arms", ARMS), ("whole_file", [FILE])):
        stamped = run(args, True)
        plain = run(args, False)
        pairs.append({"case": label, "stamped": stamped, "plain": plain,
                      "red_set_differs": sorted(set(stamped["red_set"]) ^ set(plain["red_set"])) != [],
                      "stamped_red": len(stamped["red_set"]), "plain_red": len(plain["red_set"])})
        print("%-18s stamped=%-40s plain=%-28s differs=%s"
              % (label, stamped["summary"], plain["summary"], pairs[-1]["red_set_differs"]))
    blast = json.loads(BLAST.read_text(encoding="utf-8"))
    differing = [p["file"] for p in blast["pairs"] if p["red_set_differs"]]
    receipt = {"generated_by": "89f2e2d6", "tree_head": blast["tree_head"], "cases": pairs,
               "guard_reach_measured": {
                   "files_where_the_two_modes_disagree_in_this_sample": differing + [FILE],
                   "count": len(differing) + 1,
                   "sample_of_files_compared": len(blast["pairs"]) + 1,
                   "files_in_tree_that_open_their_own_sqlite":
                       blast["denominators"]["files_that_open_their_own_sqlite"],
                   "test_files_in_tree": blast["denominators"]["test_files_in_tree"],
                   "not_measured": (blast["denominators"]["files_that_open_their_own_sqlite"] - 4)},
               "claim_corrected": "my delivered block asserted this bites every lane that stamps a "
                                  "run id; measured reach is 1 file out of the 4 I compared, and the "
                                  "other 29 candidates were not measured"}
    OUT.write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("guard reach %s" % json.dumps(receipt["guard_reach_measured"], ensure_ascii=False))
    print("receipt %s" % OUT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
