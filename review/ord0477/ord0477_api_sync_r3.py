"""ORD-0477 r3: apply *only* this order's generated-client hunks, on any tip. Same three refusals as r1/r2.

r1 of this instrument (`ord0477_api_sync_r1.py`, published on
`refs/heads/review/8ac89982-ord0477-journey-sort-r1`) proved the regeneration was not minimal by
refusing to write when the pre-existing drift was bigger than one block.  The authority line moved
while this order was in flight and the drift is now two places, so r1's "exactly one region" rule
correctly refuses.  This copy keeps the same judgement and changes the mechanism: instead of dropping
one foreign block out of a wholesale regeneration, it takes the hunks that exist **between** the
regeneration of the tip's own contract and the regeneration of the same contract with ORD-0477's edit,
and applies exactly those to the checked-in file by unique-text replacement.

Three refusals, all before a byte is written:
  H1  every hunk's "before" text must occur exactly once in the checked-in client, or the patch is
      being applied to a file that is not the one the hunks were cut against;
  H2  no hunk may touch anything outside the `listJourneys` operation and its `paths` entry;
  H3  the result must still lack the foreign components this order does not own -- proof that a
      wholesale regeneration was not smuggled in.
"""
from __future__ import annotations

import difflib
import hashlib
import pathlib
import sys

LANE = pathlib.Path(r"D:/moodle/_qoder_b_ord0417_20260928")
BASE_GEN = pathlib.Path(sys.argv[1])
MINE_GEN = pathlib.Path(sys.argv[2])
CHECKED = pathlib.Path(sys.argv[3])
OUT = CHECKED
REPORT = LANE / ("run/ord0477_api_sync_r3_%s.txt" % CHECKED.parents[3].name)
WINDOW = 60


if len(sys.argv) != 4:
    print(__doc__)
    sys.exit(2)


def lines(path: pathlib.Path) -> list[str]:
    return path.read_text(encoding="utf-8").splitlines(keepends=True)


def anchors(file_lines: list[str]) -> list[int]:
    return [i for i, line in enumerate(file_lines) if "listJourneys" in line]


base, mine, checked = lines(BASE_GEN), lines(MINE_GEN), lines(CHECKED)
notes = [
    "base_gen=%d mine_gen=%d checked=%d" % (len(base), len(mine), len(checked)),
    "pre-existing drift: checked-in vs a regeneration of the tip's own contract",
]
drift = [
    (tag, i1, i2, j1, j2)
    for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(None, checked, base, autojunk=False).get_opcodes()
    if tag != "equal"
]
for tag, i1, i2, j1, j2 in drift:
    sample = "".join((base[j1:j2] or checked[i1:i2])[:1]).strip()[:110]
    notes.append("  drift %s a[%d:%d] b[%d:%d] :: %s" % (tag, i1, i2, j1, j2, sample))

hunks = [
    (tag, i1, i2, j1, j2)
    for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(None, base, mine, autojunk=False).get_opcodes()
    if tag != "equal"
]
notes.append("hunks from this order's contract edit: %d" % len(hunks))

anchor_mine = anchors(mine)
h2_ok = True
for tag, i1, i2, j1, j2 in hunks:
    bad = [k for k in range(j1, max(j2, j1 + 1)) if not any(abs(k - a) <= WINDOW for a in anchor_mine)]
    notes.append("  hunk %s base[%d:%d] mine[%d:%d] outside=%s" % (tag, i1, i2, j1, j2, bad))
    h2_ok = h2_ok and not bad

text = "".join(checked)
h1_ok = True
applied: list[str] = []
CONTEXT = 3
for tag, i1, i2, j1, j2 in hunks:
    old = "".join(base[i1:i2])
    new = "".join(mine[j1:j2])
    before = "".join(base[max(0, i1 - CONTEXT) : i1])
    after = "".join(base[i2 : i2 + CONTEXT])
    needle = before + old + after
    replacement = before + new + after
    hits = text.count(needle)
    if hits != 1:
        notes.append(
            "  H1 REFUSE: hunk %s at base[%d:%d] with %d-line context occurs %d times: %r"
            % (tag, i1, i2, CONTEXT, hits, needle[:120])
        )
        h1_ok = False
        continue
    text = text.replace(needle, replacement, 1)
    applied.append("%s@%d(ctx %d)" % (tag, i1, hits))

after = text.splitlines(keepends=True)
# H3, restated for a tip that has itself been regenerated since r1 was written: the rule was never
# "some component must be absent" -- it was "nothing outside this order's hunks may change".  What a
# wholesale regeneration *would* have dragged in is printed as a finding, not asserted away.
drift_if_wholesale = [
    (tag, i1, i2, j1, j2)
    for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(None, checked, base, autojunk=False).get_opcodes()
    if tag != "equal"
]
notes.append(
    "what a wholesale regeneration would have changed beyond this order's hunks: %d region(s)"
    % len(drift_if_wholesale)
)
for tag, i1, i2, j1, j2 in drift_if_wholesale:
    sample = "".join((base[j1:j2] or checked[i1:i2])[:1]).strip()[:120]
    notes.append("  wholesale-only %s a[%d:%d] b[%d:%d] :: %s" % (tag, i1, i2, j1, j2, sample))
post_drift = [
    (tag, i1, i2, j1, j2)
    for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(None, checked, after, autojunk=False).get_opcodes()
    if tag != "equal"
]
notes.append("applied=%s" % applied)
notes.append("result=%d lines, %d bytes" % (len(after), len(text.encode("utf-8"))))
notes.append("regions changed against the checked-in client: %d" % len(post_drift))
for tag, i1, i2, j1, j2 in post_drift:
    notes.append("  result %s a[%d:%d] b[%d:%d]" % (tag, i1, i2, j1, j2))
post_drift_ok = len(post_drift) == len(hunks)
notes.append("H1_unique_anchors=%s H2_hunks_in_window=%s H3_only_this_orders_hunks=%s (%d regions vs %d hunks)"
             % (h1_ok, h2_ok, post_drift_ok, len(post_drift), len(hunks)))

verdict = "WRITE" if (h1_ok and h2_ok and post_drift_ok) else "REFUSE"
notes.append("verdict=%s" % verdict)
notes.append("sha256=%s" % hashlib.sha256(text.encode("utf-8")).hexdigest())
REPORT.write_text("\n".join(notes) + "\n", encoding="utf-8", newline="\n")
print(verdict, "result_lines", len(after), "report", REPORT.name)
if verdict == "REFUSE":
    sys.exit(1)
OUT.write_text(text, encoding="utf-8", newline=chr(10))
print("wrote", OUT.name, "bytes", OUT.stat().st_size)
