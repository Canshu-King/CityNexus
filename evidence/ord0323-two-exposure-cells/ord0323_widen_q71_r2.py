"""Second half of the Q71 widening: the eight per-leg (T06-T13) arms.

`ord0323_widen_q71.py` covered N1/N2/N3 and the two Q68 arms; the ten-cell legs share their own capture, so
they were still judging textContent only. Same rule as before: counted exact-match edits, no silent no-op.
"""
from __future__ import annotations

import pathlib
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
SPEC = pathlib.Path(r"D:\moodle\_qoder_b_lane_20260923\frontend\e2e\qoder-ord0323-two-exposure-cells.spec.ts")
t = SPEC.read_text(encoding="utf-8")


def rep(old: str, new: str, want: int) -> None:
    global t
    n = t.count(old)
    if n != want:
        raise SystemExit(f"expected {want}, found {n} for:\n{old[:200]}")
    t = t.replace(old, new)


rep(
    """    const found = Object.entries(NEEDLES)
      .filter(([, n]) => dom.root.includes(n) || dom.body.includes(n))
      .map(([c]) => c);
""",
    """    const found = Object.entries(NEEDLES)
      .filter(([, n]) => dom.root.includes(n) || dom.body.includes(n))
      .map(([c]) => c);
    const foundInAttrs = Object.entries(NEEDLES)
      .filter(([, n]) => dom.attrs.includes(n))
      .map(([c]) => c);
""",
    1,
)
rep(
    """      needles_found: found,
""",
    """      needles_found: found,
      needles_found_in_attributes: foundInAttrs,
      attribute_pairs_swept: dom.attr_pairs,
""",
    1,
)
rep(
    """    expect(found, node(arm, `${leg.cell}: a reply's own words are on the screen (${JSON.stringify(found)}); the slot reads "${text}"`)).toEqual([]);
""",
    """    expect(found, node(arm, `${leg.cell}: a reply's own words are on the screen (${JSON.stringify(found)}); the slot reads "${text}"`)).toEqual([]);
    expect(foundInAttrs, node(arm, `${leg.cell}: Q71 counts an attribute as the screen -- a reply's words sit in a data / aria value (${JSON.stringify(foundInAttrs)} of ${String(dom.attr_pairs)} pairs swept)`)).toEqual([]);
""",
    1,
)

if t.count("needles_found_in_attributes") != 1 or t.count("foundInAttrs") != 4:
    raise SystemExit("the leg widening did not land: key="
                     + str(t.count("needles_found_in_attributes")) + " uses=" + str(t.count("foundInAttrs")))
SPEC.write_text(t, encoding="utf-8", newline="\n")
print("T-leg arms now sweep attributes as well")
