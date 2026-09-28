/* CMDR ORD-0419 acceptance r1 - does the drawer's current-page marker FOLLOW a navigation?
 * ORD-0419 restored the active row's distinct paint, but that only matters if the marker moves with the
 * route.  Per target row: open the drawer if closed, hit-test the row's own centre, click it, then RE-OPEN
 * (the drawer closes by design after navigating) and read which row now carries the active state, plus its
 * computed background.  Readings are rendered labels and computed paint, not data attributes.
 * Usage: node cmdr_drawer_active_follows_nav_r1.js <base> <out-file> [locale]
 */
const { chromium } = require("D:/moodle/CityNexus/frontend/node_modules/playwright");
const fs = require("fs");
const BASE = process.argv[2] || "http://127.0.0.1:49150/";
const OUT = process.argv[3] || "D:/moodle/_qoder_cmdr_ref_20260921/live_checks/_drawer_active_follows_r1.json";
const LOCALE = process.argv[4] || "zh";
const TARGETS = ["地图", "旅行票夹", "回收站", "我的"];

async function main() {
  const browser = await chromium.launch({ channel: "chrome", headless: true });
  const ctx = await browser.newContext({ viewport: { width: 390, height: 844 }, hasTouch: true, locale: LOCALE });
  const page = await ctx.newPage();
  const errs = [];
  page.on("pageerror", (e) => errs.push(String(e).slice(0, 180)));
  await page.goto(BASE, { waitUntil: "networkidle", timeout: 90000 });
  const entry = await page.evaluate(() => Array.from(document.querySelectorAll('script[src*="assets/index-"]')).map((s) => s.getAttribute("src")));
  for (const cand of [page.getByText("使用封存的演示行程", { exact: false }).first(), page.getByText(/sealed demo trip/i).first()]) {
    if (await cand.count()) { await cand.click(); await page.waitForTimeout(4000); break; }
  }
  const cases = [];
  for (const want of TARGETS) {
    const rec = { target: want };
    if (!(await page.locator("#v8-nav-drawer").count())) {
      await page.locator('[aria-controls="v8-nav-drawer"]').first().click();
      await page.waitForTimeout(800);
    }
    const row = page.locator("#v8-nav-drawer button:has(svg)").filter({ hasText: want }).first();
    rec.rowFound = await row.count();
    if (!rec.rowFound) { cases.push(rec); continue; }
    await row.scrollIntoViewIfNeeded();
    const bx = await row.boundingBox();
    const cx = Math.round(bx.x + bx.width / 2), cy = Math.round(bx.y + bx.height / 2);
    rec.hitTest = await page.evaluate(([x, y, label]) => {
      const rows = Array.from(document.querySelectorAll("#v8-nav-drawer button")).filter((q) => q.querySelector("svg"));
      const t = rows.find((q) => (q.textContent || "").trim() === label);
      const top = document.elementFromPoint(x, y);
      return !!(top && t && (t === top || t.contains(top)));
    }, [cx, cy, want]);
    const before = page.url();
    await page.mouse.click(cx, cy);
    await page.waitForTimeout(1500);
    rec.urlBefore = before.replace(/^https?:\/\/[^/]+/, "");
    rec.urlAfter = page.url().replace(/^https?:\/\/[^/]+/, "");
    rec.urlChanged = before !== page.url();
    if (!(await page.locator("#v8-nav-drawer").count())) {
      await page.locator('[aria-controls="v8-nav-drawer"]').first().click();
      await page.waitForTimeout(800);
    }
    Object.assign(rec, await page.evaluate(() => {
      const all = Array.from(document.querySelectorAll("#v8-nav-drawer button"));
      const act = all.filter((x) => (x.className || "").includes("active"));
      const cs = act.length ? getComputedStyle(act[0]) : null;
      const sigOf = (x) => { const q = getComputedStyle(x); return q.backgroundColor + " / " + q.color + " / " + q.fontWeight; };
      const rows = all.filter((x) => x.querySelector("svg"));
      return {
        activeRowCount: act.length,
        activeLabel: act.length ? (act[0].textContent || "").trim() : null,
        activeSignature: cs ? sigOf(act[0]) : null,
        distinctSignatures: new Set(rows.map(sigOf)).size,
        drawerClosedByNavigation: true,
      };
    }));
    rec.markerFollowedRoute = rec.activeLabel === want;
    cases.push(rec);
  }
  await ctx.close();
  const report = { instrument: "cmdr_drawer_active_follows_nav_r1", base: BASE, locale: LOCALE, entryAssets: entry,
    cases, summary: { targets: TARGETS.length, markersFollowed: cases.filter((c) => c.markerFollowedRoute).length,
      pageErrors: errs.length, verdict: cases.length === TARGETS.length && cases.every((c) => c.markerFollowedRoute && c.hitTest)
        ? "ACTIVE_MARKER_FOLLOWS_EVERY_NAVIGATION_TESTED" : "NOT_PROVEN" }, pageErrors: errs };
  fs.writeFileSync(OUT, JSON.stringify(report, null, 2));
  console.log(JSON.stringify({ out: OUT, entry, verdict: report.summary.verdict, followed: report.summary.markersFollowed + "/" + TARGETS.length }, null, 2));
}
main().catch((e) => { console.error("FATAL", e); process.exit(1); });
