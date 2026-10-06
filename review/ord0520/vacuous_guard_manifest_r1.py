"""A re-runnable inventory of the three guarded instruments: entry, command, expected verdict.

Three cells of this lane added a guard to each of three instruments so a verdict cannot be computed over a
shorter set than it claims.  Each guard has two halves that only mean something together:

  * the refusal half -- the short sets must be refused BY NAME;
  * the control half -- the real stack, where everything is present, must be ALLOWED.

A manifest that lists only the refusal half would pass a guard that refuses everything, and one that lists
only the control would pass a guard that never fires.  So each row here states both, and running this file
RE-RUNS each arm and compares what came back with what is promised.  A row whose file is missing, or whose
verdict line does not match, is reported as a failure rather than skipped: "the file is not there" and "the
file says something else" are different answers and neither is a pass.

Exit code is non-zero when any row fails, so this file can be the receipt the next reader runs instead of
trusting this lane's memory.
"""

from __future__ import annotations

import importlib.util
import io
import json
import pathlib
import subprocess
import sys

HERE = pathlib.Path(__file__).resolve().parent
PYTHON = pathlib.Path(r"D:/moodle/CityNexus/.venv/Scripts/python.exe")

ROWS = [
    {
        "guard": "abort_glass_provenance_r3",
        "guard_file": "abort_glass_provenance_r3.py",
        "guard_at": "refuse_unless_all_present",
        "arm_file": "vacuous_guard_gap_closed_arm_r1.py",
        "arm_promised_verdict": "BOTH_GUARDS_REFUSE_THE_EMPTY_CASE_AND_ALLOW_THE_FULL_ONE",
        "control_receipt": "ABORT_GLASS_PROVENANCE_r3.json",
        "control_promised": "PROVENANCE_OK",
        "control_field": "verdict",
    },
    {
        "guard": "osmt_flake_attribution_r3",
        "guard_file": "osmt_flake_attribution_r3.py",
        "guard_at": "refuse_unless_states_present",
        "arm_file": "vacuous_guard_gap_closed_arm_r1.py",
        "arm_promised_verdict": "BOTH_GUARDS_REFUSE_THE_EMPTY_CASE_AND_ALLOW_THE_FULL_ONE",
        "control_receipt": None,
        "control_promised": None,
        "control_field": None,
    },
    {
        "guard": "abort_http_probe_r3",
        "guard_file": "abort_http_probe_r3.py",
        "guard_at": "refuse_unless_all_present",
        "arm_file": "vacuous_guard_partial_arms_r1.py",
        "arm_promised_verdict": "REFUSES_EVERY_PARTIAL_SET_AND_ALLOWS_THE_FULL_ONE",
        "control_receipt": "ABORT_HTTP_RECEIPT_r3.json",
        "control_promised": "PASSED",
        "control_field": "verdict_computed_from_the_rows_above",
    },
]


def arm_verdict(path: pathlib.Path) -> tuple[str, int, str]:
    proc = subprocess.run([str(PYTHON), "-X", "utf8", str(path)], capture_output=True,
                          text=True, encoding="utf-8", errors="replace")
    line = next((l for l in (proc.stdout or "").splitlines() if l.startswith("VERDICT")), "NO_VERDICT_LINE")
    return line.split(" ", 1)[1] if " " in line else line, proc.returncode, (proc.stdout or "")[-300:]


def guard_present(path: pathlib.Path, needle: str) -> bool:
    return needle in path.read_text(encoding="utf-8")


def self_check() -> str:
    """Run the row checks WITHOUT printing and return the verdict word only."""

    saved = sys.stdout
    sys.stdout = io.StringIO()
    try:
        failures: list[str] = []
        for row in ROWS:
            guard_path = HERE / row["guard_file"]
            arm_path = HERE / row["arm_file"]
            if not guard_path.exists() or not arm_path.exists():
                failures.append(row["guard"])
                continue
            verdict, rc, _ = arm_verdict(arm_path)
            if verdict != row["arm_promised_verdict"] or rc != 0:
                failures.append(row["guard"])
        return "MANIFEST_FAILED" if failures else "ALL_THREE_GUARDS_REPRODUCE_THEIR_PROMISED_HALVES"
    finally:
        sys.stdout = saved


