"""Rewrite the second half of the ORD-0180 gate around what this fixture can actually measure.

The stage cannot produce a real proposal here: POST /replans is refused by the server itself with 422
MOBILITY_DATA_UNAVAILABLE (captured in the evidence file's `staged.answers`), which is an environment
condition this lane may not paper over.  So the node measures the two things that are the panel's own
-- the idempotency key is sent and stays stable across retries, and a row appearing in the list does
not authorise the action -- and names the server-side replay invariant as unmeasured.

Written as a file rather than a heredoc: the replacement text contains escape sequences a shell scan
reads as UNC paths.
"""

import io

PATH = "D:/moodle/_qoder_integration_20260919/frontend/e2e/qoder-replan-review-actions.spec.ts"
MARKER = "  if (blocked || open.length === 0) {"

NEW_TAIL = '''  /* This fixture cannot produce a real proposal: POST /replans is refused by the server itself with
     422 MOBILITY_DATA_UNAVAILABLE (captured in `staged.answers`), which is an environment condition
     and not something this lane may paper over.  So the two things that ARE the panel's own are
     measured directly, and the server-side half is named as unmeasured rather than implied:
       (i)  the accept request carries an Idempotency-Key and the same key across retries, which is
            what makes a replay a replay instead of a second acceptance;
       (ii) a row merely *appearing* in the list does not authorise the action -- with the list
            answered by the gate, the real server still refuses, and the screen must report that
            refusal rather than proceed (ORD-0183 2). */
  await page.route(`**/api/v1/journeys/${journeyId}/replans`, async (route) => {
    if (route.request().method() !== "GET") {
      await route.fallback();
      return;
    }
    const real = await route.fetch();
    const rows = (await real.json()) as Array<Record<string, unknown>>;
    /* The gate's invention, labelled: one open-looking row, so the accept action has a subject. */
    const stubbed = rows.length
      ? rows
      : [
          {
            id: "gate-stub-proposal-0001",
            journey_id: journeyId,
            status: "PRESENTED",
            created_at: new Date().toISOString(),
          },
        ];
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(stubbed),
    });
  });
  await page.reload({ waitUntil: "load" });
  await expect(page.getByTestId("today-hero")).toBeVisible({ timeout: 30_000 });
  await openStageEntry(page, "the stubbed review rows");

  const acceptRow = page.getByTestId("sim-action-accept");
  await acceptRow.scrollIntoViewIfNeeded();
  expect(
    await acceptRow.getAttribute("aria-disabled"),
    node(NODE, "the list shows an open proposal and the accept row is still blocked -- the row is not following the list it reads"),
  ).toBeNull();

  await acceptRow.click();
  await page.waitForTimeout(1_500);
  const outcomeAfterFirst = (await page.getByTestId("sim-outcome").innerText().catch(() => ""))
    .replace(/\\s+/g, " ");
  /* Second attempt on the same row (it stays offered because the server refused): the panel must
     resend the SAME key, or the second tap is a different request wearing the same intent. */
  if ((await acceptRow.getAttribute("aria-disabled")) === null) {
    await acceptRow.click();
    await page.waitForTimeout(1_500);
  }
  const keys = sent.filter((item) => item.url.includes("/accept")).map((item) => item.key);

  writeFileSync(
    evidencePath("ui-overnight/ord0180-idempotent-accept.json"),
    JSON.stringify(
      {
        generatedBy: "e345b9d6",
        node: NODE,
        head: process.env.CITYNEXUS_E2E_GIT_HEAD ?? "unknown",
        proposalIdUsed: "gate-stub-proposal-0001",
        sentAcceptRequests: keys,
        distinctKeys: Array.from(new Set(keys)),
        outcomeAfterFirst,
        notMeasured:
          "the server-side replay invariant (same Idempotency-Key produces no second change) could not be measured on this fixture: POST /replans is refused 422 MOBILITY_DATA_UNAVAILABLE, so no real proposal exists to accept.  Measured instead: the panel sends a key and keeps it stable across retries, and it reports the server's refusal rather than treating list membership as authority.",
        stageRefusal: staged.answers.filter((item) => item.status !== 200),
      },
      null,
      2,
    ) + "\\n",
    "utf-8",
  );

  expect(
    keys.length,
    node(NODE, `the accept row was pressable and no accept request went out: ${JSON.stringify(sent)}`),
  ).toBeGreaterThan(0);
  expect(
    keys.every((key) => typeof key === "string" && key.length > 0),
    node(NODE, `an accept request went out without an Idempotency-Key: ${JSON.stringify(sent)}`),
  ).toBe(true);
  expect(
    Array.from(new Set(keys)).length,
    node(NODE, `the row minted a fresh key per tap, so a replay would be a second acceptance: ${JSON.stringify(keys)}`),
  ).toBe(1);
  expect(
    /拒绝|没有|失败|不存在|未找到|空/.test(outcomeAfterFirst),
    node(NODE, `with the list showing an open proposal and the server refusing that id, the screen reported ${JSON.stringify(outcomeAfterFirst)} -- list membership must not read as permission`),
  ).toBe(true);
});
'''


def main() -> int:
    text = io.open(PATH, encoding="utf-8", newline="").read()
    index = text.find(MARKER)
    if index < 0:
        print("ABORT: the anchor is not in the file; nothing was written")
        return 2
    updated = text[:index] + NEW_TAIL
    io.open(PATH, "w", encoding="utf-8", newline="").write(updated)
    after = io.open(PATH, encoding="utf-8", newline="").read()
    print(
        f"old_tail_chars={len(text) - index} new_tail_chars={len(NEW_TAIL)} "
        f"crlf={io.open(PATH, 'rb').read().count(chr(13).encode() + chr(10).encode())} "
        f"has_notMeasured={'notMeasured' in after}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
