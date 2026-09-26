"""ORD-0323 Q68 amendment: the two-way legs the commander's 04:14 ruling actually names.

Gap found by reading his order against the spec, not against the product: at candidate 499522db the product
already satisfies ①②③ (`serverReasonCode` answers only for a machine key, the `（没给编号）` branch is intact,
`serverReasonSentence` is byte-identical to the ordered baseline). What was missing is the proof:

  A  he exercises `{"error":{"code":...}}`; my arm only ever sent `reason_code`.
  B  he requires the screen to be on the 「没给编号」 branch, and the uppercased/truncated sentence to appear
     nowhere on the page. My arm judged the card minus its own fold, never the page, and never asserted the
     no-code copy was present.

Counted exact-match edits again: a drifted anchor aborts instead of producing a silent no-op.
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
    '''const Q68_CODE = "ZZ_Q68_SERVER_CODE";''',
    '''const Q68_CODE = "ZZ_Q68_SERVER_CODE";
/* CMDR 04:14 names `{"error":{"code":"BUDGET_INFEASIBLE"}}` as the shape a traveller must be able to see,
   and `serverReasonCode` accepts three machine keys, so each key gets its own arm and its own code. */
const Q68_CODE_KEYS: Array<[string, string]> = [
  ["reason_code", Q68_CODE],
  ["code", "BUDGET_INFEASIBLE"],
  ["message_key", "ZZ_Q68_MESSAGE_KEY"],
];''',
    1,
)

# Q68b: the no-code branch has to be shown present, and the screaming form has to be absent page-wide,
# not merely absent from the card. The attributed fold is the sentence's one sanctioned home (Q67=①), so it
# is removed by its own raw textContent before the page is searched -- cleaned text would not match.
rep(
    '''  const reasonEl = page.getByTestId("plan-ai-reason");
  const reasonText = clean(await reasonEl.textContent().catch(() => ""));''',
    '''  const reasonEl = page.getByTestId("plan-ai-reason");
  const reasonText = clean(await reasonEl.textContent().catch(() => ""));
  const reasonRaw = (await reasonEl.textContent().catch(() => "")) ?? "";
  /* the page as one surface, with the sanctioned attributed copy taken back out of it */
  const pageButFold = ((await domReading(page)).body || "").replace(reasonRaw, "");''',
    1,
)
rep(
    '''    needle_in_dom: dom.body.includes(Q68_PROSE),
  };''',
    '''    needle_in_dom: dom.body.includes(Q68_PROSE),
    no_code_branch_on_screen: /（没给编号）|\\(none given\\)/.test(cardAll),
    uppercased_prose_anywhere_but_the_fold: pageButFold
      .toUpperCase()
      .includes(Q68_PROSE.toUpperCase().slice(0, 60)),
    prose_anywhere_but_the_fold: pageButFold.includes(Q68_PROSE),
    page_text_length: pageButFold.length,
  };''',
    1,
)
rep(
    '''  expect(/服务器给出的原因|Reason the server gave/.test(cardAll),
    node(arm, `the attribution label is gone, so whatever sentence shows is unattributed (${cardAll.slice(0, 220)})`)).toBe(true);
});''',
    '''  expect(/服务器给出的原因|Reason the server gave/.test(cardAll),
    node(arm, `the attribution label is gone, so whatever sentence shows is unattributed (${cardAll.slice(0, 220)})`)).toBe(true);
  /* CMDR 04:14 B, first half: no machine code means the screen says it does not know. Deleting this
     branch would also answer "no prose in the slot", so it is asserted as a positive, not assumed. */
  expect(
    /（没给编号）|\\(none given\\)/.test(cardAll),
    node(arm, `the slot fell through neither the code nor the "no code" copy (${cardAll.slice(0, 240)}) -- an invented code and a silent slot are both wrong`),
  ).toBe(true);
  /* CMDR 0323 B, second half: the old fallback rendered the sentence truncated and uppercased. That form
     may not survive anywhere on the page except the attributed fold that holds the original. */
  expect(
    pageButFold.toUpperCase().includes(Q68_PROSE.toUpperCase().slice(0, 60)),
    node(arm, `the reply's sentence is on the page outside 技术详情 in the screaming form (${pageButFold.slice(0, 240)})`),
  ).toBe(false);
  expect(
    pageButFold.includes(Q68_PROSE),
    node(arm, `the reply's sentence is on the page outside 技术详情 even in its own case (${pageButFold.slice(0, 240)})`),
  ).toBe(false);
});

/* One arm per machine key: `serverReasonCode` reads them in a loop, but a loop is not evidence that each
   spelling reaches the traveller, and Q68's other half is "a real code still shows". */
for (const [key, code] of Q68_CODE_KEYS) {
  if (key === "reason_code") continue; // already the Q68a arm, kept as it was measured
  test(`N6_Q68${key === "code" ? "c" : "d"}_a_machine_code_in_${key}_reaches_the_code_slot — 编号那格：${key} 这一形给了真编号时，编号还在屏上`, async ({page}) => {
    test.setTimeout(300_000);
    const arm = key === "code" ? "Q68c" : "Q68d";
    await askTheSheet(page, jsonBody({error: {[key]: code}, detail: Q68_PROSE}));
    const card = clean(await page.getByTestId("plan-ai-result").textContent());
    const reason = clean(await page.getByTestId("plan-ai-reason").textContent().catch(() => ""));
    const dom = await domReading(page);
    readings[arm] = {asked_key: key, asked_code: code, card_text: card,
                     code_in_card: card.includes(code),
                     prose_outside_the_fold: clean(card.replace(reason, "")),
                     needle_in_dom: dom.body.includes(Q68_PROSE),
                     sweep_sees_the_tested_card: dom.attrs.includes("|data-testid|plan-ai-result"),
                     attribute_pairs_swept: dom.attr_pairs};
    expect(card.includes(code),
      node(arm, `the 原因编号 slot lost the code the server really sent in ${key} (${card.slice(0, 200)})`)).toBe(true);
    expect(/服务器回的原因编号|服务器给的原因编号/.test(card),
      node(arm, `the card no longer names this as a server-coded block for ${key} (${card.slice(0, 200)})`)).toBe(true);
    expect(dom.attrs.includes("|data-testid|plan-ai-result"),
      node(arm, `the attribute sweep found ${String(dom.attr_pairs)} pairs but not the tested card (${key})`)).toBe(true);
  });
}''',
    1,
)

if t.count('test(`N6_Q68') != 1 or "no_code_branch_on_screen" not in t:
    raise SystemExit("the Q68 amendment did not land")
SPEC.write_text(t, encoding="utf-8", newline="\n")
print("Q68c/Q68d arms added; Q68b now asserts the no-code copy and a page-wide screaming-form sweep")
