"""Widen ORD-0323's e2e instrument to Q71: an attribute is part of the screen.

Every edit here is applied by exact string with a counted assertion, so a drifted spec aborts the patch
instead of producing a silent no-op -- a green gate that measures nothing is worse than a red one.
"""
from __future__ import annotations

import pathlib
import re
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
SPEC = pathlib.Path(r"D:\moodle\_qoder_b_lane_20260923\frontend\e2e\qoder-ord0323-two-exposure-cells.spec.ts")
t = SPEC.read_text(encoding="utf-8")


def rep(old: str, new: str, want: int) -> None:
    global t
    n = t.count(old)
    if n != want:
        raise SystemExit(f"expected {want} occurrence(s), found {n} for:\n{old[:160]}")
    t = t.replace(old, new)


# 1. the DOM capture itself: sweep every data-* / aria-* value alongside the two textContent reads.
rep(
    """async function domReading(page: Page): Promise<{ root: string; body: string; overlay: string[] }> {
  return page.evaluate(() => {
    const root = document.getElementById("root");
    const body = document.body;
    return {
      root: root ? root.textContent ?? "" : "",
      body: body.textContent ?? "",
""",
    """async function domReading(page: Page): Promise<{
  root: string;
  body: string;
  attrs: string;
  attr_pairs: number;
  overlay: string[];
}> {
  return page.evaluate(() => {
    const root = document.getElementById("root");
    const body = document.body;
    /* Q71: data-* / aria-* are part of the screen, and textContent cannot see them, so the prose check
       is run over the attribute values as its own sweep rather than assumed to follow from the text one. */
    const pairs = Array.from(document.querySelectorAll("*")).flatMap((el) =>
      Array.from(el.attributes)
        .filter((a) => a.name.startsWith("data-") || a.name.startsWith("aria-"))
        .map((a) => `${el.tagName.toLowerCase()}|${a.name}|${a.value}`),
    );
    return {
      root: root ? root.textContent ?? "" : "",
      body: body.textContent ?? "",
      attrs: pairs.join("\\n"),
      attr_pairs: pairs.length,
""",
    1,
)

# 2. one attributes-side reading per cell, plus the denominator it was measured against.
for consts, want in (("CELL1_LEAKS", 1), ("CELL2_LEAKS", 2)):
    rep(
        f"    leaked_needles_still_on_screen: {consts}.filter((n) => dom.root.includes(n) || dom.body.includes(n)),\n",
        f"    leaked_needles_still_on_screen: {consts}.filter((n) => dom.root.includes(n) || dom.body.includes(n)),\n"
        f"    leaked_needles_in_attributes: {consts}.filter((n) => dom.attrs.includes(n)),\n"
        "    attribute_pairs_swept: dom.attr_pairs,\n",
        want,
    )

# 3. the negative legs: an attribute hit fails the same arm.
rep(
    """        (readings[arm] as Readings).leaked_needles_still_on_screen,
      )}); the screen reads "${clean(dom.root).slice(0, 240)}"`,
    ),
  ).toEqual([]);
});""",
    """        (readings[arm] as Readings).leaked_needles_still_on_screen,
      )}); the screen reads "${clean(dom.root).slice(0, 240)}"`,
    ),
  ).toEqual([]);
  expect(
    (readings[arm] as Readings).leaked_needles_in_attributes,
    node(
      arm,
      `Q71 counts an attribute as the screen: ${JSON.stringify(
        (readings[arm] as Readings).leaked_needles_in_attributes,
      )} is held in a data / aria attribute value (${String((readings[arm] as Readings).attribute_pairs_swept)} pairs swept)`,
    ),
  ).toEqual([]);
});""",
    1,
)

