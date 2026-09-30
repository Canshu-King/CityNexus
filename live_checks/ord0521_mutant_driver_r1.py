"""ORD-0521 mutation driver: four real defects in the product file, one at a time, restored by hash.

Each mutant is a text edit to `backend/app/demo_scene.py` that makes the shipped door do something a
reader of this order would call a defect - delete rows, invent a city, forget the receipt, open the
guard.  The driver applies one mutant, runs the delivered gate module, and restores the file; the
file's sha256 is read back before and after so "restored" is a measurement rather than a claim.

Run it from `backend/`:

    python ../live_checks/ord0521_mutant_driver_r1.py
"""

from __future__ import annotations

import hashlib
import subprocess
import sys
from pathlib import Path

TARGET = Path("app/demo_scene.py")
GATE = "tests/test_qoder_ord0521_empty_store_scene_door.py"

MUTANTS = [
    (
        "M1-the-door-deletes",
        "    rows = build_demo_fixture_rows()\n    installed: list[str] = []",
        "    rows = build_demo_fixture_rows()\n    session.query(Place).delete()\n    installed: list[str] = []",
        "test_C11_the_door_leaves_rows_it_did_not_create_alone",
    ),
    (
        "M2-an-unsupplied-city-is-answered-as-supplied",
        '    if requested and requested not in supply["supported_city_codes"]:\n        return unsupplyable(',
        '    if False:  # MUTANT M2\n        return unsupplyable(',
        "test_C8_an_unsupplied_destination_says_so_readably_instead_of_inventing",
    ),
    (
        "M3-the-receipt-is-never-read",
        "    row = session.get(IdempotencyKey, scoped_key)",
        "    row = None  # MUTANT M3",
        "test_C9_a_replayed_key_returns_the_first_receipt_and_adds_no_rows",
    ),
    (
        "M4-the-token-guard-fails-open",
        "    if not presented:\n        return (\n            \"SCENE_TOKEN_REQUIRED\",",
        "    if False:  # MUTANT M4\n        return (\n            \"SCENE_TOKEN_REQUIRED\",",
        "test_C4_no_token_is_a_named_refusal_and_writes_nothing",
    ),
    (
        "M5-a-requested-city-is-answered-with-another-citys-trip",
        "        journey = _journey_for_city(session, requested, journey)",
        "        pass  # MUTANT M5: hand back the shipped city and call it the requested one",
        "test_C15_a_supplied_city_without_a_satisfiable_constraint_refuses_by_name",
    ),
    (
        "M6-the-door-advances-whatever-row-is-newest",
        "    journey = session.get(Journey, fixture_id) if fixture_id else None",
        "    journey = None  # MUTANT M6: fall through to 'newest DRAFT' and move another board",
        "test_C16_the_door_advances_its_own_trip_not_the_newest_row",
    ),
]


def sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def run_gate(nodeid: str) -> tuple[int, str]:
    """Run one arm and prove it actually ran.

    A mutant that turns pytest into "no tests ran" is not a killed mutant - it is an empty
    denominator, which is how the first pass of this driver produced four fake reds.
    """

    answer = subprocess.run(
        [sys.executable, "-m", "pytest", nodeid, "-q", "--no-header", "-p", "no:cacheprovider"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    lines = [line.strip() for line in (answer.stdout + answer.stderr).splitlines() if line.strip()]
    summary = " | ".join(lines[-3:])
    if "no tests ran" in summary or "file or directory not found" in summary:
        raise SystemExit(f"ABORT {nodeid}: the arm never ran, so its verdict means nothing: {summary}")
    return answer.returncode, summary


def main() -> int:
    original = TARGET.read_text(encoding="utf-8")
    original_hash = sha256(original)
    print(f"baseline sha256 {original_hash}")
    rc_all, summary = run_gate(GATE)
    print(f"[unmutated] {summary}")
    if rc_all != 0:
        print("ABORT: the gate is not green before any mutant is applied")
        return 2

    reds = 0
    for name, old, new, nodeid in MUTANTS:
        if original.count(old) != 1:
            print(f"ABORT {name}: anchor matched {original.count(old)} times, not 1")
            return 2
        TARGET.write_text(original.replace(old, new, 1), encoding="utf-8", newline="")
        try:
            rc, tail = run_gate(f"{GATE}::{nodeid}")
        finally:
            TARGET.write_text(original, encoding="utf-8", newline="")
        restored = sha256(TARGET.read_text(encoding="utf-8"))
        verdict = "RED as required" if rc != 0 else "SURVIVED - the gate is not load-bearing"
        reds += rc != 0
        print(f"[{name}] {verdict}: {tail} (restored hash matches: {restored == original_hash})")

    print(f"VERDICT: {reds}/{len(MUTANTS)} mutants killed")
    return 0 if reds == len(MUTANTS) else 1


if __name__ == "__main__":
    sys.exit(main())
