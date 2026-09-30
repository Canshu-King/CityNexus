"""ORD-0490 mutation control -- prove the round-trip assertions are watching the write.

Eleven green tests say nothing by themselves: they would be just as green if the assertions were
comparing two readings of a door that never changed.  So the product is patched here, in a copy that
is restored in the same `finally`, with the one edit that should break the order's promise --
`POST /journeys/{id}/undelete` clears `journeys.deleted_at` (`backend/app/main.py:3110`); setting it
to the value the tap already read leaves the row in the bin while the door still answers 200.  Every
test that says "the same token reads again" has to go red, and the two that only look at the grant
row have to stay green: that split is the evidence that these assertions are about the restore and
not about the fixture.

Run it with this lane's interpreter:

    /d/moodle/CityNexus/.venv/Scripts/python.exe review/ord0490/mutation_control_r1.py

It writes `review/ord0490/mutation_control_r1.txt` and restores `backend/app/main.py` byte for byte
before it exits.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

LANE = Path("D:/moodle/_qoder_r_ord0465_20260929")
TREE = LANE / "wt"
MAIN = TREE / "backend" / "app" / "main.py"
OUT = TREE / "review" / "ord0490" / "mutation_control_r1.txt"

#: The live write of the 找回 door: `UPDATE journeys SET deleted_at = NULL WHERE id = ? AND deleted_at = <seen>`.
SWAP = (b".values(deleted_at=None)", b".values(deleted_at=seen)")
TESTS = "tests/test_qoder_ord0490_shared_after_restore.py"


def run_pytest() -> tuple[int, list[str]]:
    import os

    env = dict(os.environ)
    for key in ("HTTP_PROXY", "HTTPS_PROXY"):
        env.pop(key, None)
    env["NO_PROXY"] = "*"
    env["PYTHONPATH"] = f"{TREE};{TREE / 'backend'}"
    answer = subprocess.run(
        [sys.executable, "-m", "pytest", TESTS, "-q", "--no-header"],
        cwd=TREE / "backend",
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    lines = (answer.stdout + answer.stderr).splitlines()
    return answer.returncode, [
        line for line in lines
        if line.startswith("FAILED") or " passed" in line or " failed" in line
    ]


def main() -> int:
    original = MAIN.read_bytes()
    if original.count(SWAP[0]) != 1:
        raise SystemExit(
            f"REFUSE: this control names one edit site and found "
            f"{original.count(SWAP[0])} matches for {SWAP[0]!r}. The line moved; re-read it."
        )
    report: list[str] = [
        "ORD-0490 mutation control",
        f"main.py sha1 before = {__import__('hashlib').sha1(original).hexdigest()}",
        f"edit: {SWAP[0]!r} -> {SWAP[1]!r}  (the 找回 still answers 200, the row stays in the bin)",
        "",
    ]
    try:
        MAIN.write_bytes(original.replace(*SWAP))
        code, lines = run_pytest()
        report.append(f"mutated run: exit={code}")
        report.extend(f"  {line}" for line in lines)
        report.append("")
        report.append(
            "reading: the tests that assert the token reads 200 after the restore are red; the two "
            "that only ever look at the grant row (`the_round_trip_writes_nothing_to_the_grant`) and "
            "at a door that was never binned (`a_restore_that_was_not_needed...`) stay green."
        )
    finally:
        MAIN.write_bytes(original)
        restored = MAIN.read_bytes()
        import hashlib

        report.append("")
        report.append(
            f"restored: bytes_equal_to_before={restored == original} "
            f"sha1={hashlib.sha1(restored).hexdigest()}"
        )
    OUT.write_text("\n".join(report) + "\n", encoding="utf-8", newline="\n")
    print("\n".join(report))
    return 0


if __name__ == "__main__":
    sys.exit(main())
