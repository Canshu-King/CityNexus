/* ORD-0489 · make the footprint set actually grow from the screen, and read the tally both sides.
 *
 * r3 pressed the first 打卡 control and the door kept 3 rows, so all r3 proved was that the notice
 * appears.  This walks every control on the itinerary, names which one the store accepted, and
 * reads the on-screen tally before and after the accepted press.  Text is written to a UTF-8 file
 * because the console on this box is GBK and would eat the Chinese sentences.
 */
const { chromium } = require("playwright");
const fs = require("fs");
const path = require("path");

const PREVIEW = process.env.CNX_PREVIEW || "http://127.0.0.1:8792";
const BACKEND = process.env.CNX_BACKEND || "http://127.0.0.1:8790";
const OUT = "D:/moodle/_qoder_seed_ord0489/evidence/ord0489_screens";

const rows = async (journeyId) => {
  const res = await fetch(`${BACKEND}/api/v1/journeys/${journeyId}/checkins`);
  return res.json();
};

const labelOf = (loc) =>
  loc.evaluate((el) => (el.getAttribute("aria-label") || el.textContent || "").replace(/\s+/g, " ").trim());

(async () => {
  const journeys = await (await fetch(`${BACKEND}/api/v1/journeys`)).json();
  const JOURNEY = journeys.find((j) => j.city_code === "CN-TIANJIN").id;
  const report = { journey_id: JOURNEY, started_at: new Date().toISOString(), presses: [] };

  const browser = await chromium.launch();
  const ctx = await browser.newContext({ viewport: { width: 390, height: 844 }, hasTouch: true, isMobile: true, deviceScaleFactor: 3, locale: "zh-CN" });
  const page = await ctx.newPage();

  await page.goto(`${PREVIEW}/v8/${JOURNEY}`, { waitUntil: "domcontentloaded" });
  await page.waitForTimeout(2200);
  await page.goto(`${PREVIEW}/v8/trips`, { waitUntil: "domcontentloaded" });
  await page.waitForTimeout(2200);

  report.tally_before_on_screen = await page.locator('[data-testid="footprint-tally"]').count();
  const before = await rows(JOURNEY);
  report.door_rows_before = before.length;
  report.door_keys_before = before.map((r) => r.target_key);

  const controls = page.locator('[data-testid="stop-checkin"]');
  const count = await controls.count();
  report.control_count = count;
  for (let i = 0; i < count; i++) {
    const loc = controls.nth(i);
    await loc.scrollIntoViewIfNeeded().catch(() => {});
    await page.waitForTimeout(300);
    const box = await loc.boundingBox();
    if (!box) continue;
    const hit = await page.evaluate(
      ([x, y]) => {
        const el = document.elementFromPoint(x, y);
        return el ? el.getAttribute("data-testid") || el.tagName : null;
      },
      [box.x + box.width / 2, box.y + box.height / 2]
    );
    if (hit !== "stop-checkin") {
      report.presses.push({ index: i, label: await labelOf(loc), skipped: `hit-test=${hit}` });
      continue;
    }
    const beforeKeys = (await rows(JOURNEY)).map((r) => r.target_key);
    await loc.tap().catch(async () => loc.click());
    await page.waitForTimeout(1500);
    const notice = await page.locator('[data-testid="stop-checkin-notice"]').count()
      ? await page.locator('[data-testid="stop-checkin-notice"]').first().innerText()
      : null;
    const after = await rows(JOURNEY);
    const newKeys = after.map((r) => r.target_key).filter((k) => !beforeKeys.includes(k));
    report.presses.push({
      index: i,
      label: await labelOf(loc),
      hit_test: hit,
      box: { x: Math.round(box.x), y: Math.round(box.y), width: Math.round(box.width), height: Math.round(box.height) },
      notice: notice && notice.replace(/\s+/g, " ").trim(),
      door_rows_after: after.length,
      new_target_keys: newKeys,
      accepted: newKeys.length > 0,
    });
    if (newKeys.length > 0) {
      await page.goto(`${PREVIEW}/v8/footprints`, { waitUntil: "domcontentloaded" });
      await page.waitForTimeout(1800);
      report.tally_after_on_screen = await page.locator('[data-testid="footprint-tally"]').first().innerText();
      report.rows_after_on_screen = await page.locator('[data-testid="footprint-row"]').count();
      report.row_texts_after = (await page.locator('[data-testid="footprint-row"]').allInnerTexts()).map((t) => t.replace(/\s+/g, " ").trim().slice(0, 160));
      const file = path.join(OUT, "footprint_grew_r4.png");
      await page.screenshot({ path: file, fullPage: true });
      report.shot = { file: file.replace(/\\/g, "/"), bytes: fs.statSync(file).size };
      break;
    }
  }
  const afterAll = await rows(JOURNEY);
  report.door_rows_after = afterAll.length;
  await ctx.close();
  await browser.close();
  report.finished_at = new Date().toISOString();
  const stamp = report.finished_at.replace(/[-:]/g, "").slice(0, 13);
  const file = path.join(OUT, `walk_footprint_grow_r4_${stamp}.json`);
  fs.writeFileSync(file, JSON.stringify(report, null, 1), "utf-8");
  console.log(JSON.stringify({ evidence: file.replace(/\\/g, "/"), door_before: report.door_rows_before, door_after: report.door_rows_after }));
})().catch((exc) => {
  console.error("WALK_R4_FAILED", exc && exc.message ? exc.message : exc);
  process.exit(1);
});
