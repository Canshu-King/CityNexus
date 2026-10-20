/* Does the tab strip itself carry ANY signal that more tabs exist to the right?
 *
 * trips_tab_strip_r1.cjs collects every element on the screen whose words match 更多/向右/滑动/滚动/全部/→/›/».
 * On the trips page that list is not empty -- the day cards below carry 「详情 ›」 buttons -- so "the strip
 * has no hint" cannot be read off that list.  This arm attributes each match to its container and measures
 * how much of the second tab is actually on the glass.
 * argv: node trips_tab_hint_r1.cjs <base> <out.json>
 */
const { chromium } = require("D:/moodle/_qoder_phone_ord0485_20260930/recut_avatar/frontend/node_modules/playwright");
const fs = require("fs");
const BASE = process.argv[2] || "http://127.0.0.1:4895";
const OUT = process.argv[3] || "D:/moodle/_qoder_phone_ord0485_20260930/evidence/trips_tab_hint.json";

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

  const got = await page.evaluate(() => {
    const strip = document.querySelector(".trips-tabs");
    let scroller = strip;
    while (scroller && scroller.scrollWidth <= scroller.clientWidth + 2) scroller = scroller.parentElement;
    const tabs = Array.from(document.querySelectorAll("[data-testid^='trips-tab-']"));
    const inStrip = (el) => { let p = el; for (let i = 0; i < 12 && p; i++, p = p.parentElement) {
      if (p === strip) return true; } return false; };
    const hints = Array.from(document.querySelectorAll("button,[role='button'],a,span"))
      .filter((el) => /更多|向右|滑动|滚动|全部|→|›|»/.test((el.innerText || ""))
        && el.getBoundingClientRect().height > 0)
      .map((el) => { const b = el.getBoundingClientRect();
        return { words: el.innerText.trim().slice(0, 20), tag: el.tagName, inside_strip: inStrip(el),
                 cls: String(el.className || "").slice(0, 40), top: Math.round(b.top) }; });
    const vw = window.innerWidth;
    const sliver = tabs.slice(1).map((t) => { const b = t.getBoundingClientRect();
      return { testid: t.getAttribute("data-testid"), left: Math.round(b.left),
               visible_px: Math.round(Math.max(0, Math.min(b.right, vw) - b.left)) }; });
    return { inner_width: vw, strip_found: !!strip,
      strip_cls: strip ? String(strip.className).slice(0, 40) : null,
      scroller_cls: scroller ? String(scroller.className).slice(0, 40) : null,
      scroller_overflow_x: scroller ? getComputedStyle(scroller).overflowX : null,
      scroller_client_w: scroller ? Math.round(scroller.clientWidth) : null,
      scroller_scroll_w: scroller ? Math.round(scroller.scrollWidth) : null,
      strip_has_scrollbar_style: strip ? (() => { const s = getComputedStyle(strip);
        return { overflow_x: s.overflowX, scroll_w: Math.round(strip.scrollWidth),
                 client_w: Math.round(strip.clientWidth) }; })() : null,
      hints, hints_inside_strip: hints.filter((h) => h.inside_strip), sliver };
  });
  fs.writeFileSync(OUT, JSON.stringify({ schema: "CNX_TRIPS_TAB_HINT_R1", base: BASE, got, errors }, null, 1));
  console.log(JSON.stringify({ hints: got.hints.length, hints_inside_strip: got.hints_inside_strip.length,
    scroller: { cls: got.scroller_cls, overflow_x: got.scroller_overflow_x,
      client_w: got.scroller_client_w, scroll_w: got.scroller_scroll_w },
    sliver: got.sliver, errors: errors.length }, null, 1));
  await browser.close();
})();
