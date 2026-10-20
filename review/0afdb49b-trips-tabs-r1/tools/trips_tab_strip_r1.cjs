/* Building walk: the trips tab strip on a 390-wide phone -- can a person reach all four tabs at all?
 *
 * The press probe found the four tabs sit side by side at x = 17, 379, 741 and 1103, each 356 wide, on a
 * 390-wide screen: three of the four start beyond the right edge. Playwright still clicked one because it
 * scrolls containers on its own, so "a press answers" is NOT the same question as "a thumb can get there".
 * This arm reads the containing boxes (overflow, scroll width vs client width, whether it can scroll at all)
 * and whether anything on the glass tells the traveller there is more to the right.
 * argv: node trips_tab_strip_r1.cjs <base> <out.json>
 */
const { chromium } = require("D:/moodle/_qoder_phone_ord0485_20260930/recut_avatar/frontend/node_modules/playwright");
const fs = require("fs");
const BASE = process.argv[2] || "http://127.0.0.1:4895";
const OUT = process.argv[3] || "D:/moodle/_qoder_phone_ord0485_20260930/evidence/trips_tab_strip.json";

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
    const tabs = Array.from(document.querySelectorAll("[data-testid^='trips-tab-']"));
    const chain = (el) => { const out = []; let p = el.parentElement;
      for (let i = 0; i < 5 && p; i++, p = p.parentElement) {
        const s = getComputedStyle(p); const b = p.getBoundingClientRect();
        out.push({ tag: p.tagName, cls: String(p.className || "").slice(0, 46),
          overflow_x: s.overflowX, display: s.display, flex_wrap: s.flexWrap,
          client_w: Math.round(p.clientWidth), scroll_w: Math.round(p.scrollWidth),
          can_scroll: p.scrollWidth > p.clientWidth + 2, box_w: Math.round(b.width) });
      }
      return out; };
    const first = tabs[0];
    const inside = (el) => { const b = el.getBoundingClientRect();
      return b.left >= 0 && b.right <= window.innerWidth && b.width > 0; };
    const hints = Array.from(document.querySelectorAll("button,[role='button'],a,span"))
      .filter((el) => /更多|向右|滑动|滚动|全部|→|›|»/.test((el.innerText || "")) && el.getBoundingClientRect().height > 0)
      .map((el) => ({ tag: el.tagName, words: el.innerText.trim().slice(0, 24),
        h: Math.round(el.getBoundingClientRect().height) })).slice(0, 6);
    // scroll it the way a thumb would, then re-read which tabs are on screen
    const scroller = chain(first).find((c) => c.can_scroll);
    return { inner_width: window.innerWidth,
      tabs: tabs.map((t) => { const b = t.getBoundingClientRect();
        return { testid: t.getAttribute("data-testid"), words: t.innerText.trim().slice(0, 8),
                 left: Math.round(b.left), right: Math.round(b.right), w: Math.round(b.width),
                 h: Math.round(b.height), on_screen: inside(t),
                 centre_hit: (() => { const el = document.elementFromPoint(b.left + b.width / 2, b.top + b.height / 2);
                   return el ? (el.getAttribute("data-testid") || el.tagName) : null; })() }; }),
      ancestor_chain: chain(first), scroller_found: !!scroller,
      affordances: hints,
      body_head: document.body.innerText.replace(/\s+/g, " ").slice(0, 300) };
  });

  let afterScroll = null;
  const sc = got.ancestor_chain.find((c) => c.can_scroll);
  if (sc) {
    await page.evaluate(() => {
      const first = document.querySelector("[data-testid^='trips-tab-']");
      let p = first;
      while (p) { if (p.scrollWidth > p.clientWidth + 2) { p.scrollLeft = p.scrollWidth; break; } p = p.parentElement; }
    });
    await page.waitForTimeout(900);
    afterScroll = await page.evaluate(() => Array.from(document.querySelectorAll("[data-testid^='trips-tab-']"))
      .map((t) => { const b = t.getBoundingClientRect();
        return { testid: t.getAttribute("data-testid"), left: Math.round(b.left),
                 on_screen: b.left >= 0 && b.right <= window.innerWidth }; }));
  }
  fs.writeFileSync(OUT, JSON.stringify({ schema: "CNX_TRIPS_TAB_STRIP_R1", base: BASE, got, afterScroll, errors }, null, 1));
  console.log(JSON.stringify({ inner_width: got.inner_width, tabs: got.tabs,
    scroller_found: got.scroller_found, chain: got.ancestor_chain.slice(0, 3),
    affordances: got.affordances, afterScroll, errors: errors.length }, null, 1));
  await browser.close();
})();
