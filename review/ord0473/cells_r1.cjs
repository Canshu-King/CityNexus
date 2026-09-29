/* ORD-0473 screen cells 3 and 4, measured on the phone shape: the fixed bottom nav band versus the
   last drawer row (scrolled into view, centre hit), and a SCREAMING_SNAKE scan of the drawer's own
   rendered words.  Nothing here reads a data attribute -- every value is rendered text or geometry. */
const { chromium } = require("D:\\moodle\\CityNexus\\frontend\\node_modules\\playwright");
const fs = require("fs");
const BASE = process.argv[2], OUT = process.argv[3];
(async () => {
  const browser = await chromium.launch();
  const ctx = await browser.newContext({ viewport: { width: 390, height: 844 }, deviceScaleFactor: 1, isMobile: true, hasTouch: true });
  const page = await ctx.newPage();
  await page.goto(BASE + "/v8/hub", { waitUntil: "load" });
  await page.waitForTimeout(4000);
  if (await page.locator('[data-testid="trial-setup"]').count()) {
    await page.locator('[data-testid="trial-tianjin-demo"]').click({ timeout: 10000 }).catch(() => {});
    await page.waitForTimeout(4000);
  }
  await page.locator("button.v8-mobile-menu").first().click({ timeout: 8000 }).catch(() => {});
  await page.waitForTimeout(1200);

  const cells = await page.evaluate(() => {
    const nav = document.querySelector(".v8-mobile-nav");
    const navR = nav ? nav.getBoundingClientRect() : null;
    const rows = Array.from(document.querySelectorAll("#v8-nav-drawer button:not(.v8-quiet-button)"));
    const last = rows[rows.length - 1];
    const lr = last ? last.getBoundingClientRect() : null;
    const lcx = lr ? lr.left + lr.width / 2 : null, lcy = lr ? lr.top + lr.height / 2 : null;
    const hit = (lcx !== null) ? document.elementFromPoint(lcx, lcy) : null;
    // scroll the drawer itself, the way a traveller's thumb does, then re-hit the last row
    const drawer = document.querySelector("#v8-nav-drawer");
    const scroll_before = drawer ? Math.round(drawer.scrollTop) : null;
    if (drawer) drawer.scrollTop = drawer.scrollHeight;
    return { rows_rendered: rows.map((b) => b.innerText.replace(/\s+/g, " ").trim()),
             row_count: rows.length, scroll_before, scroll_after: drawer ? Math.round(drawer.scrollTop) : null,
             scroll_height: drawer ? drawer.scrollHeight : null, client_height: drawer ? drawer.clientHeight : null,
             bottom_nav: navR ? { top: Math.round(navR.top), h: Math.round(navR.height), z: getComputedStyle(nav).zIndex } : null,
             drawer_z: drawer ? getComputedStyle(drawer).zIndex : null,
             last_row_before_scroll: lr ? { y: Math.round(lr.top), bottom: Math.round(lr.bottom), h: Math.round(lr.height) } : null,
             last_hit_before_scroll: hit ? (hit === last || last.contains(hit) ? "SELF" : String(hit.className).slice(0, 40)) : null };
  });
  await page.waitForTimeout(700);
  const afterScroll = await page.evaluate(() => {
    const rows = Array.from(document.querySelectorAll("#v8-nav-drawer button:not(.v8-quiet-button)"));
    const last = rows[rows.length - 1];
    const r = last.getBoundingClientRect();
    const cx = r.left + r.width / 2, cy = r.top + r.height / 2;
    const top = document.elementFromPoint(cx, cy);
    const nav = document.querySelector(".v8-mobile-nav").getBoundingClientRect();
    return { last_row_after_scroll: { y: Math.round(r.top), bottom: Math.round(r.bottom), h: Math.round(r.height), point: [Math.round(cx), Math.round(cy)] },
             last_hit_after_scroll: top === last || last.contains(top) ? "SELF" : String(top.className).slice(0, 40),
             bottom_nav_top_after_scroll: Math.round(nav.top),
             overlap_with_nav: Math.max(0, Math.round(Math.min(r.bottom, 844) - nav.top)) };
  });
  const screenText = await page.evaluate(() => document.body.innerText);
  const tokens = screenText.match(/\b[A-Z][A-Z0-9]{1,}(_[A-Z0-9]+)+\b/g) || [];
  const rec = { base: BASE, cells, afterScroll, screaming_snake_hits: tokens.length, screaming_snake_tokens: tokens.slice(0, 20) };
  fs.writeFileSync(OUT, JSON.stringify(rec, null, 1));
  console.log(JSON.stringify(rec));
  await browser.close();
})();
