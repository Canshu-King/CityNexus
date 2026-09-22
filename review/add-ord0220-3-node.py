"""Append the ORD-0220 ③ node to the per-surface readings spec (script, not heredoc)."""

from pathlib import Path

SPEC = Path("D:/moodle/_qoder_integration_20260919/frontend/e2e/qoder-wizard-hint-surface-readings.spec.ts")

NODE = '''
test("ord0220-3-a-refused-press-brings-its-reason-on-screen — 按下去什么都没发生，这一格不再成立", async ({
  page,
}) => {
  test.setTimeout(300_000);
  const NODE = "ord0220-3-a-refused-press-brings-its-reason-on-screen";
  await reachStep2WithABlockedBudget(page);
  await settledSurface(page, \'[data-testid="trial-required-hint"]\', NODE);
  /* Reproduce the reported state: the traveller is at the top of the step, thumb on the sticky
     下一步, and the sentence is below the fold. */
  await page.evaluate(() => window.scrollTo(0, 0));
  const before = await page.evaluate(() => {
    const el = document.getElementById("trial-required-hint");
    const box = el?.getBoundingClientRect();
    return {
      top: box ? Math.round(box.top) : null,
      bottom: box ? Math.round(box.bottom) : null,
      innerHeight: window.innerHeight,
      inViewport: !!box && box.bottom > 0 && box.top < window.innerHeight,
    };
  });

  await page.getByTestId("trial-next").click({ force: true });
  await expect
    .poll(
      () =>
        page.evaluate(() => {
          const el = document.getElementById("trial-required-hint");
          const box = el?.getBoundingClientRect();
          return box ? Math.round(box.bottom) <= window.innerHeight : false;
        }),
      {
        message: node(
          NODE,
          `the press was refused but its reason never came on screen: before ${JSON.stringify(before)}`,
        ),
        timeout: 4_000,
      },
    )
    .toBe(true);
  const focused = await page.evaluate(() => document.activeElement?.id ?? null);
  expect(
    focused,
    node(NODE, `the reason is on screen but the traveller's position did not move there: activeElement is ${JSON.stringify(focused)}`),
  ).toBe("trial-required-hint");
  const after = await page.evaluate(() => {
    const el = document.getElementById("trial-required-hint");
    const box = el?.getBoundingClientRect();
    return {
      top: box ? Math.round(box.top) : null,
      bottom: box ? Math.round(box.bottom) : null,
      innerHeight: window.innerHeight,
      inViewport: !!box && box.bottom > 0 && box.top < window.innerHeight,
    };
  });
  writeFileSync(
    evidencePath("ui-overnight/ord0220-reason-on-screen.json"),
    JSON.stringify(
      {
        generatedBy: "e345b9d6",
        order: "ORD-0220 ③",
        head: process.env.CITYNEXUS_E2E_GIT_HEAD ?? "unknown",
        before,
        after,
        focusedAfterPress: focused,
        rule: "拦下时提示必须进入视口并被聚焦（bottom <= innerHeight）",
      },
      null,
      2,
    ) + "\\n",
    "utf-8",
  );
  await page.screenshot({ path: evidencePath("ui-overnight/ord0220-reason-on-screen.png"), fullPage: false });
});
'''


def main() -> int:
    text = open(SPEC, encoding="utf-8", newline="").read()
    if "ord0220-3-a-refused-press-brings-its-reason-on-screen" in text:
        print("already appended; nothing written")
        return 0
    if not text.rstrip().endswith("});"):
        print(f"ABORT: file does not end with a test close: {text.rstrip()[-40:]!r}")
        return 2
    updated = text.rstrip("\n") + "\n" + NODE
    open(SPEC, "w", encoding="utf-8", newline="").write(updated.replace("\r\n", "\n"))
    after = open(SPEC, encoding="utf-8", newline="").read()
    print(
        f"appended bytes={len(after.encode('utf-8')) - len(text.encode('utf-8'))} "
        f"node_present={'ord0220-3-a-refused-press' in after} crlf={after.count(chr(13) + chr(10))}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
