"""Finish the denominator I left unmeasured: every test file that opens its own sqlite file, run in
the stamped (authoritative) mode; the plain mode is measured only where stamping produced a red.

Readings are appended as they happen, so an interrupted run still leaves what was actually measured.
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
LOG = LANE / "tmp/GUARD_DENOMINATOR_r1.jsonl"
ALREADY = {
    "tests/test_qoder_provider_identity_leg.py",
    "tests/test_qoder_ord197_four_class_receipt.py",
    "tests/test_ord0526_offline_source_row_count_r1.py",
    "tests/test_qoder_pending_destination_identity.py",
}
SEED = re.compile(r'tmp_path / "\S+\.db"|sqlite3\.connect\(|create_engine\(f?"sqlite|make_engine\(')


def run(args: list[str], stamp: bool) -> dict:
    env = dict(os.environ)
    for key in ("DEEPSEEK_API_KEY", "CITYNEXUS_E2E_RUN_ID", "CITYNEXUS_DATABASE_URL"):
        env.pop(key, None)
    env["PYTHONIOENCODING"] = "utf-8"
    run_id = ""
    if stamp:
        run_id = "guardden-%s" % uuid.uuid4().hex[:8]
        db = LANE / "db" / ("_%s.db" % run_id)
        env["CITYNEXUS_DATABASE_URL"] = "sqlite:///" + db.as_posix()
        env["CITYNEXUS_E2E_RUN_ID"] = run_id
    started = datetime.datetime.now()
    try:
        proc = subprocess.run([str(PYTHON), "-X", "utf8", "-m", "pytest", "-q", "-p", "no:randomly"] + args,
                              cwd=str(BACKEND), env=env, capture_output=True, text=True,
                              encoding="utf-8", errors="replace", timeout=420)
        out = proc.stdout or ""
    except subprocess.TimeoutExpired:
        return {"mode": "stamped" if stamp else "plain", "timeout": True, "rc": None,
                "summary": "(timed out at 420 s)", "red_set": [], "seconds": 420}
    summary = [l for l in out.splitlines() if re.search(r"\d+ (passed|failed|error)", l)]
    seconds = re.search(r"in ([\d.]+)s", summary[-1] if summary else "")
    return {"mode": "stamped" if stamp else "plain", "timeout": False, "rc": proc.returncode,
            "run_id": run_id or "(none)",
            "summary": summary[-1].strip() if summary else "(no count line)",
            "seconds": float(seconds.group(1)) if seconds else None,
            "red_set": sorted(n.split("::")[-1] for n in re.findall(r"FAILED (\S+)", out)),
            "errors": sorted(set(re.findall(r"^ERROR (\S+)", out, re.M)))[:4]}


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    lo, hi = int(sys.argv[1]), int(sys.argv[2])
    tip = subprocess.run(["git", "-C", str(TREE), "rev-parse", "HEAD"], capture_output=True,
                         text=True, encoding="utf-8").stdout.strip()
    all_seed = sorted(p.name for p in (BACKEND / "tests").glob("test_*.py")
                      if SEED.search((BACKEND / "tests" / p.name).read_text(encoding="utf-8",
                                                                             errors="replace")))
    todo = ["tests/" + n for n in all_seed if "tests/" + n not in ALREADY]
    print("seeded_files=%d already_compared=%d todo=%d this chunk=[%d,%d)"
          % (len(all_seed), len(ALREADY), len(todo), lo, hi))
    for f in todo[lo:hi]:
        stamped = run([f], True)
        rec = {"tree_head": tip, "file": f, "stamped": stamped, "plain": None}
        control = None
        # an ERROR is as much a refusal as a FAILED: the guard can kill a fixture before any arm runs
        if stamped["red_set"] or stamped.get("errors") or stamped["timeout"]:
            control = run([f], False)
            rec["plain"] = control
        differs = bool(control and (sorted(set(control["red_set"]) ^ set(stamped["red_set"]))
                                    or sorted(set(control.get("errors") or [])) != sorted(
                                        stamped.get("errors") or [])))
        rec["differs"] = differs
        with LOG.open("a", encoding="utf-8") as sink:
            sink.write(json.dumps(rec, ensure_ascii=False) + "\n")
        print("%-58s stamped=%-40s plain=%-24s differs=%s"
              % (f.split("/")[-1], stamped["summary"],
                 (control or {}).get("summary", "(no control needed)"), differs))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
