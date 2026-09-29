import { expect, test, type Page } from "@playwright/test";
import { writeFileSync } from "node:fs";
import { ensureDemoJourney, openScreen } from "./_qoderShellSeed";
import { evidencePath } from "./_qoderEvidence";

/**
 * ORD-0440 second half -- the three cells this panel used to carry, graded on the screen.
 *
 * The exposure rule (`ui_exposure_taint_ast_r7b.cjs`, blob
 * d3f66ce9fecd0790981a4fcdeb5e36b1c0fd10f2) counted three text-position cells here: the capability
 * read error, the action error, and the job's `error.message` printed behind the label
 * "服务器的原话". What the panel shows now is a dictionary sentence plus, where this device read a
 * status, that status -- one of the six fields the rule allows.
 *
 * The third cell is a relocation and not a deletion, which is the ruling ORD-0369 already made on
 * the same class of slot: the server's words must leave the reading line and stay reachable in the
 * technical detail, and the fold has to name what it holds. Both directions are asserted below,
 * because each one alone can pass on a screen that simply dropped the text.
 *
 * Staging, named as staging: arm A plants a 500 whose body carries a sentence that must never be
 * painted; arm B rewrites the *real* polled job record to add an error, exactly the way
 * `qoder-destination-preparation.spec.ts` pins a running job. No product behaviour is mocked out;
 * the responses are the transport, and the readings are the pixels.
 */

const FILE = "e2e/qoder-ord0440-prep-exposure-cells.spec.ts";
const rows: Record<string, unknown>[] = [];
const push = (arm: string, v: Record<string, unknown>) => {
  rows.push({ arm, ...v });
  console.log(`${FILE} :: ${arm} — ${JSON.stringify(v)}`);
};
const node = (n: string, m: string) => `${n}: ${m}`;

const painted = (page: Page, testId: string) =>
  page.getByTestId(testId).first().innerText({ timeout: 4_000 })
    .then((t) => t.replace(/\s+/g, " ").trim()).catch(() => null);

async function openPrep(page: Page): Promise<void> {
  await ensureDemoJourney(page);
  await openScreen(page, "/v8/discover", ["prep-query"]);
  await expect(page.getByTestId("prep-query").first()).toBeVisible({ timeout: 25_000 });
}

test("A reading-line discipline -- a planted 500 paints our sentence and the measured status, never its prose", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await openPrep(page);
  test.setTimeout(180_000);
  const PLANTED = "PLANTED SERVER SENTENCE THAT MUST NOT BE PAINTED";
  await page.route("**/api/v1/destinations/capability*", (route) =>
    route.fulfill({
      status: 500,
      contentType: "application/json",
      body: JSON.stringify({ error: { message: PLANTED, reason_code: "CAPABILITY_EXPLODED" } }),
    }),
  );
  await page.getByTestId("prep-query").fill("天津");
  await page.getByTestId("prep-check").click();
  await expect(page.getByTestId("prep-check-error").first()).toBeVisible({ timeout: 20_000 });
  const sentence = await painted(page, "prep-check-error");
  const status = await painted(page, "prep-check-error-status");
  const shellText = await page.locator("body").innerText();
  await page.screenshot({ path: evidencePath("ord0440", "arm_a_reading_line.png") });
  await page.unroute("**/api/v1/destinations/capability*");
  const locale = await page.evaluate(() => localStorage.getItem("citynexus.locale"));
  push("A", { sentence, status, locale, plantedPresentInBody: shellText.includes(PLANTED) });
  expect(sentence, node("A", "the failure has to be this screen's own sentence")).toBeTruthy();
  /* The dictionary's wording, in whichever arm the session is on. My first version pinned the Chinese
     half only and went red on an English session -- the claim is "a sentence we own", not "a sentence
     in one language", so the alternation is what the node actually grades. */
  expect(sentence!, node("A", "the reading line wears the dictionary's wording"))
    .toMatch(/was not read back|读回来/);
  expect(status, node("A", "what this device measured is the status, and it is allowed on screen")).toContain("500");
  expect(shellText.includes(PLANTED), node("A", "the planted prose reached the DOM")).toBe(false);
});

test("B relocation, not deletion -- the server's words leave the reading line and stay in the anchored fold", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await openPrep(page);
  test.setTimeout(240_000);
  const PLANTED = "服务器原话：这次准备在抓取阶段失败";
  await page.route("**/api/v1/catalog-hydrations/*", async (route) => {
    if (route.request().method() !== "GET") {
      await route.fallback();
      return;
    }
    const real = await route.fetch();
    const body = (await real.json()) as Record<string, unknown>;
    body.status = "FAILED";
    body.terminal = true;
    body.phase = "DISCOVERING_POIS";
    body.outcome = null;
    body.elapsed_ms = 5200;
    body.error = { message: PLANTED, reason_code: "CATALOG_HYDRATION_FAILED" };
    await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(body) });
  });
  await page.getByTestId("prep-query").fill("天津");
  await page.getByTestId("prep-check").click();
  await expect(page.getByTestId("prep-verdict").first()).toBeVisible({ timeout: 20_000 });
  await page.getByTestId("prep-start").click();
  await expect(page.getByTestId("prep-server-message").first()).toBeVisible({ timeout: 25_000 });
  const readingLine = await painted(page, "prep-server-message");
  const anchor = await page.getByTestId("prep-server-detail").first().getAttribute("data-cnx-field");
  const foldClosedText = await page.locator("body").innerText();
  await page.getByTestId("prep-server-summary").first().click();
  const wordsInFold = await painted(page, "prep-server-words");
  await page.screenshot({ path: evidencePath("ord0440", "arm_b_fold_open.png") });
  await page.unroute("**/api/v1/catalog-hydrations/*");
  push("B", {
    readingLine, anchor, wordsInFold,
    proseOnReadingLineBeforeOpening: foldClosedText.includes(PLANTED),
    staging: "the polled job record's own fields were pinned on top of a real hydration, the way qoder-destination-preparation.spec.ts does; body.error is planted",
  });
  expect(readingLine, node("B", "the reading line is this screen's sentence")).toBeTruthy();
  expect(readingLine!, node("B", "the reading line must not carry the server's sentence"))
    .not.toContain("服务器原话");
  expect(foldClosedText.includes(PLANTED), node("B", "the prose was on screen before anything was opened"))
    .toBe(false);
  expect(anchor, node("B", "the fold has to name the field it is anchored on")).toBe("response_received");
  expect(wordsInFold, node("B", "relocation is not deletion -- the words must still be reachable"))
    .toContain(PLANTED);
});

test.afterAll(() => {
  writeFileSync(
    evidencePath("ord0440", "readings.json"),
    JSON.stringify({ file: FILE, rows }, null, 1),
  );
});
