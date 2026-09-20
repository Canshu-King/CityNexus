"""Kill evidence for the false-202 fix: put the pre-fix behaviour back, one clause at a time.

Run:  python review/mutate_ord57_restage.py
Writes: D:/moodle/_qoder_ord30_evidence_20260920/ord57/restage-kill-evidence.json

Two mutants, chosen for what each one claims:

* `K1` removes only the re-staging after a rolled-back attempt.  That is tonight's defect: the
  retry commits an empty transaction, the door answers 202, and the id it handed out does not
  exist.  If the new gate is real, this mutant must turn it red.
* `K2` removes the re-staging *and* the post-commit durability check - the whole pre-fix shape,
  which proves the two clauses are not each other's cover.

`K3` removes only the durability check.  With re-staging present, the store genuinely holds the
row, so this one is expected to **survive**: the check is a guard against a future lie, not the
mechanism that fixes today's.  Reporting it as a kill would overstate what the gate owns, so the
result is labelled with its expected verdict either way.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path

TREE = Path(r"D:\moodle\_qoder_integration_20260919")
TARGET = TREE / "backend" / "app" / "stay_generation_operations.py"
TEST_FILE = "tests/test_qoder_stay_generation_operations.py"
PYTHON = Path(r"D:\moodle\CityNexus\.venv\Scripts\python.exe")
OUT = Path(r"D:\moodle\_qoder_ord30_evidence_20260920\ord57\restage-kill-evidence.json")

RESTAGE_CALL = "            if restage is not None:\n                restage()\n"
DURABILITY = """    if not durable:
        raise GenerationStoreBusy(
            f"operation {operation_id} reported a commit the store does not hold"
        )
"""
GATE = "test_a_refused_commit_is_re_staged_and_only_then_called_a_202"

MUTANTS = [
    {"name": "K1 no re-staging after a rolled-back attempt (tonight's defect)",
     "expect": "KILLED", "edits": [(RESTAGE_CALL, "            # mutant: nothing re-staged\n")]},
    {"name": "K2 no re-staging and no durability check (the whole pre-fix shape)",
     "expect": "KILLED", "edits": [(RESTAGE_CALL, "            # mutant: nothing re-staged\n"), (DURABILITY, "")]},
    {"name": "K3 durability check removed, re-staging intact (guard alone)",
     "expect": "SURVIVES-BY-DESIGN", "edits": [(DURABILITY, "")]},
]


def run_case() -> tuple[int, str]:
    completed = subprocess.run(
        [str(PYTHON), "-m", "pytest", TEST_FILE, "-q", "--no-header", "-k", GATE,
         "-p", "no:cacheprovider"],
        cwd=TREE / "backend",
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    return completed.returncode, (completed.stdout + completed.stderr)[-4000:]


def main() -> int:
    original = TARGET.read_bytes()
    digest = hashlib.sha256(original).hexdigest()
    text = original.decode("utf-8")
    results = []
    try:
        for mutant in MUTANTS:
            mutated = text
            anchors = [(old, text.count(old)) for old, _new in mutant["edits"]]
            if any(count != 1 for count in (text.count(old) for old, _ in mutant["edits"])):
                results.append({"mutant": mutant["name"], "verdict": "NOT-MEASURED", "anchors": anchors})
                continue
            for old, new in mutant["edits"]:
                mutated = mutated.replace(old, new)
            TARGET.write_bytes(mutated.encode("utf-8"))
            code, tail = run_case()
            failed = GATE in tail and ("1 failed" in tail or "failed" in tail)
            results.append(
                {
                    "mutant": mutant["name"],
                    "expected": mutant["expect"],
                    "suite_exit": code,
                    "gate_red": bool(code != 0),
                    "verdict": "KILLED" if code != 0 else "SURVIVED",
                    "matches_expectation": (mutant["expect"] == "KILLED") == (code != 0),
                    "tail": " | ".join(
                        line for line in tail.splitlines() if "passed" in line or "failed" in line
                    )[-200:],
                }
            )
            TARGET.write_bytes(original)
    finally:
        TARGET.write_bytes(original)

    payload = {
        "restored": hashlib.sha256(TARGET.read_bytes()).hexdigest() == digest,
        "gate": GATE,
        "cases": results,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8", newline="\n")
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    return 0 if payload["restored"] and all(item.get("matches_expectation") for item in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
