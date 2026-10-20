/* Building walk: who actually matches the census selector on the map screen?
 *
 * The 17-screen census lists both a 34-tall thing with no testid and 22-tall chips named
 * v8-map-stop-label among "controls under the touch floor".  Reading the source, the chip is
 * `aria-hidden="true"` with `pointer-events: none` by a documented rule ("the pin owns the tap"), and the
 * interactive element is the pin: `div.v9-map-marker[role=button][tabindex=0]` with click and keydown
 * handlers.  So before I report either as a defect I ask the browser, in the live page, which elements the
 * census selector really matches, and print what each one is.
 * argv: node map_census_membership_r1.cjs <base> <out.json>
 */
const { chromium } = require("D:/moodle/_qoder_phone_ord0485_20260930/recut_avatar/frontend/node_modules/playwright");
const fs = require("fs");
const BASE = process.argv[2] || "http://127.0.0.1:4895";
const OUT = process.argv[3] || "D:/moodle/_qoder_phone_ord0485_20260930/evidence/map_membership.json";

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

  const rows = await page.evaluate(() => {
    const SEL = "button,[role='button'],a[href],input[type='submit'],input[type='checkbox']";
    const strip = (x) => String(x || "").replace(/\s+/g, " ").trim();
    const vis = (el) => { const b = el.getBoundingClientRect(); const s = getComputedStyle(el);
      return b.width > 0 && b.height > 0 && s.display !== "none" && s.visibility !== "hidden"; };
    const matched = Array.from(document.querySelectorAll(SEL)).filter(vis).map((el) => {
      const b = el.getBoundingClientRect(); const s = getComputedStyle(el);
      return { tag: el.tagName, testid: el.getAttribute("data-testid"), role: el.getAttribute("role"),
        cls: String(el.className || "").slice(0, 48), words: strip(el.innerText || el.getAttribute("aria-label")).slice(0, 30),
        h: Math.round(b.height), w: Math.round(b.width), pe: s.pointerEvents, tabindex: el.getAttribute("tabindex"),
        aria_hidden: el.getAttribute("aria-hidden"),
        is_chip: el.classList.contains("v8-map-stop-label") };
    });
    const chips = Array.from(document.querySelectorAll(".v8-map-stop-label")).filter(vis).map((el) => ({
      cls: "v8-map-stop-label", pe: getComputedStyle(el).pointerEvents,
      role: el.getAttribute("role"), aria_hidden: el.getAttribute("aria-hidden"),
      matches_selector: el.matches(SEL) }));
    const pins = Array.from(document.querySelectorAll(".v9-map-marker")).filter(vis).map((el) => ({
      role: el.getAttribute("role"), tabindex: el.getAttribute("tabindex"),
      pe: getComputedStyle(el).pointerEvents, w: Math.round(el.getBoundingClientRect().width),
      h: Math.round(el.getBoundingClientRect().height), text: strip(el.innerText).slice(0, 4),
      matches_selector: el.matches(SEL) }));
    return { selector: SEL, matched_count: matched.length, matched: matched.slice(0, 24),
      chips: chips.slice(0, 4), pins: pins.slice(0, 4), chip_total: chips.length, pin_total: pins.length };
  });
  fs.writeFileSync(OUT, JSON.stringify({ schema: "CNX_MAP_CENSUS_MEMBERSHIP_R1", base: BASE, rows }, null, 1));
  console.log(JSON.stringify({ matched_count: rows.matched_count, chip_total: rows.chip_total,
    pin_total: rows.pin_total,
    a_chip_matches_selector: rows.chips.length ? rows.chips[0].matches_selector : null,
    a_pin_matches_selector: rows.pins.length ? rows.pins[0].matches_selector : null,
    pins: rows.pins, chips: rows.chips,
    matched_under_44: rows.matched.filter((r) => r.h < 44).map((r) => ({ tag: r.tag, testid: r.testid,
      cls: r.cls, h: r.h, w: r.w, pe: r.pe, role: r.role, words: r.words })) }, null, 1));
  await browser.close();
})();
