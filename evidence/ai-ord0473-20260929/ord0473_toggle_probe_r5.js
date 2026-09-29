// ORD-0473, two open questions measured rather than assumed:
//  1) with the drawer open, is the 菜单 button still reachable (the order asks that it 开关 the drawer)?
//  2) how many of the drawer's own nodes carry a data-testid -- the number the blocking report used as
//     its only witness ("可见 testid 枚数 47 -> 47").
const { chromium } = require("D:/moodle/CityNexus/frontend/node_modules/playwright");
const BASE = process.argv[2] || "http://127.0.0.1:4870";
const ENTRY = ["使用封存的演示行程", "sealed demo", "封存演示"];
(async () => {
  const b = await chromium.launch();
  const ctx = await b.newContext({ viewport: { width: 390, height: 844 } });
  const page = await ctx.newPage();
  await page.goto(BASE + "/", { waitUntil: "domcontentloaded", timeout: 60000 }).catch(() => {});
  await page.evaluate(() => localStorage.setItem("citynexus.locale", "zh-CN"));
  await page.goto(BASE + "/v8/hub", { waitUntil: "domcontentloaded", timeout: 60000 }).catch(() => {});
  for (const l of ENTRY) { const loc = page.getByText(l, { exact: false }).first(); if (await loc.count()) { await loc.click({ timeout: 8000 }).catch(() => {}); await page.waitForTimeout(2500); break; } }
  await page.goto(BASE + "/v8/hub", { waitUntil: "domcontentloaded", timeout: 60000 }).catch(() => {});
  await page.waitForTimeout(3000);
  const centre = await page.evaluate(() => { const m = Array.from(document.querySelectorAll("button")).find((e) => (e.textContent || "").trim() === "菜单"); const r = m.getBoundingClientRect(); return [Math.round(r.left + r.width / 2), Math.round(r.top + r.height / 2)]; });
  const closed = await page.evaluate(() => ({ testids: document.querySelectorAll("[data-testid]").length, drawer: !!document.querySelector("#v8-nav-drawer") }));
  await page.mouse.click(centre[0], centre[1]);
  await page.waitForTimeout(1200);
  const open = await page.evaluate((c) => {
    const nav = document.querySelector("#v8-nav-drawer");
    const at = document.elementFromPoint(c[0], c[1]);
    const inDrawer = !!(nav && at && nav.contains(at));
    return {
      testids: document.querySelectorAll("[data-testid]").length,
      visible_testids: Array.from(document.querySelectorAll("[data-testid]")).filter((e) => { const r = e.getBoundingClientRect(); return r.width > 0 && r.height > 0; }).length,
      drawer_testids: nav ? nav.querySelectorAll("[data-testid]").length : null,
      entry_count: nav ? nav.querySelectorAll("button,a").length : null,
      entries_with_testid: nav ? Array.from(nav.querySelectorAll("button,a")).filter((e) => e.hasAttribute("data-testid")).length : null,
      hit_at_menu_centre_while_open: at ? at.tagName + "." + String(at.className || "").slice(0, 22) : "none",
      menu_button_is_under_drawer: inDrawer,
      aria_expanded: (Array.from(document.querySelectorAll("button")).find((e) => (e.textContent || "").trim() === "菜单") || {}).getAttribute ? document.querySelector(".v8-mobile-menu").getAttribute("aria-expanded") : null,
    };
  }, centre);
  // second press at the same point while open
  await page.mouse.click(centre[0], centre[1]);
  await page.waitForTimeout(1000);
  const after2nd = await page.evaluate(() => ({ drawer_still_open: !!document.querySelector("#v8-nav-drawer") }));
  console.log(JSON.stringify({ centre, closed, open, after2nd }, null, 1));
  await b.close();
})();
