"""ORD-0477 r3: the反件, re-run on the rebased generation, one mutation at a time, reverted by bytes.

r1 of this instrument (`review/ord0477/ord0477_mutant_runner_r1.py`, published on the r2 ref) stayed
where it is: the readings it produced belong to the generation it ran on. This copy exists because the
authority line moved 103 commits (ORD-0503, ORD-0527 and ORD-0532 all landed under this order), so the
question "does each arm still bite?" has to be asked of *this* tree again rather than quoted from the
old one. Same judgement as r1: every mutant names the arms it must redden, the file's sha256 is taken
before and after, and a mutation that leaves the named arms green is reported as a dead assertion --
which is a finding, not a pass.

Two additions over r1:

* `pin_pre_tier_segment_swapped_in` -- ORD-0402's byte pin on this door. ORD-0532 converted
  `main.py` to LF, which is exactly the event a byte pin is supposed to notice, so whether the arm
  still bites on the LF generation is measured here, not assumed.
* `TREE` comes from the environment, because a candidate is no longer one directory.

usage: python ord0477_mutant_r2.py <mutant> <command...>
"""
from __future__ import annotations

import hashlib
import json
import os
import pathlib
import subprocess
import sys

LANE = pathlib.Path(r"D:/moodle/_qoder_b_ord0417_20260928")
TREE = pathlib.Path(os.environ.get("ORD0477_TREE") or (LANE / "ord0477cut_7862c6de"))
RUN = LANE / "run"
NL = chr(10)

START = '@app.get(' + NL + '    "/api/v1/journeys",' + NL + '    response_model=list[JourneySchema],'
END = '@app.delete("/api/v1/journeys/{journey_id}", status_code=204)'

MUTANTS = {
    # the door stops refusing an unknown word and answers its own default order instead
    "silent_default_on_unknown_word": (
        "backend/app/main.py",
        "    if sort not in JOURNEY_SORT_TIERS:" + NL,
        "    if sort not in JOURNEY_SORT_TIERS:" + NL
        + "        return [journey_schema(item) for item in session.scalars(" + NL
        + "            live.order_by(Journey.created_at, Journey.id)" + NL
        + "        ).all()]" + NL
        + "    if False:" + NL,
    ),
    # a tier orders characters instead of instants
    "characters_not_instants": (
        "backend/app/main.py",
        '    "DEPARTURE_DATE": (lambda row: _journey_instant(row.start_at), False),' + NL,
        '    "DEPARTURE_DATE": (lambda row: row.start_at, False),' + NL,
    ),
    # the name tier loses its case-fold
    "no_case_fold": (
        "backend/app/main.py",
        '    "TITLE": (lambda row: row.title.casefold(), False),' + NL,
        '    "TITLE": (lambda row: row.title, False),' + NL,
    ),
    # the screen stops sending the word
    "screen_stops_asking": (
        "frontend/src/features/access/accessDoors.ts",
        "  return request<JourneySummary[]>(journeyListPath(sort));",
        "  return request<JourneySummary[]>(JOURNEY_LIST_PATH);",
    ),
}

# which arms each mutant must redden, as the substrings that name them in the report. These are read
# off the arm names in the two test files and the spec, not written from memory: an expected string
# that matches nothing would silently turn a dead assertion into a "missed" finding of the wrong kind.
#
# ORD-0402's byte pin is in every backend set below, measured rather than assumed: editing any byte
# inside the door's segment moves those bytes, so the pin arm reddens under all three -- which is the
# proof the freeze gate is wired to the door and not to a number.
PIN = "was_not_touched_down_to_its_bytes"
EXPECTED = {
    "silent_default_on_unknown_word": [
        "an_unknown_word_is_refused_by_name",
        "an_empty_sort_word_is_a_sent_word",
        "a_tier_word_is_not_case_insensitive",
        PIN,
    ],
    "characters_not_instants": ["orders_by_instant_not_by_characters", PIN],
    "no_case_fold": ["case_folded_code_point_order", PIN],
    "screen_stops_asking": ["sort-reorders-zh", "sort-asked-by-word-zh"],
    "pin_pre_tier_segment_swapped_in": [PIN],
}


