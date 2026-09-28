/* CMDR ORD-0419 premise instrument r1 - is every drawer row reachable by scrolling the drawer itself?
 * Lane 2d2d7428 left me a binary at 320x653 ("10 rows need a 725px visible stack").  That question is only
 * worth asking if the drawer's own scroll does NOT reach the tail.  This sweeps `#v8-nav-drawer`.scrollTop
 * across its whole range in every shape and hit-tests each row's own centre at every offset:
 *   reachableAtTop / reachableAtBottom  = what is hittable without sweeping
 *   reachableSomewhere                  = union over the whole scroll range  <- the load-bearing number
 * A row counts only when elementFromPoint at its centre lands on itself (or a descendant) AND its box is
 * fully inside the viewport, so a row hidden behind the topbar or clipped at the bottom does not count.
 * Usage: node cmdr_drawer_reach_sweep_r1.js <base> <out-file> [locale]
 */
const { chromium } = require("D:/moodle/CityNexus/frontend/node_modules/playwright");
const fs = require("fs");

const BASE = process.argv[2] || "http://127.0.0.1:4805/";
const OUT = process.argv[3] || "D:/moodle/_qoder_cmdr_ref_20260921/live_checks/_drawer_reach_sweep_r1.json";
const LOCALE = process.argv[4] || "zh";
const SHAPES = [[320, 653], [360, 800], [390, 844], [414, 896]];

async function main() {
  const browser = await chromium.launch({ channel: "chrome", headless: true });
  const shapes = {};
  let entryAssets = null;
  for (const [w, h] of SHAPES) {
    const ctx = await browser.newContext({ viewport: { width: w, height: h }, hasTouch: true, locale: LOCALE });
    const page = await ctx.newPage();
    await page.goto(BASE, { waitUntil: "networkidle", timeout: 90000 });
    if (!entryAssets) {
      entryAssets = await page.evaluate(() =>
        Array.from(document.querySelectorAll('script[src*="assets/index-"]')).map((s) => s.getAttribute("src")));
    }
    const seal = page.getByText("使用封存的演示行程", { exact: false }).first();
    const sealEn = page.getByText(/sealed demo trip/i).first();
    let sealClicked = null;
    for (const cand of [seal, sealEn]) {
      if (await cand.count()) {
        sealClicked = (await cand.textContent() || "").trim().slice(0, 40);
        await cand.click();
        await page.waitForTimeout(4000);
        break;
      }
    }
    const ham = page.locator('[aria-controls="v8-nav-drawer"]');
    if (await ham.count()) { await ham.first().click(); await page.waitForTimeout(1000); }
    const shape = await page.evaluate(async () => {
      const d = document.querySelector("#v8-nav-drawer");
      if (!d) return { error: "DRAWER_NOT_FOUND" };
      const rows = Array.from(d.querySelectorAll("button")).filter((x) => x.querySelector("svg"));
      const probe = () => rows.map((x) => {
        const r = x.getBoundingClientRect();
        const cx = Math.round(r.left + r.width / 2), cy = Math.round(r.top + r.height / 2);
        const t = document.elementFromPoint(cx, cy);
        return { ok: !!(t && x.contains(t)) && r.top >= 0 && r.bottom <= window.innerHeight };
      });
      const at = async (y) => { d.scrollTop = y; await new Promise((r) => setTimeout(r, 150)); return probe(); };
      const reachableAtTop = (await at(0)).filter((r) => r.ok).length;
      const reachableAtBottom = (await at(d.scrollHeight)).filter((r) => r.ok).length;
      const seen = new Set();
      const offsets = [];
      for (let y = 0; y <= d.scrollHeight; y += 120) {
        offsets.push(y);
        (await at(y)).forEach((r, i) => { if (r.ok) seen.add(i); });
      }
      return {
        rows: rows.length,
        scrollHeightPx: d.scrollHeight,
        clientHeightPx: d.clientHeight,
        overflowY: getComputedStyle(d).overflowY,
        offsetsWalked: offsets.length,
        reachableAtTop,
        reachableAtBottom,
        reachableSomewhere: seen.size,
        unreachableLabels: rows.filter((x, i) => !seen.has(i)).map((x) => (x.textContent || "").trim()),
        verdict: seen.size === rows.length ? "ALL_ROWS_REACHABLE_BY_DRAWER_SCROLL" : "SOME_ROWS_UNREACHABLE",
      };
    });
    shape.sealClickedText = sealClicked;
    shapes[`${w}x${h}`] = shape;
    await ctx.close();
  }
  await browser.close();
  const report = { instrument: "cmdr_drawer_reach_sweep_r1", base: BASE, locale: LOCALE, entryAssets, shapes };
  fs.writeFileSync(OUT, JSON.stringify(report, null, 2));
  console.log(JSON.stringify({ out: OUT, entryAssets, shapes }, null, 2));
}

main().catch((e) => { console.error("FATAL", e); process.exit(1); });
