/* ORD-0489 · why did one 打卡 control fail its hit test at 390 wide?
 *
 * r4 skipped control index 1 because `document.elementFromPoint` at its centre answered `nav-map`.
 * This measures every 打卡 control and every bottom-nav element in the same frame: boxes, the name
 * the hit test returns, and the overlap area.  Nothing is pressed here, so it is a geometry reading
 * and not a behaviour claim.
 */
const { chromium } = require("playwright");
const fs = require("fs");
const path = require("path");

const PREVIEW = process.env.CNX_PREVIEW || "http://127.0.0.1:8792";
const BACKEND = process.env.CNX_BACKEND || "http://127.0.0.1:8790";
const OUT = "D:/moodle/_qoder_seed_ord0489/evidence/ord0489_screens";

(async () => {
  const journeys = await (await fetch(`${BACKEND}/api/v1/journeys`)).json();
  const J = journeys.find((j) => j.city_code === "CN-TIANJIN").id;
  const browser = await chromium.launch();
  const ctx = await browser.newContext({ viewport: { width: 390, height: 844 }, hasTouch: true, isMobile: true, deviceScaleFactor: 3, locale: "zh-CN" });
  const page = await ctx.newPage();
  await page.goto(`${PREVIEW}/v8/${J}`, { waitUntil: "domcontentloaded" });
  await page.waitForTimeout(2200);
  await page.goto(`${PREVIEW}/v8/trips`, { waitUntil: "domcontentloaded" });
  await page.waitForTimeout(2500);

  const controls = page.locator('[data-testid="stop-checkin"]');
  const n = await controls.count();
  const nav = await page.evaluate(() => {
    const els = Array.from(document.querySelectorAll('[data-testid^="nav-"]'));
    return els.map((el) => {
      const r = el.getBoundingClientRect();
      return { testid: el.getAttribute("data-testid"), x: Math.round(r.x), y: Math.round(r.y), width: Math.round(r.width), height: Math.round(r.height) };
    });
  });
  const readings = [];
  for (let i = 0; i < n; i++) {
    const loc = controls.nth(i);
    await loc.scrollIntoViewIfNeeded().catch(() => {});
    await page.waitForTimeout(400);
    const box = await loc.boundingBox();
    if (!box) { readings.push({ index: i, box: null }); continue; }
    const hit = await page.evaluate(
      ([x, y]) => {
        const el = document.elementFromPoint(x, y);
        const chain = [];
        let cur = el;
        for (let k = 0; cur && k < 4; k += 1) { chain.push(cur.getAttribute("data-testid") || cur.tagName); cur = cur.parentElement; }
        return { at_point: el ? el.getAttribute("data-testid") || el.tagName : null, chain };
      },
      [box.x + box.width / 2, box.y + box.height / 2]
    );
    const overlaps = nav
      .map((nv) => {
        const ox = Math.max(0, Math.min(box.x + box.width, nv.x + nv.width) - Math.max(box.x, nv.x));
        const oy = Math.max(0, Math.min(box.y + box.height, nv.y + nv.height) - Math.max(box.y, nv.y));
        return { nav: nv.testid, overlap_px2: Math.round(ox * oy), nav_box: nv };
      })
      .filter((o) => o.overlap_px2 > 0);
    readings.push({
      index: i,
      label: await loc.evaluate((el) => (el.getAttribute("aria-label") || el.textContent || "").replace(/\s+/g, " ").trim()),
      box: { x: Math.round(box.x), y: Math.round(box.y), width: Math.round(box.width), height: Math.round(box.height) },
      scroll_y: await page.evaluate(() => window.scrollY),
      hit_at_centre: hit.at_point,
      hit_chain: hit.chain,
      overlaps_nav: overlaps,
    });
  }
  const shotFile = path.join(OUT, "checkin_geometry_r5.png");
  await page.screenshot({ path: shotFile, fullPage: true });
  const report = { journey_id: J, viewport: { width: 390, height: 844 }, nav_elements: nav, controls: readings, shot: { file: shotFile.replace(/\\/g, "/"), bytes: fs.statSync(shotFile).size }, taken_at: new Date().toISOString() };
  const stamp = report.taken_at.replace(/[-:]/g, "").slice(0, 13);
  const file = path.join(OUT, `checkin_geometry_r5_${stamp}.json`);
  fs.writeFileSync(file, JSON.stringify(report, null, 1), "utf-8");
  console.log(JSON.stringify({ evidence: file.replace(/\\/g, "/"), controls: readings.length, blocked: readings.filter((r) => r.hit_at_centre && r.hit_at_centre !== "stop-checkin").length }));
  await ctx.close();
  await browser.close();
})().catch((exc) => {
  console.error("R5_FAILED", exc && exc.message ? exc.message : exc);
  process.exit(1);
});
