/* The cell-ten re-cut needs a picture taken ON the merged head, not inherited from the pre-merge build.
 * Same navigation as trips_tab_strip_r1.cjs (demo card -> nav-trips), then a viewport screenshot at 390x844
 * and one clipped to the tab strip so the four pills are readable at 1:1.
 * argv: node trips_tab_shot_r1.cjs <base> <out.png> [strip.png]
 */
const { chromium } = require("D:/moodle/_qoder_phone_ord0485_20260930/recut_avatar/frontend/node_modules/playwright");
const fs = require("fs");
const BASE = process.argv[2] || "http://127.0.0.1:4895";
const OUT = process.argv[3] || "D:/moodle/_qoder_phone_ord0485_20260930/evidence/trips_tab_strip_on_merged_tip.png";
const STRIP = process.argv[4] || "";

(async () => {
  const browser = await chromium.launch();
  const ctx = await browser.newContext({ viewport: { width: 390, height: 844 }, deviceScaleFactor: 2,
    isMobile: true, hasTouch: true, serviceWorkers: "block" });
  const page = await ctx.newPage();
  const errors = [];
  page.on("pageerror", (e) => errors.push(String(e).slice(0, 160)));
  await page.goto(BASE + "/", { waitUntil: "networkidle", timeout: 60000 });
  await page.waitForTimeout(1200);
  const a = page.locator("[data-testid='trial-tianjin-demo']").first();
  if (await a.count()) { await a.evaluate(e => e.scrollIntoViewIfNeeded()); await a.click(); }
  await page.waitForTimeout(1600);
  const nav = page.locator("[data-testid='nav-trips']").first();
  await nav.evaluate(e => e.scrollIntoViewIfNeeded()); await nav.click(); await page.waitForTimeout(2200);

  const box = await page.evaluate(() => {
    const tabs = Array.from(document.querySelectorAll("[data-testid^='trips-tab-']"));
    const first = tabs[0]; let p = first;
    while (p) { const s = getComputedStyle(p);
      if (s.overflowX !== "visible") break; p = p.parentElement; }
    const b = (p || first).getBoundingClientRect();
    return { left: Math.round(b.left), top: Math.round(b.top), width: Math.round(b.width),
             height: Math.round(b.height), n: tabs.length };
  });
  await page.screenshot({ path: OUT });
  if (STRIP) {
    await page.screenshot({ path: STRIP, clip: { x: Math.max(0, box.left), y: Math.max(0, box.top - 6),
      width: Math.min(390 - Math.max(0, box.left), box.width + 6), height: box.height + 12 } });
  }
  fs.writeFileSync(OUT + ".meta.json", JSON.stringify({ base: BASE, strip_box: box, errors }, null, 1));
  console.log(JSON.stringify({ out: OUT, strip: STRIP || null, strip_box: box,
    bytes: fs.statSync(OUT).size, errors: errors.length }, null, 1));
  await browser.close();
})();
