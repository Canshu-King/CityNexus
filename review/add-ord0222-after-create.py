"""Append the "still gone after the trip is created" arm to the surface-readings spec.

HJ-P1's wording was 「创建成功后仍会听到」, and my node only followed the fix as far as step 3.
Script rather than heredoc: a heredoc eats the backslash escapes in this file's TypeScript.
"""

from pathlib import Path

SPEC = Path("D:/moodle/_qoder_integration_20260919/frontend/e2e/qoder-wizard-hint-surface-readings.spec.ts")

NODE = '''
test("ord0222-6-the-announcement-is-still-gone-after-the-trip-exists — 创建成功之后也不该再播那一句", async ({
  page,
}) => {
  test.setTimeout(300_000);
  const NODE = "ord0222-6-the-announcement-is-still-gone-after-the-trip-exists";
  await reachStep2WithABlockedBudget(page);
  await page.getByTestId("trial-next").click({ force: true });
  await expect
    .poll(() => surface(page, "#trial-next-reason").then((read) => read.text), {
      message: node(NODE, "the refused press never wrote an announcement, so this arm would pass on nothing"),
      timeout: 5_000,
    })
    .toContain("总预算");
  await page.getByTestId("trial-budget").fill("1500");
  await page.getByTestId("trial-next").click();
  await expect(page.getByTestId("trial-step3-body")).toBeVisible({ timeout: 15_000 });
  /* Create for real.  The row must exist before the claim "nothing stale is announced after the
     trip exists" means anything. */
  await page.getByTestId("trial-create").click();
  await expect(page.getByTestId("today-heading")).toBeVisible({ timeout: 60_000 });
  const afterCreate = await surface(page, "#trial-next-reason");
  expect(
    afterCreate.text.includes("总预算"),
    node(NODE, `the trip exists and the announcement still names the fixed field: "${afterCreate.text}"`),
  ).toBe(false);
  writeFileSync(
    evidencePath("ui-overnight/ord0222-after-create.json"),
    JSON.stringify(
      {
        generatedBy: "e345b9d6",
        order: "ORD-0222 ②-follow-up (HJ-P1 19:46 wording)",
        head: process.env.CITYNEXUS_E2E_GIT_HEAD ?? "unknown",
        journeyOnScreen: ((await page.getByTestId("today-heading").innerText()) ?? "").trim(),
        announcementAfterCreate: afterCreate,
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
    if "ord0222-6-the-announcement-is-still-gone-after-the-trip-exists" in text:
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
        f"node_present={'ord0222-6-the-announcement' in after} crlf={after.count(chr(13) + chr(10))}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