# N2 and N3 each close their own leak assertion; anchor on each arm's distinct failure message.
for anchor in (
    '`the panel is repeating the reply again (${JSON.stringify((readings[arm] as Readings).leaked_needles_still_on_screen)}); memory reads "${messageText}" and the queue reads "${pendingText}"`,',
    '`the confirmation fold is repeating the reply again (${JSON.stringify((readings[arm] as Readings).leaked_needles_still_on_screen)}); it reads "${detailText}"`,',
):
    old = f"""    {anchor}
    ),
  ).toEqual([]);"""
    if old not in t:
        raise SystemExit("assertion tail drifted: " + anchor[:70])
    new = old.replace(
        "  ).toEqual([]);",
        """  ).toEqual([]);
  expect(
    (readings[arm] as Readings).leaked_needles_in_attributes,
    node(
      arm,
      `Q71 counts an attribute as the screen: ${JSON.stringify(
        (readings[arm] as Readings).leaked_needles_in_attributes,
      )} is held in a data / aria attribute value (${String(
        (readings[arm] as Readings).attribute_pairs_swept,
      )} pairs swept)`,
    ),
  ).toEqual([]);""",
    )
    rep(old, new, 1)

# 4. Q68: the code slot's own attribute is where the truncated sentence landed pre-fix, so the slot is
#    judged in the attribute too -- and Q68a proves the sweep can see a value there at all.
rep(
    """  readings[arm] = {card_text: card, code_in_card: card.includes(Q68_CODE),""",
    """  readings[arm] = {card_text: card, code_in_card: card.includes(Q68_CODE),
                   sweep_sees_the_tested_card: dom.attrs.includes("|data-testid|plan-ai-result"),
                   attribute_pairs_swept: dom.attr_pairs,""",
    1,
)
rep(
    """  expect(card.includes("BLOCKED") || card.includes("服务器回的原因编号"),
    node(arm, `the card no longer names this as a server-coded block (${card.slice(0, 200)})`)).toBe(true);""",
    """  expect(card.includes("BLOCKED") || card.includes("服务器回的原因编号"),
    node(arm, `the card no longer names this as a server-coded block (${card.slice(0, 200)})`)).toBe(true);
  /* The control that keeps the attribute leg from being vacuous: the card under test carries its own
     data-testid, so if the sweep cannot name that pair, every "no sentence in the attributes" reading
     on this page measures nothing. */
  expect(dom.attrs.includes("|data-testid|plan-ai-result"),
    node(arm, `the attribute sweep found ${String(dom.attr_pairs)} pairs but not the tested card among them (${card.slice(0, 160)})`)).toBe(true);""",
    1,
)
rep(
    """    uppercased_prose_in_code_slot: cardWithoutReason.toUpperCase().includes(Q68_PROSE.toUpperCase().slice(0, 18)),""",
    """    uppercased_prose_in_code_slot: cardWithoutReason.toUpperCase().includes(Q68_PROSE.toUpperCase().slice(0, 18)),
    uppercased_prose_in_attributes: dom.attrs.toUpperCase().includes(Q68_PROSE.toUpperCase().slice(0, 18)),
    attribute_pairs_swept: dom.attr_pairs,""",
    1,
)
rep(
    """  expect(
    cardWithoutReason.toUpperCase().includes(Q68_PROSE.toUpperCase().slice(0, 18)),
    node(arm, `the 原因编号 slot is showing the reply's sentence again (${cardWithoutReason.slice(0, 220)})`),
  ).toBe(false);""",
    """  expect(
    cardWithoutReason.toUpperCase().includes(Q68_PROSE.toUpperCase().slice(0, 18)),
    node(arm, `the 原因编号 slot is showing the reply's sentence again (${cardWithoutReason.slice(0, 220)})`),
  ).toBe(false);
  expect(
    dom.attrs.toUpperCase().includes(Q68_PROSE.toUpperCase().slice(0, 18)),
    node(arm, `Q71: the sentence is in a data / aria attribute value (${String((readings[arm] as Readings).attribute_pairs_swept)} pairs swept) even though the visible slot is clean`),
  ).toBe(false);""",
    1,
)

if t.count("leaked_needles_in_attributes") < 3 or "attr_pairs: pairs.length" not in t:
    raise SystemExit("the widening did not land where it had to")
SPEC.write_text(t, encoding="utf-8", newline="\n")
print("spec widened:", len(re.findall(r"leaked_needles_in_attributes", t)), "attribute legs added,",
      t.count("attribute_pairs_swept"), "denominator readings")
