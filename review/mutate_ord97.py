"""Kill evidence for ORD-0097: four sabotages, each owned by a named gate.

Run:  python review/mutate_ord97.py
Writes: D:/moodle/_qoder_ord30_evidence_20260920/ord97/kill-evidence.json

The order's acceptance is a statement that can be falsified: "which plan is current" must be
the journey's pointer, not the array position, not the row's status, and not the newest
version.  So each of those three wrong answers is installed as a mutant, plus a fourth that
puts back the `select_plan` guard exactly as it was written - the one that answered 409 to
switching a selection on a journey that was never started.  Both source files are restored
from raw bytes and verified by SHA-256.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path

TREE = Path(r"D:\moodle\_qoder_integration_20260919")
SERVICES = TREE / "backend" / "app" / "services.py"
MAIN = TREE / "backend" / "app" / "main.py"
TEST_FILE = "tests/test_qoder_current_plan_is_named.py"
PYTHON = Path(r"D:\moodle\CityNexus\.venv\Scripts\python.exe")
OUT = Path(r"D:\moodle\_qoder_ord30_evidence_20260920\ord97\kill-evidence.json")

POINTER_TRUTH = '        is_current=str(current_plan_version_id or "") == item.id,'
LIST_CALL = """    return [
        plan_schema(session, item, current_plan_version_id=journey.active_plan_version_id)
        for item in items
    ]"""
GUARD_ORIGINAL = """        abandoned = session.get(PlanVersion, abandoned_id)
        if abandoned is not None and abandoned.status == "ACTIVE":
"""
GUARD_UNSCOPED = """        if True:  # mutant: the guard is unscoped again, so a SELECTED pointer is retired too
"""

MUTANTS = [
    {
        "name": "M1 every row of a pointed-to journey claims to be current",
        "file": SERVICES,
        "old": POINTER_TRUTH,
        "new": "        is_current=bool(current_plan_version_id),",
        "gate": "test_the_current_plan_is_named_and_is_not_the_last_row",
    },
    {
        "name": "M2 the endpoint elects the last item in the array (order as truth)",
        "file": MAIN,
        "old": LIST_CALL,
        "new": """    return [
        plan_schema(session, item, current_plan_version_id=items[-1].id if items else None)
        for item in items
    ]""",
        "gate": "test_the_current_plan_is_named_and_is_not_the_last_row",
    },
    {
        "name": "M3 is_current is derived from status instead of the pointer",
        "file": SERVICES,
        "old": POINTER_TRUTH,
        "new": '        is_current=item.status in {"SELECTED", "ACTIVE"},',
        "gate": "test_a_journey_without_a_pointer_names_nothing_rather_than_the_first_row",
    },
    {
        "name": "M4 the pre-start guard is unscoped again (switching a selection 409s)",
        "file": MAIN,
        "old": GUARD_ORIGINAL,
        "new": GUARD_UNSCOPED,
        "gate": "test_selecting_another_candidate_moves_the_answer_not_the_order",
    },
]


def run_gate(gate: str) -> tuple[int, str]:
    completed = subprocess.run(
        [str(PYTHON), "-m", "pytest", TEST_FILE, "-q", "--no-header", "-k", gate,
         "-p", "no:cacheprovider"],
        cwd=TREE / "backend",
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    return completed.returncode, completed.stdout + completed.stderr


def main() -> int:
    originals = {path: path.read_bytes() for path in (SERVICES, MAIN)}
    digests = {path: hashlib.sha256(raw).hexdigest() for path, raw in originals.items()}
    results = []
    try:
        for mutant in MUTANTS:
            path = mutant["file"]
            text = originals[path].decode("utf-8")
            hits = text.count(mutant["old"])
            if hits != 1:
                results.append({"mutant": mutant["name"], "verdict": "NOT-MEASURED", "anchor_hits": hits})
                continue
            path.write_bytes(text.replace(mutant["old"], mutant["new"]).encode("utf-8"))
            code, output = run_gate(mutant["gate"])
            summary = [line for line in output.splitlines() if " passed" in line or " failed" in line]
            results.append(
                {
                    "mutant": mutant["name"],
                    "owner_gate": mutant["gate"],
                    "killed": code != 0,
                    "summary": summary[-1] if summary else output[-200:],
                }
            )
            path.write_bytes(originals[path])
    finally:
        for path, raw in originals.items():
            path.write_bytes(raw)

    payload = {
        "restored": all(
            hashlib.sha256(path.read_bytes()).hexdigest() == digest for path, digest in digests.items()
        ),
        "cases": results,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8", newline="\n")
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    return 0 if payload["restored"] and all(item.get("killed") for item in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
