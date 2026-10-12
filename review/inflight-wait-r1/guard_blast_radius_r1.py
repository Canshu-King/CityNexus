"""Blast radius of the fresh-database guard, measured in two modes rather than predicted.

Same tree, same file, two invocations: one stamped with CITYNEXUS_E2E_RUN_ID (the mode the standing
rule tells every lane to use) and one plain pytest run.  A file whose red set differs between the
two is a file where the guard, not the product, decides what a lane reports as broken.

Sample is named and small; whatever was not run is written out as not measured, not assumed green.
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
OUT = LANE / "tmp/GUARD_BLAST_RADIUS_r1.json"

FILES = [
    "tests/test_qoder_provider_identity_leg.py",
    "tests/test_qoder_ord197_four_class_receipt.py",
    "tests/test_ord0526_offline_source_row_count_r1.py",
]
SECONDS_LIMIT = 240


def run(args: list[str], stamp: bool) -> dict:
    env = dict(os.environ)
    env.pop("DEEPSEEK_API_KEY", None)
    run_id = ""
    if stamp:
        run_id = "guardchk-%s" % uuid.uuid4().hex[:8]
        db = LANE / "db" / ("_%s.db" % run_id)
        env["CITYNEXUS_DATABASE_URL"] = "sqlite:///" + db.as_posix()
        env["CITYNEXUS_E2E_RUN_ID"] = run_id
    env["PYTHONIOENCODING"] = "utf-8"
    started = datetime.datetime.now(datetime.timezone.utc)
    proc = subprocess.run([str(PYTHON), "-X", "utf8", "-m", "pytest", "-q", "-p", "no:randomly"] + args,
                          cwd=str(BACKEND), env=env, capture_output=True, text=True,
                          encoding="utf-8", errors="replace", timeout=SECONDS_LIMIT)
    out = proc.stdout or ""
    summary = [l for l in out.splitlines() if re.search(r"\d+ (passed|failed|error)", l)]
    seconds = re.search(r"in ([\d.]+)s", summary[-1] if summary else "")
    return {"mode": "authoritative_run_id" if stamp else "plain_pytest",
            "run_id": run_id or "(none)",
            "started_utc": started.strftime("%H%M%SZ"),
            "rc": proc.returncode,
            "summary": summary[-1].strip() if summary else "(no count line)",
            "seconds": seconds.group(1) if seconds else "(none)",
            "red_set": sorted(n.split("::")[-1] for n in re.findall(r"FAILED (\S+)", out)),
            "errors": sorted(set(re.findall(r"ERROR (\S+)", out)))[:5]}


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    tip = subprocess.run(["git", "-C", str(TREE), "rev-parse", "HEAD"], capture_output=True,
                         text=True, encoding="utf-8").stdout.strip()
    files_scanned = sorted(p.name for p in (BACKEND / "tests").glob("test_*.py"))
    seeding = [p.name for p in (BACKEND / "tests").glob("test_*.py")
               if re.search(r"tmp_path / \"\S+\.db\"|sqlite3\.connect\(|create_engine\(f?\"sqlite|make_engine\(",
                            p.read_text(encoding="utf-8", errors="replace"))]
    receipt = {"generated_by": "89f2e2d6", "tree_head": tip, "pairs": [],
               "denominators": {"test_files_in_tree": len(files_scanned),
                                "files_that_open_their_own_sqlite": len(seeding)},
               "sample": FILES, "not_measured_by_lane": [f for f in seeding
                                                          if "tests/" + f not in FILES]}
    for f in FILES:
        stamped = run([f], True)
        plain = run([f], False)
        diff = sorted(set(stamped["red_set"]) ^ set(plain["red_set"]))
        receipt["pairs"].append({"file": f, "authoritative": stamped, "plain": plain,
                                 "red_set_differs": bool(diff), "arms_only_one_mode_reports": diff})
        print("%-52s stamped=%-34s plain=%-30s differs=%s"
              % (f.split("/")[-1], stamped["summary"], plain["summary"], bool(diff)))
        for arm in diff:
            print("      differs: %s" % arm)
    OUT.write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("denominators %s" % json.dumps(receipt["denominators"]))
    print("receipt %s" % OUT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
