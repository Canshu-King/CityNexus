import { expect, test } from "@playwright/test";

import { ensureDemoJourney, openScreen } from "./_qoderShellSeed";

/*
 * ORD-0602 甲半 (加闸工): the recovery door now states where the route timing behind a
 * weather switch came from, and that sentence has to reach the traveller's screen — not
 * only the JSON.  Nothing here fabricates a response: the journey is seeded by the shell's
 * own demo button, the click is the traveller's own "rain" control, and the assertion
 * reads the text the product rendered into its status element.
 */

const LIVE_SENTENCE = "measured by a provider";
const SYNTHETIC_SENTENCE = "synthetic or estimated";

test("the rain switch says, on the glass, who measured the route timing", async ({ page }) => {
  test.setTimeout(180_000);
  await ensureDemoJourney(page);
  await openScreen(page, "/v8/live", ["live-report-rain"]);

  const button = page.getByTestId("live-report-rain");
  await expect(button).toBeVisible();
  await button.click();

  const message = page.locator(".v8-message");
  await expect(message).toBeVisible({ timeout: 30_000 });
  // The status line changes in two steps (recovery outcome, then the source sentence appended),
  // so wait until it actually carries one of the two source sentences rather than any text.
  await expect
    .poll(async () => ((await message.count()) ? await message.first().innerText() : ""), {
      timeout: 30_000,
      message: "the status line never carried a route-source sentence",
    })
    .toMatch(new RegExp(`${LIVE_SENTENCE}|${SYNTHETIC_SENTENCE}`));

  const rendered = await message.first().innerText();
  const truth = await page.evaluate(() => localStorage.getItem("citynexus.v8.journey_id") ?? "");
  console.log(
    "JZ0602-SCREEN journey=%s\nJZ0602-SCREEN rendered .v8-message=%j\nJZ0602-SCREEN has-live-phrase=%s has-synthetic-phrase=%s",
    truth,
    rendered,
    rendered.includes(LIVE_SENTENCE),
    rendered.includes(SYNTHETIC_SENTENCE),
  );
  /* The status line sits above the fold on this surface: scroll it in and shoot the element
     itself, otherwise the picture proves nothing about what a traveller can read. */
  await message.first().scrollIntoViewIfNeeded();
  await expect(message.first()).toBeInViewport();
  await message.first().screenshot({ path: "e2e-artifacts/jz0602-message-crop.png" });
  await page.screenshot({ path: "e2e-artifacts/jz0602-route-truth-on-screen.png", fullPage: false });
  expect(rendered).toMatch(/measured by a provider|synthetic or estimated/);
});
