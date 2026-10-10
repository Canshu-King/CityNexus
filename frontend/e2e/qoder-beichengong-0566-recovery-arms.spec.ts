/**
 * ORD-0566 · the two recovery actions the server can send but this screen used to drop.
 *
 * What the order asks for and how this file answers it:
 *   "这条动作码真出现在返回里时那一屏渲染出的文字" -> `page.route()` answers
 *   `/destinations/capability` with the server's own shape for each of the two codes, and the test
 *   reads the painted `innerText` of the button -- a `data-testid` or a DOM node would not be enough;
 *   "你点下去之后的去向" -> PREPARE_PLACES is asserted to land on the import screen (the route the
 *   drawer already uses), CHOOSE_ANOTHER_DESTINATION is asserted to clear this verdict AND put the
 *   cursor in the query field, which is the difference between a door and a repaint;
 *   two languages -> each cell runs once in zh-CN and once in en, and in both the words are read back
 *   out of the dictionary file itself, so a label that silently stopped matching its key goes red.
 *
 * The payload shapes come from the panel's own contract (`DestinationCapability`), and the two codes
 * are the ones `_cmdr_action_code_front_r1.py` still counts as having no arm at the tip.
 */
import { expect, test, type Page } from "@playwright/test";
import fs from "node:fs";

const LOCALE_KEY = "citynexus.locale";
const JOURNEY_KEY = "citynexus.v8.journey_id";
const CAPABILITY = "**/api/v1/destinations/capability**";
const DICTIONARY = "src/i18n/LocaleContext.tsx";

/** The words this order adds, read from the dictionary rather than restated here. */
function dictText(key: string, book: "en" | "zh"): string {
  const src = fs.readFileSync(DICTIONARY, "utf8");
  const zhStart = src.split("\n").findIndex((l) => l.startsWith("const zhCN: Dict"));
  const lines = src.split("\n");
  for (let i = 0; i < lines.length; i += 1) {
    const m = new RegExp('^\\s*"' + key + '": "(.*)",\\s*$').exec(lines[i]);
    if (!m) continue;
    const side = i < zhStart ? "en" : "zh";
    if (side === book) return m[1];
  }
  throw new Error("dictionary side missing for " + key + " " + book);
}

function capabilityPayload(action: string, reasonCode: string, verdict: string) {
  return {
    query: "备城工0566探针",
    destination_state: "RESOLVED",
    destination_resolution: "test",
    places: [],
    retryable: action === "RETRY_LATER",
    candidates: [],
    malformed_candidates: [],
    matched_label: "备城工0566探针",
    capability: verdict,
    reason_code: reasonCode,
    recommended_action: action,
    coverage: {},
    coverage_detail: {},
    missing_categories: [],
    hard_gaps: [],
  };
}

async function openPrep(page: Page, locale: string, action: string, reason: string, verdict: string) {
  const seeded = await (await page.request.get("/api/v1/demo/scene")).json();
  const journeyId = String((seeded as { journey_id?: string }).journey_id ?? "");
  expect(journeyId.length, "the shell needs a journey before the prep panel mounts").toBeGreaterThan(8);
  await page.addInitScript(
    ([loc, id]) => {
      localStorage.clear();
      localStorage.setItem("citynexus.locale", loc);
      localStorage.setItem("citynexus.v8.journey_id", id);
    },
    [locale, journeyId] as [string, string],
  );
  await page.route(CAPABILITY, (route) =>
    route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(capabilityPayload(action, reason, verdict)) }),
  );
  await page.goto("/v8/discover", { waitUntil: "load" });
  await expect(page.getByTestId("prep-panel")).toBeVisible({ timeout: 30_000 });
  await page.getByTestId("prep-query").fill("备城工0566探针");
  await page.getByTestId("prep-check").click();
  await expect(page.getByTestId("prep-verdict")).toBeVisible({ timeout: 20_000 });
}

test("0566-a PREPARE_PLACES really opens the place-import screen (zh then en)", async ({ page }) => {
  for (const locale of ["zh-CN", "en"]) {
    await openPrep(page, locale, "PREPARE_PLACES", "PLACES_NO_COORDINATE", "HYDRATABLE");
    const arm = page.getByTestId("prep-prepare-places");
    await expect(arm).toBeVisible();
    const painted = (await arm.innerText()).trim();
    const expected = dictText("discovery.preparePlaces", locale === "zh-CN" ? "zh" : "en");
    expect(painted, locale + " arm label must be the dictionary text").toBe(expected);
    // the code literal itself must never be what the traveller reads
    expect(painted).not.toContain("PREPARE_PLACES");
    await arm.click();
    await expect(page.getByTestId("poi-import")).toBeVisible({ timeout: 20_000 });
    expect(page.url()).toContain("import");
  }
});

test("0566-b CHOOSE_ANOTHER_DESTINATION clears the verdict and focuses the query (zh then en)", async ({ page }) => {
  for (const locale of ["zh-CN", "en"]) {
    await openPrep(page, locale, "CHOOSE_ANOTHER_DESTINATION", "NO_CANONICAL_IDENTITY", "UNAVAILABLE");
    const arm = page.getByTestId("prep-choose-another-primary");
    await expect(arm).toBeVisible();
    const painted = (await arm.innerText()).trim();
    const expected = dictText("discovery.pickAnotherDestination", locale === "zh-CN" ? "zh" : "en");
    expect(painted, locale + " arm label must be the dictionary text").toBe(expected);
    expect(painted).not.toContain("CHOOSE_ANOTHER_DESTINATION");
    await arm.click();
    await expect(page.getByTestId("prep-verdict")).toHaveCount(0);
    const focused = await page.evaluate(() => document.activeElement?.getAttribute("data-testid"));
    expect(focused, "the click has to hand the traveller back the field, not just repaint").toBe("prep-query");
  }
});
