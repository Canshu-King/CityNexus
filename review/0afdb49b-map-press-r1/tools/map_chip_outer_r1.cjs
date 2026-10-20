/* Building walk: print one live map label element, attributes and all.
 * The source sets no role on the chip (frontend/src/components/v8/MapPanel.tsx:606-616), yet the page
 * reports role="button" on it.  Before claiming anything about a "button that cannot be pressed", read the
 * element the browser actually built.
 * argv: node map_chip_outer_r1.cjs <base> <out.json>
 */
const { chromium } = require("D:/moodle/_qoder_phone_ord0485_20260930/recut_avatar/frontend/node_modules/playwright");
const fs = require("fs");
const BASE = process.argv[2] || "http://127.0.0.1:4895";
const OUT = process.argv[3] || "D:/moodle/_qoder_phone_ord0485_20260930/evidence/map_chip_outer.json";
(async () => {
  const b = await chromium.launch();
  const ctx = await b.newContext({ viewport: { width: 390, height: 844 }, isMobile: true, hasTouch: true,
    serviceWorkers: "block", deviceScaleFactor: 2 });
  const p = await ctx.newPage();
  await p.goto(BASE + "/", { waitUntil: "networkidle", timeout: 60000 });
  await p.waitForTimeout(1200);
  const a = p.locator("[data-testid='trial-tianjin-demo']").first();
  if (await a.count()) { await a.evaluate(e => e.scrollIntoViewIfNeeded()); await a.click(); }
  await p.waitForTimeout(1500);
  const m = p.locator("[data-testid='v8-mobile-menu']").first();
  await m.evaluate(e => e.scrollIntoViewIfNeeded()); await m.click(); await p.waitForTimeout(900);
  const e2 = p.locator("[data-testid='v8-drawer-entry-map']").first();
  await e2.evaluate(e => e.scrollIntoViewIfNeeded()); await e2.click(); await p.waitForTimeout(2500);
  const got = await p.evaluate(() => {
    const chip = document.querySelector(".v8-map-stop-label");
    const stop = document.querySelector("button.v8-map-stop");
    const reset = document.querySelector("[data-testid='map-viewport-reset']");
    const pin = document.querySelector(".v9-map-marker");
    const attrs = (el) => el ? Array.from(el.attributes).map((x) => x.name + "=" + String(x.value).slice(0, 44)) : null;
    const box = (el) => { if (!el) return null; const r = el.getBoundingClientRect();
      return [Math.round(r.width), Math.round(r.height), Math.round(r.top)]; };
    return { chip_html: chip ? chip.outerHTML.slice(0, 320) : null, chip_attrs: attrs(chip), chip_box: box(chip),
      chip_style_pointer_events: chip ? getComputedStyle(chip).pointerEvents : null,
      stop_attrs: attrs(stop), stop_box: box(stop), stop_text: stop ? stop.innerText.trim().slice(0, 30) : null,
      reset_attrs: attrs(reset), reset_box: box(reset),
      pin_attrs: attrs(pin), pin_box: box(pin) };
  });
  fs.writeFileSync(OUT, JSON.stringify({ schema: "CNX_MAP_CHIP_OUTER_R1", base: BASE, got }, null, 1));
  console.log(JSON.stringify(got, null, 1));
  await b.close();
})();
