/* Building walk r2: after the hit-box extension, does the press still answer, and by how much did the
 * pressable area grow?
 *
 * r1 of this family had a bad sensor: it watched the canvas CSS transform for the re-centre button and an
 * aria-selected set for the stop list, neither of which is what those controls actually publish. The stop
 * buttons carry `aria-pressed` and the viewport button carries `data-viewport-state`, so this arm reads
 * those, and samples the pressable box with the same grid rule used on the avatar (so the two hands'
 * numbers mean the same thing).
 * argv: node map_press_after_r2.cjs <base> <out.json>
 */
const { chromium } = require("D:/moodle/_qoder_phone_ord0485_20260930/recut_avatar/frontend/node_modules/playwright");
const fs = require("fs");
const BASE = process.argv[2] || "http://127.0.0.1:4895";
const OUT = process.argv[3] || "D:/moodle/_qoder_phone_ord0485_20260930/evidence/map_press_after.json";
const run = { schema: "CNX_MAP_PRESS_AFTER_R2", base: BASE, started: new Date().toString(), controls: [], taps: [], errors: [] };

const PRESSABLE = (sel) => {
  const el = document.querySelector(sel);
  if (!el) return null;
  el.scrollIntoViewIfNeeded();
  const b = el.getBoundingClientRect();
  const cx = b.left + b.width / 2, cy = b.top + b.height / 2;
  let minx = cx, maxx = cx, miny = cy, maxy = cy;
  for (let dx = -40; dx <= 40; dx += 2) for (let dy = -40; dy <= 40; dy += 2) {
    const t = document.elementFromPoint(cx + dx, cy + dy);
    if (t && (t === el || el.contains(t))) { minx = Math.min(minx, cx + dx); maxx = Math.max(maxx, cx + dx);
      miny = Math.min(miny, cy + dy); maxy = Math.max(maxy, cy + dy); }
  }
  return { sel, painted: [Math.round(b.width), Math.round(b.height)],
           pressable: [Math.round(maxx - minx + 2), Math.round(maxy - miny + 2)],
           role: el.getAttribute("role"), tabindex: el.getAttribute("tabindex"),
           pe: getComputedStyle(el).pointerEvents, aria: (el.getAttribute("aria-label") || "").slice(0, 40),
           pressed_attr: el.getAttribute("aria-pressed"), viewport_state: el.getAttribute("data-viewport-state") };
};

(async () => {
  const browser = await chromium.launch();
  const ctx = await browser.newContext({ viewport: { width: 390, height: 844 }, deviceScaleFactor: 2,
    isMobile: true, hasTouch: true, serviceWorkers: "block" });
  const page = await ctx.newPage();
  page.on("pageerror", (e) => run.errors.push(String(e).slice(0, 160)));
  await page.goto(BASE + "/", { waitUntil: "networkidle", timeout: 60000 });
  await page.waitForTimeout(1200);
  const a = page.locator("[data-testid='trial-tianjin-demo']").first();
  if (await a.count()) { await a.evaluate(e => e.scrollIntoViewIfNeeded()); await a.click(); }
  await page.waitForTimeout(1500);
  const m = page.locator("[data-testid='v8-mobile-menu']").first();
  await m.evaluate(e => e.scrollIntoViewIfNeeded()); await m.click(); await page.waitForTimeout(900);
  const e2 = page.locator("[data-testid='v8-drawer-entry-map']").first();
  await e2.evaluate(e => e.scrollIntoViewIfNeeded()); await e2.click(); await page.waitForTimeout(2500);

  for (const sel of [".v8-map-page-grid .v8-map-stop", ".v8-map-panel .v8-map-viewport-control",
                     ".v9-map-marker", ".v8-map-stop-label"]) {
    const got = await page.evaluate(({ sel, src }) => eval(src)(sel), { sel, src: PRESSABLE.toString() });
    run.controls.push({ sel, ...(got || { missing: true }) });
  }

  const stopSel = ".v8-map-page-grid .v8-map-stop:nth-of-type(3)";
  const s0 = await page.evaluate(({ sel, src }) => eval(src)(sel), { sel: stopSel, src: PRESSABLE.toString() });
  let loc = page.locator(stopSel).first();
  if (await loc.count() === 0) loc = page.locator(".v8-map-page-grid .v8-map-stop").nth(2);
  await loc.click();
  await page.waitForTimeout(1600);
  const s1 = await page.evaluate(({ sel, src }) => eval(src)(sel), { sel: stopSel, src: PRESSABLE.toString() });
  run.taps.push({ what: "stop list row (third)", before: s0 && s0.pressed_attr, after: s1 && s1.pressed_attr,
    pins_now_pressed: await page.evaluate(() => Array.from(document.querySelectorAll(".v9-map-marker[aria-pressed=true]")).length) });

  const r0 = await page.evaluate(() => document.querySelector(".v8-map-panel .v8-map-viewport-control")
    .getAttribute("data-viewport-state"));
  await page.locator(".v8-map-panel .v8-map-viewport-control").first().click();
  await page.waitForTimeout(1600);
  run.taps.push({ what: "re-centre", before: r0,
    after: await page.evaluate(() => document.querySelector(".v8-map-panel .v8-map-viewport-control")
      .getAttribute("data-viewport-state")) });

  run.horizontal_overflow = await page.evaluate(() => document.documentElement.scrollWidth > document.documentElement.clientWidth + 2);
  run.finished = new Date().toString();
  fs.writeFileSync(OUT, JSON.stringify(run, null, 1));
  console.log(JSON.stringify({ controls: run.controls.map(c => ({ sel: c.sel, painted: c.painted,
    pressable: c.pressable, role: c.role, pe: c.pe, aria: c.aria, pressed: c.pressed_attr, state: c.viewport_state })),
    taps: run.taps, horizontal_overflow: run.horizontal_overflow, errors: run.errors.length }, null, 1));
  await browser.close();
})();
