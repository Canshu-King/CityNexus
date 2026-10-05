"""Is `test_abandon_reports_a_request_not_a_death` a flake or my patch? Rate it, both states.

The r1 A/B report's own verdict was wrong in the direction of blaming me: it compared UNION sets of
red names across six batches per state, and the abandon family (four arms in
`tests/test_qoder_catalog_hydration.py`: `_a_worker_that_wakes_on_an_abandoned_row_closes_it_instead_of_running_it_`,
`_abandon_reports_a_request_not_a_death`, `_abandon_from_another_process_resolves_the_terminal_write_as_abandoned`,
`_abandon_whose_own_write_never_landed_still_closes_the_job`) produced a different member on each
side.  That is one flaky family showing two faces, not two behaviours.

This run measures the family properly: the same file, ten batches per state, and the unit of count
is "an abandon-family arm went red", reported per arm name.  It also records whether the arm my
patch touches (`GET /api/v1/destinations/capability`) is even on the failing arms' path -- the
answer is read out of the file's own source, not asserted from memory.
"""

from __future__ import annotations

import datetime
import json
import pathlib
import re
import subprocess

TREE = pathlib.Path(r"D:/moodle/_qoder_lane_ord0520_20260930/wt2")
BACKEND = TREE / "backend"
DBDIR = TREE.parent / "db"
PATCH = TREE / "tmp/osmt_product.patch"
PYTHON = pathlib.Path(r"D:/moodle/CityNexus/.venv/Scripts/python.exe")
ROWS = TREE.parent / "tmp/OSMT_ABANDON_FAMILY_r1.jsonl"
REPORT = TREE.parent / "tmp/OSMT_ABANDON_FAMILY_r1.json"

FILE = "tests/test_qoder_catalog_hydration.py"
FAMILY = [
    "test_a_worker_that_wakes_on_an_abandoned_row_closes_it_instead_of_running_it",
    "test_abandon_reports_a_request_not_a_death",
    "test_an_abandon_from_another_process_resolves_the_terminal_write_as_abandoned",
    "test_an_abandon_whose_own_write_never_landed_still_closes_the_job",
]


def git(*args: str) -> int:
    return subprocess.run(["git", "-C", str(TREE), *args], capture_output=True).returncode


def run(state: str) -> dict:
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%H%M%S%f")
    db = DBDIR / ("_osmt-fam-%s-%s.db" % (state, stamp))
    env = dict(subprocess.os.environ)
    env.pop("DEEPSEEK_API_KEY", None)
    env["CITYNEXUS_DATABASE_URL"] = "sqlite:///" + db.as_posix()
    env["PYTHONIOENCODING"] = "utf-8"
    proc = subprocess.run(
        [str(PYTHON), "-X", "utf8", "-m", "pytest", "-q", "-p", "no:randomly", "--no-header", FILE],
        cwd=str(BACKEND), env=env, capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    out = proc.stdout or ""
    failed = re.findall(r"FAILED \S+::(\S+)", out)
    counts = re.search(r"(\d+) failed, (\d+) passed", out)
    for suffix in ("", "-wal", "-shm"):
        path = pathlib.Path(str(db) + suffix)
        if path.exists():
            path.unlink()
    return {
        "state": state,
        "db": db.name,
        "rc": proc.returncode,
        "failed": sorted(failed),
        "family_red": sorted(n for n in failed if n in FAMILY),
        "summary": counts.group(0) if counts else out.strip()[-160:],
    }


# Does the failing arm's own source ever ask the door my patch changes? Read it out, don't assume.
source = (BACKEND / FILE).read_text(encoding="utf-8")
arm_bodies: dict[str, bool] = {}
for name in FAMILY:
    start = source.index("def " + name)
    nxt = source.find("\ndef ", start + 1)
    body = source[start:nxt if nxt > 0 else len(source)]
    arm_bodies[name] = "destinations/capability" in body or "CAPABILITY" in body

rows: list[dict] = []
ROWS.unlink(missing_ok=True)
try:
    for state in ("patched", "tip_bytes"):
        if state == "tip_bytes":
            assert git("apply", "-R", str(PATCH)) == 0
        for _ in range(10):
            row = run(state)
            rows.append(row)
            ROWS.open("a", encoding="utf-8").write(json.dumps(row, ensure_ascii=False) + "\n")
            print("%-9s %-60s family_red=%s | %s"
                  % (state, row["summary"], row["family_red"], row["db"]))
finally:
    if git("apply", str(PATCH)) != 0:
        print("NOTE restore rc!=0 (may already be applied)")

per_state: dict[str, dict] = {}
for state in ("patched", "tip_bytes"):
    sel = [r for r in rows if r["state"] == state]
    per_state[state] = {
        "batches": len(sel),
        "batches_with_family_red": sum(1 for r in sel if r["family_red"]),
        "family_red_by_arm": {
            arm: sum(1 for r in sel if arm in r["family_red"]) for arm in FAMILY
        },
        "non_family_red_names": sorted({n for r in sel for n in r["failed"] if n not in FAMILY}),
    }

report = {
    "measured_against_head": subprocess.run(["git", "-C", str(TREE), "rev-parse", "HEAD"],
                                            capture_output=True, text=True).stdout.strip(),
    "family_arms": len(FAMILY),
    "each_state": per_state,
    "failing_arms_read_the_capability_door": arm_bodies,
    "verdict": None,
}
p_bad = per_state["patched"]["batches_with_family_red"]
b_bad = per_state["tip_bytes"]["batches_with_family_red"]
report["family_red_rate_patched"] = "%d/%d" % (p_bad, per_state["patched"]["batches"])
report["family_red_rate_tip_bytes"] = "%d/%d" % (b_bad, per_state["tip_bytes"]["batches"])
only_p = set(per_state["patched"]["non_family_red_names"]) - set(per_state["tip_bytes"]["non_family_red_names"])
report["verdict"] = (
    "FLAKY_ON_BOTH_STATES_NOT_ATTRIBUTABLE_TO_THE_PATCH"
    if (p_bad or b_bad) and not only_p
    else ("NEITHER_STATE_FLAKED_THIS_RUN" if not (p_bad or b_bad) else "STILL_UNRESOLVED")
)
REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps(report, ensure_ascii=False, indent=2))
