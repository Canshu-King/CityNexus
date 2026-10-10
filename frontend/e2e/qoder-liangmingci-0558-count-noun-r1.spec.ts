/**
 * ORD-0558 -- the English verdict sentence counts its own noun.
 *
 * `DestinationPreparationPanel.tsx`'s COVERAGE_INCOMPLETE body read `${missing.length} categories`
 * outright, so a destination short of one fact was announced as "1 categories". This spec pins the
 * two states the traveller can actually reach -- one missing category and two -- on the English
 * face, and keeps the Chinese face as a control because this order changes English only.
 *
 * What is instrument and what is product:
 *   - the verdict, the reason code, the coverage map and every token in `missing_categories` come
 *     from this run's own backend, unchanged;
 *   - the only thing this file touches is how many of the server's own named gaps the screen is
 *     shown, which is what a count is. The slice is labelled in each evidence row.
 */
import { expect, test, type Page } from "@playwright/test";
import { writeFileSync } from "node:fs";
import { evidencePath } from "./_qoderEvidence";

const FILE = "e2e/qoder-liangmingci-0558-count-noun-r1.spec.ts";
const VIEWPORT = { width: 390, height: 844 };

test.use({ viewport: VIEWPORT, hasTouch: true });

/** The discover surface, in the language whose grammar is under test. */
async function openDiscover(page: Page, locale: "en" | "zh-CN"): Promise<void> {
  const seeded = await (await page.request.get("/api/v1/demo/scene")).json();
  const journeyId = String((seeded as { journey_id?: string }).journey_id ?? "");
  await page.addInitScript(
    (args) => {
      localStorage.clear();
      localStorage.setItem("citynexus.v8.journey_id", args.journeyId);
      localStorage.setItem("citynexus.locale", args.locale);
    },
    { journeyId, locale },
  );
  await page.goto("/v8/hub", { waitUntil: "load" });
  await expect(page.getByTestId("today-hero")).toBeVisible({ timeout: 30_000 });
  await page.goto("/v8/discover", { waitUntil: "load" });
  await expect(
    page.getByTestId("prep-panel"),
    `${FILE} :: the preparation flow is not on the discover surface`,
  ).toBeVisible({ timeout: 30_000 });
}

/** Show the screen only the first `take` of the gaps the server itself named. */
async function showFirstGaps(page: Page, take: number): Promise<{ server_named: string[] }> {
  let serverNamed: string[] = [];
  await page.route("**/api/v1/destinations/capability**", async (route) => {
    const real = await route.fetch();
    const body = (await real.json()) as Record<string, unknown>;
    const list = Array.isArray(body.missing_categories) ? body.missing_categories.map(String) : [];
    serverNamed = list;
    body.missing_categories = list.slice(0, take);
    body.recorded_by_instrument = {
      taken: take,
      server_named_count: list.length,
      note: "instrument: how many of the server's own named gaps the screen is shown",
    };
    await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(body) });
  });
  await page.getByTestId("prep-query").fill("天津");
  await page.getByTestId("prep-check").click();
  await expect(
    page.getByTestId("prep-verdict"),
    `${FILE} :: no server verdict reached the screen for a city with no catalogue`,
  ).toBeVisible({ timeout: 30_000 });
  return { server_named: serverNamed };
}

async function readVerdict(page: Page): Promise<{ reason: string | null; title: string; body: string; missing: string }> {
  const panel = page.getByTestId("prep-panel");
  return {
    reason: await panel.getAttribute("data-reason"),
    title: (await page.getByTestId("prep-verdict-title").innerText()).trim(),
    body: (await page.getByTestId("prep-verdict-body").innerText()).replace(/\s+/g, " ").trim(),
    missing: (await page.getByTestId("prep-missing").innerText().catch(() => "")).replace(/\s+/g, " ").trim(),
  };
}

type State = { take: number; noun: string };
const STATES: State[] = [
  { take: 1, noun: "category" },
  { take: 2, noun: "categories" },
];

for (const state of STATES) {
  test(`ord0558-en-one-count-${state.take} — 英文面数量 ${state.take} 的名词跟着数走`, async ({ page }) => {
    test.setTimeout(180_000);
    const id = `en-count-${state.take}`;
    await openDiscover(page, "en");
    const gaps = await showFirstGaps(page, state.take);
    const read = await readVerdict(page);
    const evidence = { order: "ORD-0558", spec: FILE, node: id, side: "en", state, read, gaps };
    /* Record first, assert second: the arm that is red by design still has to leave its reading. */
    writeFileSync(evidencePath(`ord0558/${id}.json`), JSON.stringify(evidence, null, 2) + "\n", "utf-8");
    await page.screenshot({ path: evidencePath(`ord0558/${id}.png`), fullPage: true });
    expect(
      read.reason,
      `${FILE} :: ${id} — the server did not answer COVERAGE_INCOMPLETE, so there is no counted sentence: ${JSON.stringify(read)}`,
    ).toBe("COVERAGE_INCOMPLETE");
    expect(
      read.body.includes(`${state.take} ${state.noun} missing`),
      `${FILE} :: ${id} — the English verdict does not read "${state.take} ${state.noun} missing": ${JSON.stringify(read.body)}`,
    ).toBe(true);
    expect(
      read.body.includes(`${state.take} ${state.noun === "category" ? "categories" : "category"} missing`),
      `${FILE} :: ${id} — the English verdict still carries the other number's noun: ${JSON.stringify(read.body)}`,
    ).toBe(false);
  });

  test(`ord0558-zh-one-count-${state.take} — 中文面同屏不动（本单只改英文侧）`, async ({ page }) => {
    test.setTimeout(180_000);
    const id = `zh-count-${state.take}`;
    await openDiscover(page, "zh-CN");
    const gaps = await showFirstGaps(page, state.take);
    const read = await readVerdict(page);
    const evidence = { order: "ORD-0558", spec: FILE, node: id, side: "zh", state, read, gaps };
    writeFileSync(evidencePath(`ord0558/${id}.json`), JSON.stringify(evidence, null, 2) + "\n", "utf-8");
    await page.screenshot({ path: evidencePath(`ord0558/${id}.png`), fullPage: true });
    expect(
      read.body.includes(`${state.take} 类事实`),
      `${FILE} :: ${id} — the Chinese verdict changed, and this order does not touch it: ${JSON.stringify(read.body)}`,
    ).toBe(true);
  });
}
