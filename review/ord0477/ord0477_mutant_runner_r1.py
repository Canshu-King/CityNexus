"""ORD-0477 mutant runner -- one mutation at a time, reverted before the report is written.

Why a runner instead of hand-editing: the mutation has to be gone when the next reading is taken, and
"gone" is judged on the file's own bytes (`sha256` before == after), not on my belief that I pasted it
back.  Each mutant names the assertion it is supposed to redden; a mutant that leaves the gate green is
reported as a dead assertion, which is the finding the order asked for rather than a passing number.

usage: python ord0477_mutant_r1.py <mutant> <command...>
"""
from __future__ import annotations

import hashlib
import pathlib
import subprocess
import sys

TREE = pathlib.Path(r"D:/moodle/_qoder_b_ord0417_20260928/ord0477")
RUN = pathlib.Path(r"D:/moodle/_qoder_b_ord0417_20260928/run")

MUTANTS = {
    # the door stops refusing an unknown word and answers its own default order instead -- the exact
    # silent-default shape ORD-0477 forbids, and the one a client cannot tell apart from a real list
    "silent_default_on_unknown_word": (
        "backend/app/main.py",
        "    if sort not in JOURNEY_SORT_TIERS:\n",
        "    if sort not in JOURNEY_SORT_TIERS:\n"
        "        return [journey_schema(item) for item in session.scalars(\n"
        "            live.order_by(Journey.created_at, Journey.id)\n"
        "        ).all()]\n"
        "    if False:\n",
    ),
    # a tier orders characters instead of instants: +08:00 and Z rows are compared as strings
    "characters_not_instants": (
        "backend/app/main.py",
        '    "DEPARTURE_DATE": (lambda row: _journey_instant(row.start_at), False),\n',
        '    "DEPARTURE_DATE": (lambda row: row.start_at, False),\n',
    ),
    # the name tier loses its case-fold, so `Zoo camp` reads as coming before `apple market`
    "no_case_fold": (
        "backend/app/main.py",
        '    "TITLE": (lambda row: row.title.casefold(), False),\n',
        '    "TITLE": (lambda row: row.title, False),\n',
    ),
    # the screen stops sending the word: the door is asked the same way whatever tier is picked
    "screen_stops_asking": (
        "frontend/src/features/access/accessDoors.ts",
        "  return request<JourneySummary[]>(journeyListPath(sort));",
        "  return request<JourneySummary[]>(JOURNEY_LIST_PATH);",
    ),
}


def digest(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    if len(sys.argv) < 3 or sys.argv[1] not in MUTANTS:
        print("usage: ord0477_mutant_r1.py <%s> <command...>" % "|".join(MUTANTS))
        return 2
    name = sys.argv[1]
    command = sys.argv[2:]
    relative, old, new = MUTANTS[name]
    target = TREE / relative
    original = target.read_text(encoding="utf-8")
    before = digest(target)
    if original.count(old) != 1:
        print(f"REFUSE: {old[:40]!r} occurs {original.count(old)} times in {relative}")
        return 3
    target.write_text(original.replace(old, new, 1), encoding="utf-8", newline="\n")
    print(f"MUTATED {relative} sha_before={before[:12]} -> sha_now={digest(target)[:12]}")
    try:
        completed = subprocess.run(command, cwd=str(TREE), capture_output=True, text=True, encoding="utf-8", errors="replace")
    finally:
        target.write_text(original, encoding="utf-8", newline="\n")
    reverted = digest(target) == before
    out = (completed.stdout or "") + ("\n" + completed.stderr if completed.stderr else "")
    log = RUN / f"ord0477_mutant_{name}.txt"
    log.write_text(
        "mutant=%s rc=%s reverted=%s sha_before=%s sha_after_revert=%s\ncommand=%s\n\n%s\n"
        % (name, completed.returncode, reverted, before, digest(target), " ".join(command), out[-12000:]),
        encoding="utf-8",
    )
    tail = [line for line in out.splitlines() if " passed" in line or " failed" in line or "failed," in line or "Error" in line][-6:]
    sys.stdout.buffer.write(
        ("MUTANT=%s RC=%s REVERTED=%s LOG=%s\n%s\n" % (name, completed.returncode, reverted, log, chr(10).join(tail))).encode(
            "utf-8", "replace"
        )
    )
    return 0 if (completed.returncode != 0 and reverted) else 4


if __name__ == "__main__":
    sys.exit(main())
