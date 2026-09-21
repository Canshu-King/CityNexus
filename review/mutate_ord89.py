"""Kill evidence for ORD-0089: three sabotages, each owned by a specific clause.

Run:  python review/mutate_ord89.py
Writes: D:/moodle/_qoder_ord30_evidence_20260920/ord89/kill-evidence.json

The gates in `tests/test_qoder_beijing_catalogue.py` claim three separate things - that a
catalogue city is plannable by the default path, that its derived schedule respects each
venue's own hours, and that every leg is priced by an explicit fact rather than the fixture's
blanket default.  A green gate that survives the removal of the thing it names is not
evidence, so each clause gets its own mutant.  Both mutated files are restored from raw bytes
and verified by SHA-256 afterwards - never by re-writing text read back, which would flip the
line endings of a file the measuring tool just claimed to leave alone.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path

TREE = Path(r"D:\moodle\_qoder_integration_20260919")
SERVICES = TREE / "backend" / "app" / "services.py"
MATRIX = TREE / "data" / "mock" / "mobility_matrix.json"
TEST_FILE = "tests/test_qoder_beijing_catalogue.py"
PYTHON = Path(r"D:\moodle\CityNexus\.venv\Scripts\python.exe")
OUT = Path(r"D:\moodle\_qoder_ord30_evidence_20260920\ord89\kill-evidence.json")

CATALOGUE_BRANCH = """    if not raw_templates:
        # Derived from this city's own places, with the minutes above subtracted between
        # stops, so the windows handed to the scheduler are ones the gate can honour.
        raw_templates = _catalogue_templates(
            places,
            lambda origin, destination: travel_minutes.get((origin, destination), 0),
        )
"""
FIT_GUARD = """            if end > closed:
                # Dropped, not squeezed: an activity that cannot fit inside its own opening
                # hours is not made honest by moving its minutes around.
                continue
"""

MUTANTS = [
    {
        "name": "M1 default path never derives a schedule (the 422 comes back)",
        "file": SERVICES,
        "old": CATALOGUE_BRANCH,
        "new": "    # mutant: catalogue path disabled\n",
        "gate": "test_a_beijing_journey_gets_at_least_two_candidates_from_the_default_path",
    },
    {
        "name": "M2 the packer stops respecting a venue's closing time",
        "file": SERVICES,
        "old": FIT_GUARD,
        "new": "            # mutant: squeezed in regardless\n",
        # Owned by the packer gate, not the end-to-end one: measured on the real Beijing set
        # no venue is ever over-run, so the end-to-end gate cannot see this mutant at all.
        "gate": "test_the_packer_drops_a_stop_that_cannot_fit_before_its_own_closing_time",
    },
    {
        "name": "M3 one Beijing leg loses its explicit fact and falls back to the default",
        "file": MATRIX,
        "old": '    "place-beijing-tiananmen-square|place-beijing-forbidden-city": 20,\n',
        "new": "",
        "gate": "test_the_beijing_catalogue_is_real_data_and_every_leg_is_priced_explicitly",
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
    originals = {path: path.read_bytes() for path in (SERVICES, MATRIX)}
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
                    "exit": code,
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
