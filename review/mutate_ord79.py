"""Kill evidence for the ORD-0079 gates: three mutants, each must turn its own gate red.

Run:  python ../_qoder_scratch/mutate_ord79.py   (from the integration tree root this is easier:
      python review/mutate_ord79.py)

Why it is needed here: the new `evidence_state` has four values, and a green assertion on one of
them proves nothing unless the other three are reachable by the code and unreachable by a lie.
Each mutant is a one-line sabotage of the exact predicate the gate claims to test, the file is
restored from raw bytes afterwards (never `write_text`, which would flip LF to CRLF), and the
restoration is verified by SHA-256 against the pre-mutation digest.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

TREE = Path(r"D:\moodle\_qoder_integration_20260919")
TARGET = TREE / "backend" / "app" / "main.py"
TESTS = ["tests/test_qoder_mobility_evidence_sources.py"]
PYTHON = Path(r"D:\moodle\CityNexus\.venv\Scripts\python.exe")

MUTANTS = [
    {
        "name": "M1 fall back to the old proxy: a plan with no declared TTL reads as no evidence",
        "old": '        evidence_state = "FROZEN_WITHOUT_TTL"\n',
        "new": '        evidence_state = "NO_FROZEN_EVIDENCE"\n',
        "expect": "test_a_plan_without_a_declared_ttl_is_frozen_evidence_not_absent_evidence",
    },
    {
        "name": "M2 count legs unconditionally instead of asking hard_minutes",
        "old": '        "legs_hard_eligible": hard_eligible,\n',
        "new": '        "legs_hard_eligible": len(legs),\n',
        "expect": "test_the_read_fails_closed_when_the_plan_really_has_nothing",
    },
    {
        "name": "M3 trust any non-empty snapshot id, dropping the column cross-check",
        "old": '        "reference_consistent": bool(snapshot_id) and snapshot_id == plan.mobility_snapshot_id,\n',
        "new": '        "reference_consistent": bool(snapshot_id),\n',
        "expect": "test_a_pointer_that_disagrees_with_its_own_payload_is_reported_as_inconsistent",
    },
]


def run_suite() -> tuple[int, str]:
    completed = subprocess.run(
        [str(PYTHON), "-m", "pytest", *TESTS, "-q", "--no-header", "-p", "no:cacheprovider"],
        cwd=TREE / "backend",
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    return completed.returncode, completed.stdout + completed.stderr


def main() -> int:
    original = TARGET.read_bytes()
    digest = hashlib.sha256(original).hexdigest()
    text = original.decode("utf-8")
    results = []
    try:
        for mutant in MUTANTS:
            occurrences = text.count(mutant["old"])
            if occurrences != 1:
                results.append(
                    {
                        "mutant": mutant["name"],
                        "verdict": "NOT-MEASURED",
                        "reason": f"anchor matched {occurrences} times, not 1",
                    }
                )
                continue
            TARGET.write_bytes(text.replace(mutant["old"], mutant["new"]).encode("utf-8"))
            code, output = run_suite()
            failed = [
                line.split("::")[-1].split(" ")[0]
                for line in output.splitlines()
                if line.startswith("FAILED")
            ]
            results.append(
                {
                    "mutant": mutant["name"],
                    "suite_exit": code,
                    "failed_tests": failed,
                    "expected_to_hit": mutant["expect"],
                    "killed": code != 0 and any(mutant["expect"] in item for item in failed),
                }
            )
            TARGET.write_bytes(original)
            assert hashlib.sha256(TARGET.read_bytes()).hexdigest() == digest, "restore failed"
    finally:
        TARGET.write_bytes(original)

    restored = hashlib.sha256(TARGET.read_bytes()).hexdigest() == digest
    print(json.dumps({"restored": restored, "mutants": results}, indent=2, ensure_ascii=False))
    out = Path(r"D:\moodle\_qoder_ord30_evidence_20260920\ord79\kill-evidence.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({"restored": restored, "mutants": results}, indent=2, ensure_ascii=False), encoding="utf-8", newline="\n")
    print("->", out)
    return 0 if restored and all(item.get("killed") for item in results) else 1


if __name__ == "__main__":
    sys.exit(main())
