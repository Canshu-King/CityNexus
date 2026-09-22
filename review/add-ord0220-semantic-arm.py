"""Append the ORD-0220 ① node to the budget-tier gate.

Written as a script rather than an inline shell heredoc on purpose: a heredoc here eats the
backslash escapes in the TypeScript strings and the file stops parsing (this lane hit that five
times).  The anchor is re-measured in the same run, and the write is LF-only.
"""

from pathlib import Path

SPEC = Path("D:/moodle/_qoder_integration_20260919/frontend/e2e/qoder-budget-advisory-tiers.spec.ts")

NODE = '''
/* ORD-0220 ①: co-occurrence is not meaning.  The three assertions above only prove two strings are
   present somewhere in the block, which is why the red team's mutant survived: keep the caveat and
   append 「——不过实际上预算充足，放心消费」 and every one of them still reads green while the screen
   contradicts itself.  This node asserts what the caveat **says**. */
const RISK_WORDS = ["超出", "紧张", "吃紧", "不够"];
const ALLAY_WORDS = ["充足", "放心", "宽裕", "富余", "没问题", "绰绰有余"];

test("ord0220-1-the-tight-caveat-cannot-contradict-itself — caveat 说了什么也要断言", async ({
  page,
}) => {
  test.setTimeout(300_000);
  const NODE = "ord0220-1-the-tight-caveat-cannot-contradict-itself";
  await openHubWithReference(page, reference({ per_person_per_day_minor: 4000 }));
  const block = page.getByTestId("budget-advisory");
  await expect(
    block,
    node(NODE, "the tight advisory is not on screen, so there is no caveat to judge"),
  ).toBeVisible({ timeout: 20_000 });
  const text = (await block.innerText()).replace(/\\s+/g, " ");
  const risk = RISK_WORDS.filter((word) => text.includes(word));
  const allay = ALLAY_WORDS.filter((word) => text.includes(word));
  expect(
    risk.length,
    node(NODE, `the tight advisory carries a number but its caveat says no risk at all: "${text}"`),
  ).toBeGreaterThan(0);
  expect(
    allay,
    node(
      NODE,
      `the tight caveat contradicts itself -- risk ${JSON.stringify(risk)} printed alongside ${JSON.stringify(allay)}: "${text}"`,
    ),
  ).toEqual([]);
  writeFileSync(
    evidencePath("ui-overnight/ord0220-caveat-meaning.json"),
    JSON.stringify(
      {
        generatedBy: "e345b9d6",
        node: NODE,
        head: process.env.CITYNEXUS_E2E_GIT_HEAD ?? "unknown",
        text,
        risk,
        allay,
        rule: "tight 的 caveat 必须自己说出风险，且不得同时出现安抚类词",
      },
      null,
      2,
    ) + "\\n",
    "utf-8",
  );
});
'''


def main() -> int:
    text = open(SPEC, encoding="utf-8", newline="").read()
    if "ord0220-1-the-tight-caveat-cannot-contradict-itself" in text:
        print("already appended; nothing written")
        return 0
    if not text.rstrip().endswith("});"):
        print(f"ABORT: the file does not end with a test close, got {text.rstrip()[-40:]!r}")
        return 2
    updated = text.rstrip("\n") + "\n" + NODE
    open(SPEC, "w", encoding="utf-8", newline="").write(updated.replace("\r\n", "\n"))
    after = open(SPEC, encoding="utf-8", newline="").read()
    print(
        f"appended bytes={len(after.encode('utf-8')) - len(text.encode('utf-8'))} "
        f"node_present={'ord0220-1-the-tight-caveat' in after} crlf={after.count(chr(13) + chr(10))}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
