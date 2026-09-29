/* ORD-0435 -- which layer actually holds the write? (lane dt, be19052c)
 *
 * The commander's second condition is a read-back of the activity from the server after a pick, not a
 * screenshot of the multi-select. The screen's receipt block is component state, so the honest test is
 * to reload the page and see what survives:
 *   A) after 完成: the receipt is on screen AND the same row answers `GET /plans/{id}`;
 *   B) after a real reload of /v8/discover: the receipt is gone from the DOM (it was never a durable
 *      surface), while the row is still there -- twice over, once through the route and once straight
 *      out of the sqlite file the backend has open.
 * If B showed the receipt still on screen with nothing behind it, that would be exactly the
 * "client state pretending to be added" the order forbids. This prints both halves so the claim can be
 * made about the store rather than about a div.
 */
const { chromium } = require("D:/moodle/CityNexus/frontend/node_modules/playwright");
const fs = require("fs");
const { DatabaseSync } = require("node:sqlite");

const BASE = process.argv[2] || "http://127.0.0.1:4835";
const API = process.argv[3] || "http://127.0.0.1:8812";
const DB = process.argv[4] || "D:/moodle/_qoder_b_ord0435b_20260929/backend/_ord0435c_priv.db";
const OUT = process.argv[5] || "D:/moodle/_qoder_b_ord0435b_20260929/review/ord0435";

const S = {
  goal: '[data-testid="v13-discovery-goal"]',
  submit: '[data-testid="v13-discover-submit"]',
  mode: 'select[aria-label]',
  cards: "article.v8-stay-card",
  tick: '[data-testid="v13-pick-candidate"]',
  finish: '[data-testid="v13-discovery-finish-batch"]',
  receipt: '[data-testid="v13-discovery-batch-receipt"]',
  row: '[data-testid="v13-discovery-batch-row"]',
  planLine: ".v8-batch-receipt-plan",
};
const UUID = /[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}/g;

async function discover(page, journeyId) {
  await page.goto(BASE + "/v8/discover", { waitUntil: "load" });
  await page.waitForSelector(S.goal, { timeout: 150_000 }).catch(() => {});
  await page.locator(S.goal).fill("河边适合散步咖啡");
  await page.locator(S.mode).first().selectOption("replay");
  await page.locator(S.submit).click();
  await page.waitForSelector(S.cards, { timeout: 150_000 }).catch(() => {});
  await page.waitForTimeout(1200);
}

(async () => {
  const scene = await (await fetch(API + "/api/v1/demo/scene")).json();
  const journeyId = String(scene.journey_id ?? "");
  if (journeyId.length < 8) throw new Error("stage named no journey");

  const browser = await chromium.launch();
  const ctx = await browser.newContext({ locale: "zh-CN", viewport: { width: 390, height: 844 } });
  await ctx.addInitScript((seed) => {
    localStorage.clear();
    localStorage.setItem("citynexus.locale", "zh-CN");
    localStorage.setItem("citynexus.v8.journey_id", seed);
  }, journeyId);
  const warm = await ctx.newPage();
  await warm.goto(BASE + "/v8/hub", { waitUntil: "load" });
  await warm.waitForSelector('[data-testid="today-hero"]', { timeout: 180_000 }).catch(() => {});
  await warm.close();

  const page = await ctx.newPage();
  const out = { base: BASE, api: BASE, journey_id: journeyId };

  await discover(page, journeyId);
  await page.locator(S.tick).first().click();
  await page.waitForTimeout(300);
  await page.locator(S.finish).click();
  await page.waitForSelector(S.receipt, { timeout: 150_000 }).catch(() => {});
  await page.waitForTimeout(1000);

  const rowsOnScreen = (await page.locator(S.row).allInnerTexts()).map((v) => v.replace(/\s+/g, " "));
  const planLine = (await page.locator(`${S.receipt} ${S.planLine}`).first().innerText().catch(() => "")) || "";
  const planId = (planLine.match(UUID) ?? [])[0] ?? null;
  const screenIds = rowsOnScreen.flatMap((v) => v.match(UUID) ?? []);
  out.A_after_done = {
    receipt_blocks: await page.locator(S.receipt).count(),
    row_count: rowsOnScreen.length,
    rows: rowsOnScreen,
    plan_line: planLine.replace(/\s+/g, " "),
    plan_id: planId,
    screen_activity_ids: screenIds,
  };
  await page.screenshot({ path: `${OUT}/persistence_A_after_done.png`, fullPage: true });

  /* the same row, read by the route rather than by the browser that wrote it */
  const viaRoute = planId ? await (await fetch(`${API}/api/v1/plans/${planId}`)).json() : null;
  const routeRows = (viaRoute?.activities ?? []).filter((a) => String(a.place_id ?? "").startsWith("real-place-"));
  out.A_route_read = {
    plan_status: viaRoute?.status ?? null,
    picked_rows: routeRows.map((a) => ({ id: a.id, title: a.title, start_at: a.start_at })),
  };

  /* B: a real reload. Whatever is on screen now is not carried by the component that wrote it. */
  await page.reload({ waitUntil: "load" });
  await page.waitForTimeout(2500);
  out.B_after_reload = {
    receipt_blocks_on_screen: await page.locator(S.receipt).count(),
    row_blocks_on_screen: await page.locator(S.row).count(),
    result_area_on_screen: await page.locator('[data-testid="v13-discovery-result"]').count(),
    note: "the console starts empty after a reload by design; the durable answer is the two reads below",
  };
  await page.screenshot({ path: `${OUT}/persistence_B_after_reload.png`, fullPage: true });

  const again = planId ? await (await fetch(`${API}/api/v1/plans/${planId}`)).json() : null;
  const againRows = (again?.activities ?? []).filter((a) => String(a.place_id ?? "").startsWith("real-place-"));
  const db = new DatabaseSync(DB.replace(/\//g, "\\"), { readOnly: true });
  const storeRows = planId
    ? db
        .prepare("SELECT id, title, place_id, start_at FROM activities WHERE plan_version_id = ? AND place_id LIKE 'real-place-%' ORDER BY sequence_no")
        .all(planId)
    : [];
  db.close();
  out.B_after_reload.route_still_answers = {
    plan_status: again?.status ?? null,
    picked_rows: againRows.map((a) => ({ id: a.id, title: a.title, start_at: a.start_at })),
  };
  out.B_after_reload.store_read_only = {
    picked_rows: storeRows.map((a) => ({ id: a.id, title: a.title, start_at: a.start_at })),
  };
  const key = (r) => `${r.id}|${r.title}|${r.start_at}`;
  out.verdict = {
    screen_ids_all_survive_reload_via_route: screenIds.every((id) =>
      (again?.activities ?? []).some((a) => a.id === id),
    ),
    route_and_store_same_rows:
      JSON.stringify(againRows.map(key)) === JSON.stringify(storeRows.map(key)),
    receipt_is_component_state_only: out.B_after_reload.receipt_blocks_on_screen === 0,
    row_still_written: storeRows.length === rowsOnScreen.length && storeRows.length > 0,
  };

  fs.writeFileSync(`${OUT}/persistence_across_reload.json`, JSON.stringify(out, null, 1), "utf-8");
  console.log(JSON.stringify({ A: out.A_after_done, A_route: out.A_route_read, B: out.B_after_reload, verdict: out.verdict }, null, 1));
  await browser.close();
})();
