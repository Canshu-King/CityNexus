"""ORD-0518 mutant runner r1 -- the order's two反件, each applied to one product line and reverted.

Why a runner and not a hand edit: the mutation has to be *gone* before the next reading is taken, and
"gone" is judged on the file's bytes (sha256 before == after), not on my belief that I pasted it back.
Each mutant names the arms it must redden; a mutant that leaves them green is reported as a dead
assertion, which is the finding the order asked for rather than a passing number.

The two the order names:

* `server_order_masked` -- the door's answer is turned upside down between the door and the screen.
  This is the shape the whole order exists for: the traveller is shown a list whose real order nobody
  vouched for.  `order-verified` must stop saying "checked row by row" and `order-rows-named` must see
  the rows move, so both families have to go red.
* `tier_switch_keeps_the_list_still` -- the screen asks the door the same way whatever the traveller
  picks.  `order-rows-named` pins the first and last trip per order, so if switching does not swap the
  ends, that arm has to go red.

usage: python ord0518_mutant_r1.py <mutant> <command...>
"""
from __future__ import annotations

import hashlib
import os
import pathlib
import subprocess
import sys

TREE = pathlib.Path(
    os.environ.get("ORD0518_TREE") or r"D:/moodle/_qoder_b_ord0417_20260928/ord0477cut_be0ffee2"
)
RUN = pathlib.Path(r"D:/moodle/_qoder_b_ord0417_20260928/run")

# the arms each mutant is required to redden, as substrings of the playwright report line
EXPECTED = {
    "server_order_masked": ["order-verified-zh", "order-rows-named-zh"],
    "tier_switch_keeps_the_list_still": ["order-rows-named-zh", "order-verified-zh"],
    # not one of the two the order names: the arms it exists to test are the "不得假装按时间排" ones
    "verdict_stops_reading_the_rows": ["order-verified-zh"],
}

MUTANTS = {
    # what the door answered is no longer what the screen shows: the rows arrive in the opposite order
    "server_order_masked": (
        "frontend/src/features/access/accessDoors.ts",
        "  return request<JourneySummary[]>(journeyListPath(choice));",
        "  return request<JourneySummary[]>(journeyListPath(choice)).then((rows) => rows.slice().reverse());",
    ),
    # the word the traveller pressed never reaches the door: every order asks the same question
    "tier_switch_keeps_the_list_still": (
        "frontend/src/features/access/accessDoors.ts",
        "  return choice === null ? JOURNEY_LIST_PATH : `${JOURNEY_LIST_PATH}?sort=${encodeURIComponent(choice)}`;",
        "  return JOURNEY_LIST_PATH;",
    ),
    # the screen says "checked" for an order whose rows it never looked at -- the claim this order
    # exists to forbid, and the one the two commanded mutants cannot reach (they leave the verdict
    # reading the rows, which is why they redden it rather than silencing it)
    "verdict_stops_reading_the_rows": (
        "frontend/src/features/access/journeyOrderVerdict.ts",
        "  if (tier === null || ORDERS_THIS_SCREEN_CANNOT_VERIFY.includes(tier)) {",
        "  if (false && (tier === null || ORDERS_THIS_SCREEN_CANNOT_VERIFY.includes(tier))) {",
    ),
}


def digest(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def failed_names(text: str) -> list[str]:
    out = []
    for line in text.splitlines():
        if "›" in line and ("spec.ts" in line) and ("failed" in line or "Error:" in line):
            out.append(line.strip())
        if line.strip().endswith("failed") or " failed" in line:
            out.append(line.strip())
    return out


def main() -> int:
    if len(sys.argv) < 3 or sys.argv[1] not in MUTANTS:
        print("usage: ord0518_mutant_r1.py <%s> <command...>" % "|".join(MUTANTS))
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
    mutated = digest(target)
    print(f"MUTATED {relative} sha_before={before[:16]} sha_mutated={mutated[:16]}")
    try:
        completed = subprocess.run(
            command, cwd=str(TREE / "frontend"), capture_output=True, text=True, encoding="utf-8", errors="replace"
        )
    finally:
        target.write_text(original, encoding="utf-8", newline="\n")
    reverted = digest(target) == before
    out = (completed.stdout or "") + ("\n" + completed.stderr if completed.stderr else "")
    reddened = [arm for arm in EXPECTED[name] if arm in out]
    missed = [arm for arm in EXPECTED[name] if arm not in reddened]
    log = RUN / f"ord0518_mutant_{name}_r1.txt"
    log.write_text(
        "mutant=%s rc=%s reverted=%s sha_before=%s sha_after_revert=%s\n"
        "expected_red=%s reddened=%s missed=%s\ncommand=%s\n\n%s\n"
        % (
            name,
            completed.returncode,
            reverted,
            before,
            digest(target),
            EXPECTED[name],
            reddened,
            missed,
            " ".join(command),
            out[-40000:],
        ),
        encoding="utf-8",
    )
    summary = [line for line in out.splitlines() if " failed" in line or " passed" in line or "Error:" in line][:40]
    tail = "\n".join(
        line for line in out.splitlines() if line.strip().startswith("[chromium]") or " failed" in line or " passed" in line
    )
    sys.stdout.buffer.write(
        (
            "MUTANT=%s RC=%s REVERTED=%s REDDENED=%s MISSED=%s LOG=%s\n%s\n--- lines ---\n%s\n"
            % (name, completed.returncode, reverted, reddened, missed, log, tail, "\n".join(summary))
        ).encode("utf-8", "replace")
    )
    return 0 if (completed.returncode != 0 and reverted and not missed) else 4


if __name__ == "__main__":
    sys.exit(main())
