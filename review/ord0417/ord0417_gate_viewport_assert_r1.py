"""ORD-0417 lane: put the viewport assertion back into the hub gate that is on the line.

What happened, in one sentence: the landing took the 20-file commit (`408fce7174bd334f6086f361fafce57d2c89e9ff`)
but not the follow-up (`ae639db989ae562b475e5a6ff8cb77cc6995c2ab`) that added the assertion, so the
shipped gate is v1 -- it checks the naming element's computed style and its panel ancestry and passes
while the sentence is painted at y=854 on a 844 px viewport.  That is the same over-claim this lane
already reported once, so this instrument re-applies exactly that delta to whatever copy of the spec
is on the line, by anchor, and refuses if the anchors are not unique.

Two edits, nothing else: the cell probe gains `inside_viewport` / `inner_h`, and `hub-not-aria` gains
the assertion that uses them.

usage: python ord0417_gate_viewport_assert_r1.py <path to hub spec> [--check-only]
"""
import sys

PATH = sys.argv[1]
CHECK_ONLY = "--check-only" in sys.argv

EDITS = [
    (
        """        inside_panel: !!el.closest(".v8-map-panel"),""",
        """        inside_panel: !!el.closest(".v8-map-panel"),
        inside_viewport: r.top >= 0 && r.bottom <= window.innerHeight,
        inner_h: window.innerHeight,""",
    ),
    (
        """    expect(cell.inside_panel, node("H2", `${arm.locale}: the name is painted outside the map panel: ${JSON.stringify(cell)}`)).toBe(true);""",
        """    expect(cell.inside_panel, node("H2", `${arm.locale}: the name is painted outside the map panel: ${JSON.stringify(cell)}`)).toBe(true);
    /* The whole point of this order is a name the traveller READS.  On the hub the caption sits at the
       bottom of a panel that starts below the fold, so "visible" in the computed-style sense is not
       enough: the box has to be inside the viewport the finger is looking at.  Asserting this is what
       caught that the sentence was painted at y=854 on a 844 px viewport. */
    expect(cell.inside_viewport, node("H2", `${arm.locale}: the name is painted but below the fold — box ${JSON.stringify(cell.box)} in a ${cell.inner_h} px viewport: ${JSON.stringify(cell)}`)).toBe(true);""",
    ),
]

src = open(PATH, encoding="utf-8").read()
if "inside_viewport" in src:
    raise SystemExit("REFUSE: this copy already carries the viewport assertion -- nothing to do")
out = src
for old, new in EDITS:
    n = out.count(old)
    if n != 1:
        raise SystemExit(f"REFUSE: anchor matched {n} times, expected exactly 1: {old[:60]!r}")
    out = out.replace(old, new, 1)

print(f"anchors unique x{len(EDITS)}; delta {len(out) - len(src)} bytes; "
      f"inside_viewport hits now {out.count('inside_viewport')}")
if CHECK_ONLY:
    print("check-only: nothing written")
else:
    open(PATH, "w", encoding="utf-8", newline=chr(10)).write(out)
    print("patched", PATH)
