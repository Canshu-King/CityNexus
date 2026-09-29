/* ORD-0473 desktop arm (1280x720): the mobile toggle must stay out of the way and the sidebar nav
   must still change the screen.  Readings are rendered text + elementFromPoint, per row. */
const { chromium } = require("D:\\moodle\\CityNexus\\frontend\\node_modules\\playwright");
const fs = require("fs");
const BASE = process.argv[2], OUT = process.argv[3];
(async () => {
  const browser = await chromium.launch();
  const ctx = await browser.newContext({ viewport: { width: 1280, height: 720 }, deviceScaleFactor: 1 });
  const page = await ctx.newPage();
  const errors = [];
  page.on("pageerror", (e) => errors.push(String(e).slice(0, 300)));
  await page.goto(BASE + "/v8/hub", { waitUntil: "load" });
  await page.waitForTimeout(4000);
  if (await page.locator('[data-testid="trial-setup"]').count()) {
    await page.locator('[data-testid="trial-tianjin-demo"]').click({ timeout: 10000 }).catch(() => {});
    await page.waitForTimeout(4000);
  }
  const rec = { base: BASE, viewport: [1280, 720], errors };
  rec.toggle = await page.evaluate(() => {
    const m = document.querySelector(".v8-mobile-menu");
    if (!m) return { present: false };
    const r = m.getBoundingClientRect();
    return { present: true, display: getComputedStyle(m).display, box: { w: Math.round(r.width), h: Math.round(r.height) } };
  });
  rec.drawer_open_at_desktop = await page.evaluate(() => !!document.querySelector("#v8-nav-drawer"));
  rec.sidebar = [];
  const rows = await page.locator(".v8-sidebar nav button").all();
  rec.sidebar_row_count = rows.length;
  for (let i = 0; i < Math.min(4, rows.length); i++) {
    const row = rows[i];
    const label = (await row.textContent() || "").replace(/\s+/g, " ").trim();
    const geo = await row.evaluate((el) => {
      const r = el.getBoundingClientRect();
      const cx = r.left + r.width / 2, cy = r.top + r.height / 2;
      const top = document.elementFromPoint(cx, cy);
      return { box: { x: Math.round(r.x), y: Math.round(r.y), w: Math.round(r.width), h: Math.round(r.height) },
               hit_is_self: top === el || (top !== null && el.contains(top)) };
    });
    const before = await page.evaluate(() => ({ p: location.pathname, h: (document.querySelector("h1, h2") || {}).innerText || null }));
    let err = null;
    try { await row.click({ timeout: 6000 }); } catch (e) { err = String(e).split("\n")[0].slice(0, 160); }
    await page.waitForTimeout(1600);
    const after = await page.evaluate(() => ({ p: location.pathname, h: (document.querySelector("h1, h2") || {}).innerText || null }));
    rec.sidebar.push({ i, label: label.slice(0, 24), ...geo, error: err, before, after, changed: before.p !== after.p || before.h !== after.h });
  }
  fs.writeFileSync(OUT, JSON.stringify(rec, null, 1));
  console.log(JSON.stringify(rec, null, 1).slice(0, 2500));
  await browser.close();
})();
