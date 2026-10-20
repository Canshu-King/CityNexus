/* Building walk: how much room is there to extend a hit box outward on the map screen?
 *
 * cn-pulse-map.css:96-101 records the factory's answer to the touch floor: keep the painted box, extend
 * the hit box outward, and do not let the extension overlap a neighbour (that panel uses a 16 px row gap so
 * an 8 px extension stays 6 px clear).  Before I pick a number for the stop list and the viewport controls,
 * I measure what is actually between them on the phone, not what the comment implies.
 * argv: node map_gap_probe_r1.cjs <base> <out.json>
 */
const { chromium } = require("D:/moodle/_qoder_phone_ord0485_20260930/recut_avatar/frontend/node_modules/playwright");
const fs = require("fs");
const BASE = process.argv[2] || "http://127.0.0.1:4895";
const OUT = process.argv[3] || "D:/moodle/_qoder_phone_ord0485_20260930/evidence/map_gaps.json";

(async () => {
  const browser = await chromium.launch();
  const ctx = await browser.newContext({ viewport: { width: 390, height: 844 }, deviceScaleFactor: 2,
    isMobile: true, hasTouch: true, serviceWorkers: "block" });
  const page = await ctx.newPage();
  await page.goto(BASE + "/", { waitUntil: "networkidle", timeout: 60000 });
  await page.waitForTimeout(1200);
  const a = page.locator("[data-testid='trial-tianjin-demo']").first();
  if (await a.count()) { await a.evaluate(e => e.scrollIntoViewIfNeeded()); await a.click(); }
  await page.waitForTimeout(1500);
  const m = page.locator("[data-testid='v8-mobile-menu']").first();
  await m.evaluate(e => e.scrollIntoViewIfNeeded()); await m.click(); await page.waitForTimeout(900);
  const e2 = page.locator("[data-testid='v8-drawer-entry-map']").first();
  await e2.evaluate(e => e.scrollIntoViewIfNeeded()); await e2.click(); await page.waitForTimeout(2500);

  const got = await page.evaluate(() => {
    const rows = (sel) => Array.from(document.querySelectorAll(sel)).map((el) => {
      const b = el.getBoundingClientRect(); const s = getComputedStyle(el);
      return { top: Math.round(b.top), bottom: Math.round(b.bottom), left: Math.round(b.left),
               right: Math.round(b.right), h: Math.round(b.height), w: Math.round(b.width),
               mt: s.marginTop, mb: s.marginBottom, gap: s.rowGap, pe: s.pointerEvents,
               testid: el.getAttribute("data-testid") }; });
    const stops = rows(".v8-map-page-grid .v8-map-stop");
    const ctrls = rows(".v8-map-panel .v8-map-viewport-control");
    const wrap = document.querySelector(".v8-map-panel .v8-map-viewport-controls");
    const gaps = [];
    for (let i = 1; i < stops.length; i++) gaps.push(stops[i].top - stops[i - 1].bottom);
    const cg = [];
    for (let i = 1; i < ctrls.length; i++) cg.push(ctrls[i].left - ctrls[i - 1].right);
    return { stops, stop_gaps: gaps, controls: ctrls, control_gaps: cg,
      controls_wrap: wrap ? { gap: getComputedStyle(wrap).gap, pe: getComputedStyle(wrap).pointerEvents,
        box: (b => [Math.round(b.width), Math.round(b.height)])(wrap.getBoundingClientRect()) } : null,
      list_style: (() => { const l = document.querySelector(".v8-map-page-grid .v8-map-stops");
        return l ? { gap: getComputedStyle(l).rowGap, box: (b => [Math.round(b.width), Math.round(b.height)])(l.getBoundingClientRect()) } : null; })() };
  });
  fs.writeFileSync(OUT, JSON.stringify({ schema: "CNX_MAP_GAP_PROBE_R1", base: BASE, got }, null, 1));
  console.log(JSON.stringify({ stop_count: got.stops.length, stop_h: got.stops.map(s => s.h),
    stop_gaps: got.stop_gaps, list_gap: got.list_style, ctrl_h: got.controls.map(c => c.h),
    ctrl_gaps: got.control_gaps, ctrl_wrap: got.controls_wrap }, null, 1));
  await browser.close();
})();
