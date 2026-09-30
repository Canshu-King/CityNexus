"""ORD-0505 - three counter-examples, one per named refusal.

Each mutant removes exactly one guard from `abort_journey` and nothing else, then runs only the arm
that is supposed to notice.  A mutant is believed only after it is shown to have landed (the guard's
condition is replaced, the original text is gone), and every run is followed by a byte-for-byte
restore checked by sha1 -- a tree left mutated would make the next reading meaningless.

Run against the working tree; restores from the backups taken at the start.
"""

from __future__ import annotations

import hashlib
import subprocess
import sys
from pathlib import Path

# The tree whose bytes are being measured is the tree this instrument sits in.  A hard-coded lane
# path here would mutate some other checkout and still print "killed".
BACKEND = Path(__file__).resolve().parents[2] / "backend"
MAIN = BACKEND / "app" / "main.py"
PY = sys.executable

GUARDS = {
    "MA_no_authorisation": (
        "        if journey.traveler_id != str(payload.requested_by):\n",
        "        if False:  # MUTANT MA: the authorisation guard is gone\n",
        "test_ord0505_three_refusals_each_answer_with_their_own_name",
    ),
    "MB_no_already_cancelled": (
        '        if seen == "CANCELLED":\n',
        "        if False:  # MUTANT MB: the stopped-already guard is gone\n",
        "test_ord0505_three_refusals_each_answer_with_their_own_name",
    ),
    "MC_no_missing_trip": (
        "    for _ in range(_JOURNEY_ABORT_ATTEMPTS):\n"
        "        journey = session.get(Journey, str(journey_id))\n"
        "        if journey is None:\n",
        "    for _ in range(_JOURNEY_ABORT_ATTEMPTS):\n"
        "        journey = session.get(Journey, str(journey_id))\n"
        "        if False:  # MUTANT MC: the not-found guard is gone\n",
        "test_ord0505_three_refusals_each_answer_with_their_own_name",
    ),
    "MD_no_live_refusal": (
        '    if journey.status == "CANCELLED":\n',
        "    if False:  # MUTANT MD: the live-door guard is gone\n",
        "test_ord0505_live_door_refuses_an_aborted_trip_by_name",
    ),
}


def sha(path: Path) -> str:
    return hashlib.sha1(path.read_bytes()).hexdigest()


def run(test: str) -> tuple[int, str]:
    proc = subprocess.run(
        [PY, "-m", "pytest", f"tests/test_qoder_ord0505_journey_abort.py::{test}",
         "-p", "no:cacheprovider", "-q", "--tb=line"],
        cwd=str(BACKEND), capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    out = proc.stdout + proc.stderr
    tail = [line for line in out.splitlines() if " passed" in line or " failed" in line
            or " error" in line]
    return proc.returncode, (tail[-1].strip() if tail else out[-160:])


original = sha(MAIN)
print(f"main.py sha1 before any mutation: {original}")
backup = MAIN.with_suffix(".py.bak0505")
backup.write_bytes(MAIN.read_bytes())
results: list[tuple[str, str, int, str]] = []
try:
    for name, (old, new, test) in GUARDS.items():
        text = backup.read_text(encoding="utf-8")
        count = text.count(old)
        if count != 1:
            print(f"{name}: anchor appears {count} times, skipped as unusable")
            results.append((name, "ANCHOR-NOT-UNIQUE", 9, ""))
            continue
        mutated = text.replace(old, new)
        assert new in mutated and old not in mutated, f"{name}: mutation did not land"
        MAIN.write_text(mutated, encoding="utf-8", newline="")
        assert sha(MAIN) != original, f"{name}: bytes unchanged"
        code, summary = run(test)
        print(f"{name}: landed; arm says -> {summary}")
        results.append((name, "LANDED", code, summary))
finally:
    MAIN.write_bytes(backup.read_bytes())
    print(f"restored sha1 == original: {sha(MAIN) == original}")
    code, summary = run("test_ord0505_abort_stores_the_why_and_reads_it_back_off_the_server")
    print(f"after restore, the success arm says -> {summary}")
    backup.unlink(missing_ok=True)

print("\nverdict:")
for name, landed, code, summary in results:
    print(f"  {name:26s} exit={code} :: {summary}")