def digest(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def pin_swap(tree: pathlib.Path) -> tuple[str, str, str]:
    """(relative, old, new) for the byte-pin mutant: the pre-tier segment put back over the door."""
    r2 = tree / "review/ord0402-readouts/LIST_DOOR_BASELINE_r2.json"
    r3 = tree / "review/ord0402-readouts/LIST_DOOR_BASELINE_r3.json"
    source = (tree / "backend/app/main.py").read_text(encoding="utf-8")
    pre_tier = json.loads(r2.read_text(encoding="utf-8"))["segment_lf"]
    post_tier = json.loads(r3.read_text(encoding="utf-8"))["segment_lf"]
    start, end = source.index(START), source.index(END)
    current = source[start:end]
    if current != post_tier:
        raise SystemExit(
            "REFUSE: the tree's door segment is not what LIST_DOOR_BASELINE_r3 recorded "
            "(%d bytes here vs %d recorded)" % (len(current), len(post_tier))
        )
    return "backend/app/main.py", current, pre_tier


def main() -> int:
    if len(sys.argv) < 3:
        print("usage: ord0477_mutant_r2.py <%s> <command...>" % "|".join(list(MUTANTS) + ["pin_pre_tier_segment_swapped_in"]))
        return 2
    name = sys.argv[1]
    command = sys.argv[2:]
    if name == "pin_pre_tier_segment_swapped_in":
        relative, old, new = pin_swap(TREE)
    elif name in MUTANTS:
        relative, old, new = MUTANTS[name]
    else:
        print("unknown mutant")
        return 2
    target = TREE / relative
    original = target.read_text(encoding="utf-8")
    before = digest(target)
    if original.count(old) != 1:
        print("REFUSE: %r occurs %d times in %s" % (old[:60], original.count(old), relative))
        return 3
    target.write_text(original.replace(old, new, 1), encoding="utf-8", newline=NL)
    mutated = digest(target)
    try:
        # cwd is the tree, not the tree's `backend`: the commands below name paths from the tree root
        # (`backend/tests/...`), and a wrong cwd makes every arm "not found", which reads as a red
        completed = subprocess.run(
            command,
            cwd=str(TREE),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            env=dict(os.environ, PYTHONPATH=str(TREE / "backend")),
        )
    finally:
        target.write_text(original, encoding="utf-8", newline=NL)
    reverted = digest(target) == before
    out = (completed.stdout or "") + (NL + completed.stderr if completed.stderr else "")
    reddened = [arm for arm in EXPECTED[name] if arm in out]
    missed = [arm for arm in EXPECTED[name] if arm not in reddened]
    log = RUN / ("ord0477_mutant_r2_%s.txt" % name)
    log.write_text(
        "mutant=%s tree=%s rc=%s reverted=%s sha_before=%s sha_mutated=%s sha_after_revert=%s" % (
            name, TREE.name, completed.returncode, reverted, before, mutated, digest(target))
        + NL + "expected_red=%s reddened=%s missed=%s" % (EXPECTED[name], reddened, missed)
        + NL + "command=%s" % " ".join(command)
        + NL + NL + out[-40000:] + NL,
        encoding="utf-8",
    )
    tail = NL.join(line for line in out.splitlines() if " failed" in line or " passed" in line or "Error" in line)[:4000]
    # named slots, not positional: a `%`-tuple of mine once printed a reading with one slot short, and
    # a mis-ordered number in a report is worse than no number
    sys.stdout.buffer.write(
        (
            "MUTANT={name} RC={rc} REVERTED={reverted} REDDENED={reddened} MISSED={missed} LOG={log}"
            .format(name=name, rc=completed.returncode, reverted=reverted, reddened=reddened, missed=missed, log=log)
            + NL
            + tail
        ).encode("utf-8", "replace")
    )
    return 0 if (completed.returncode != 0 and reverted and not missed) else 4


if __name__ == "__main__":
    sys.exit(main())
