"""Append the ORD-0220 ② node to the per-surface readings spec.

Script rather than heredoc: a heredoc eats the backslash escapes in this file's TypeScript and the
spec stops parsing (this lane hit that five times).
"""

from pathlib import Path

SPEC = Path("D:/moodle/_qoder_integration_20260919/frontend/e2e/qoder-wizard-hint-surface-readings.spec.ts")

NODE = '''
test("ord0220-2-the-announcement-retires-when-the-field-is-fixed — 听的那句也要跟现值重算", async ({
  page,
}) => {
  test.setTimeout(300_000);
  const NODE = "ord0220-2-the-announcement-retires-when-the-field-is-fixed";
  await reachStep2WithABlockedBudget(page);
  /* Press the blocked 下一步 the way a thumb does.  Without this the region is never written and
     the node would pass on an unfired stub -- this lane's own recorded trap. */
  await page.getByTestId("trial-next").click({ force: true });
  await expect
    .poll(() => surface(page, "#trial-next-reason").then((read) => read.text), {
      message: node(NODE, "the refused press wrote no announcement, so there is nothing to retire"),
      timeout: 5_000,
    })
    .toContain("总预算");
  const spoken = await surface(page, "#trial-next-reason");
  expect(
    spoken.insideSrOnly && !spoken.visuallyRendered,
    node(NODE, `the surface being retired is not the screen-reader one: ${JSON.stringify(spoken)}`),
  ).toBe(true);

  /* Fix the field.  The visible hint has always recomputed; the announcement must retire with it,
     or a screen-reader user is told the trip still needs a number that is already on the screen. */
  await page.getByTestId("trial-budget").fill("1500");
  await expect
    .poll(() => surface(page, "#trial-next-reason").then((read) => read.text), {
      message: node(
        NODE,
        `the announcement still names 总预算 after it was fixed: it was "${spoken.text}" and is still that`,
      ),
      timeout: 5_000,
    })
    .not.toContain("总预算");

  // And it stays retired on step 3, which is where HJ-P1's reading lived.
  await page.getByTestId("trial-next").click();
  await expect(page.getByTestId("trial-step3-body")).toBeVisible({ timeout: 15_000 });
  const atStep3 = await surface(page, "#trial-next-reason");
  expect(
    atStep3.text.includes("总预算"),
    node(NODE, `step 3 still announces a field the traveller already filled: "${atStep3.text}"`),
  ).toBe(false);
  writeFileSync(
    evidencePath("ui-overnight/ord0220-announcement-retired.json"),
    JSON.stringify(
      {
        generatedBy: "e345b9d6",
        order: "ORD-0220 ②",
        head: process.env.CITYNEXUS_E2E_GIT_HEAD ?? "unknown",
        method: "the region's own textContent, read per surface; body innerText is never used",
        spokenAtRefusal: spoken,
        afterFix: await surface(page, "#trial-next-reason"),
        atStep3,
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
    if "ord0220-2-the-announcement-retires-when-the-field-is-fixed" in text:
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
        f"node_present={'ord0220-2-the-announcement-retires' in after} crlf={after.count(chr(13) + chr(10))}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