def main() -> int:
    failures: list[str] = []
    report: list[dict] = []

    for row in ROWS:
        guard_path = HERE / row["guard_file"]
        arm_path = HERE / row["arm_file"]
        entry = {"guard": row["guard"], "guard_file": row["guard_file"], "arm_file": row["arm_file"]}

        if not guard_path.exists():
            entry["status"] = "GUARD_FILE_MISSING"
            failures.append("%s: %s is not here" % (row["guard"], row["guard_file"]))
            report.append(entry)
            continue
        if not arm_path.exists():
            entry["status"] = "ARM_FILE_MISSING"
            failures.append("%s: %s is not here" % (row["guard"], row["arm_file"]))
            report.append(entry)
            continue

        entry["guard_carries_its_predicate"] = guard_present(guard_path, "def %s(" % row["guard_at"])
        if not entry["guard_carries_its_predicate"]:
            failures.append("%s: no %s in %s" % (row["guard"], row["guard_at"], row["guard_file"]))

        verdict, rc, tail = arm_verdict(arm_path)
        entry["arm_ran_rc"] = rc
        entry["arm_verdict"] = verdict
        entry["arm_matches_promise"] = (verdict == row["arm_promised_verdict"] and rc == 0)
        if not entry["arm_matches_promise"]:
            failures.append("%s: arm said %r rc=%s, promised %r"
                            % (row["guard"], verdict, rc, row["arm_promised_verdict"]))

        if row["control_receipt"]:
            receipt_path = HERE / row["control_receipt"]
            if not receipt_path.exists():
                entry["status"] = "CONTROL_RECEIPT_MISSING"
                failures.append("%s: control receipt %s is not here" % (row["guard"], row["control_receipt"]))
                report.append(entry)
                continue
            receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
            entry["control_receipt"] = row["control_receipt"]
            entry["control_verdict"] = receipt.get(row["control_field"])
            entry["control_matches_promise"] = receipt.get(row["control_field"]) == row["control_promised"]
            if not entry["control_matches_promise"]:
                failures.append("%s: control receipt says %r, promised %r"
                                % (row["guard"], receipt.get(row["control_field"]), row["control_promised"]))
        else:
            entry["control_receipt"] = "shared with the row above (same arm file runs both guards)"

        entry["status"] = "OK" if entry.get("arm_matches_promise") else "ARM_DISAGREES"
        report.append(entry)

    for entry in report:
        print(json.dumps(entry, ensure_ascii=False))

    # A manifest that cannot fail is a decoration.  Two broken variants are driven here, in memory, and
    # both must come back MANIFEST_FAILED: one that promises a verdict nothing produces, and one whose row
    # names a file that is not there.  Only then is the green above worth anything.
    controls = []
    for label, mutate in (
        ("a promise nothing produces",
         {"arm_promised_verdict": "SOMETHING_THAT_IS_NOT_THE_VERDICT"}),
        ("a row naming a file that is not there",
         {"guard_file": "abort_http_probe_r3_NOT_HERE.py"}),
    ):
        ROWS[2] = dict(ROWS[2], **mutate)
        controls.append((label, self_check()))
        ROWS[2] = {k: v for k, v in ROWS[2].items() if k not in mutate}
    bad = [label for label, outcome in controls if outcome != "MANIFEST_FAILED"]
    for label, outcome in controls:
        print("NEGATIVE_CONTROL %-40s -> %s" % (label, outcome))
    if bad:
        failures.append("the manifest did not fail on: %s" % ", ".join(bad))

    # The verdict is derived here, from this run's failures -- never carried over from a loop variable
    # that may still hold some other file's word.
    verdict = "ALL_THREE_GUARDS_REPRODUCE_THEIR_PROMISED_HALVES" if not failures else "MANIFEST_FAILED"
    print("VERDICT %s" % verdict)
    for line in failures:
        print("FAIL %s" % line)
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())