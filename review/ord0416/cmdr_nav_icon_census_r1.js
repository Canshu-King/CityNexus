/* CMDR ORD-0416 r1 -- four shapes x two arms, before and after, on the product's own CSS.
 *
 * Reuses cmdr_drawer_cause_probe_r1.js's 口径 (lane N3's hit floor: elementFromPoint(centre) inside the
 * row AND centre.y <= 768) and adds what ORD-0416 asks for:
 *   - four shapes: 390x844, 360x800, 320x653, 414x896, each with a zh arm and an en arm;
 *   - rows_within_floor per shape (acceptance: not below 10 -- reported per shape, not averaged);
 *   - overflow_px before/after;
 *   - the oversized-icon census the commander's own sweep uses: every <svg> whose rendered box is
 *     taller than 60px, counted per route with the drawer closed AND with it open. The before arm must
 *     show 14 in the drawer and 0 everywhere else; the after arm must show 0.
 *
 * Nothing is injected here: unlike the probe, this reads the shipped stylesheet, so what it measures is
 * what a traveller's browser would do.
 *
 * Usage: node cmdr_ordinary_icons_r1.js <base> <out-dir> <label>
 */
const { chromium } = require("D:/moodle/CityNexus/frontend/node_modules/playwright");
const fs = require("fs");

const BASE = (process.argv[2] || "http://127.0.0.1:50991/").replace(/\/$/, "");
const OUT = process.argv[3] || "D:/moodle/_qoder_q_ord0416_20260928/probe/_arms_r1/";
const LABEL = process.argv[4] || "unlabelled";
const FLOOR = 768;
const SHAPES = [[390, 844], [360, 800], [320, 653], [414, 896]];
const LOCALES = ["zh-CN", "en"];
/* The 13 routes the commander swept, plus the bare hub. Read from routes/v8Routes.ts, not invented. */
const ROUTES = ["hub", "live", "map", "studio", "stay", "discover", "bookings", "agent",
                "authoritative", "intelligence", "twin", "trash", "trips", "me"];

async function sweep(page) {
  return page.evaluate((floor) => {
    const big = Array.from(document.querySelectorAll("svg"))
      .map((s) => ({ w: Math.round(s.getBoundingClientRect().width),
                     h: Math.round(s.getBoundingClientRect().height),
                     parent: s.parentElement ? s.parentElement.tagName : null,
                     in_drawer: !!s.closest("#v8-nav-drawer") }))
      .filter((x) => x.h > 60);
    const d = document.querySelector("#v8-nav-drawer");
    let rows = [];
    if (d) {
      rows = Array.from(d.querySelectorAll(":scope > div > button")).slice(1).map((b) => {
        const r = b.getBoundingClientRect();
        const c = [Math.round(r.x + r.width / 2), Math.round(r.y + r.height / 2)];
        const top = document.elementFromPoint(c[0], c[1]);
        return { h: Math.round(r.height), centre: c,
                 hittable: !!(top && (b.contains(top) || b === top)), above_floor: c[1] <= floor };
      });
    }
    return { oversized_total: big.length, oversized_in_drawer: big.filter((x) => x.in_drawer).length,
             oversized_parents: Array.from(new Set(big.map((x) => x.parent))),
             oversized_box: big.length ? [big[0].w, big[0].h] : null,
             drawer_present: !!d,
             drawer_scroll: d ? d.scrollHeight : null,
             drawer_client: d ? d.clientHeight : null,
             drawer_overflow: d ? d.scrollHeight - d.clientHeight : null,
             drawer_rows: rows.length,
             rows_within_floor: rows.filter((r) => r.hittable && r.above_floor).length,
             row_height: rows.length ? rows[0].h : null };
  }, FLOOR);
}

async function run(browser, shape, locale) {
  const [w, h] = shape;
  const page = await browser.newPage({ viewport: { width: w, height: h } });
  const errors = [];
  page.on("pageerror", (e) => errors.push(String(e).slice(0, 200)));
  const rec = { label: LABEL, shape: `${w}x${h}`, arm: locale, hit_floor_px: FLOOR, errors };
  try {
    await page.goto(`${BASE}/v8/hub`, { waitUntil: "networkidle", timeout: 60000 });
    const seal = page.getByText("使用封存的演示行程", { exact: false }).first();
    if (await seal.count()) { await seal.click(); await page.waitForTimeout(3200); }
    const lang = page.locator("[data-testid='topbar-language']").first();
    const offered = (await lang.innerText()).trim();
    if ((locale === "en") === (offered === "EN")) { await lang.click(); await page.waitForTimeout(1200); }
    rec.routes_closed = {};
    for (const r of ROUTES) {
      await page.goto(`${BASE}/v8/${r}`, { waitUntil: "networkidle", timeout: 60000 });
      await page.waitForTimeout(700);
      rec.routes_closed[r] = await sweep(page);
    }
    await page.goto(`${BASE}/v8/hub`, { waitUntil: "networkidle", timeout: 60000 });
    await page.waitForTimeout(900);
    await page.locator("[aria-controls='v8-nav-drawer']").first().click();
    await page.waitForTimeout(900);
    rec.drawer_open = await sweep(page);
    await page.screenshot({ path: `${OUT}${LABEL}_${w}x${h}_${locale}.png` });
  } catch (e) {
    rec.fatal = String(e).slice(0, 200);
  }
  rec.errors = errors;
  await page.close();
  const d = rec.drawer_open || {};
  const route_hits = Object.entries(rec.routes_closed || {}).filter(([, v]) => v.oversized_total > 0)
    .map(([k, v]) => `${k}=${v.oversized_total}`);
  console.log("%s %s %s  drawer: rows=%s within_floor=%s row_h=%s scroll=%s overflow=%s | oversized drawer=%s closed_routes_with_hits=%s | err=%s%s",
              LABEL, rec.shape, rec.arm, d.drawer_rows, d.rows_within_floor, d.row_height,
              d.drawer_scroll, d.drawer_overflow, d.oversized_in_drawer,
              route_hits.length ? route_hits.join(",") : "none", rec.errors.length,
              rec.fatal ? " FATAL=" + rec.fatal.slice(0, 90) : "");
  return rec;
}

async function main() {
  fs.mkdirSync(OUT, { recursive: true });
  const browser = await chromium.launch({ channel: "chrome", headless: true });
  const results = [];
  for (const shape of SHAPES) for (const locale of LOCALES) results.push(await run(browser, shape, locale));
  const path = `${OUT}${LABEL}.receipt.json`;
  fs.writeFileSync(path, JSON.stringify({ at: new Date().toISOString(), base: BASE, label: LABEL,
                                          hit_floor_px: FLOOR, shapes: SHAPES, results }, null, 1), "utf-8");
  console.log("wrote", path);
  await browser.close();
}
main().catch((e) => { console.log("FATAL", String(e).slice(0, 300)); process.exit(9); });
