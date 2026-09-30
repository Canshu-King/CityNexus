/* ORD-0489 · one-variable test: does visiting /v8/discover write catalogue rows?
 *
 * The seeded board read back 8 places in CN-TIANJIN and 4 in CN-BEIJING.  After a browser pass
 * that walked all sixteen routes the same two doors answer 15 and 12.  This presses exactly one
 * route and measures the delta, so the claim names its own variable instead of blaming the walk.
 */
const { chromium } = require("playwright");
const fs = require("fs");
const path = require("path");

const PREVIEW = process.env.CNX_PREVIEW || "http://127.0.0.1:8791";
const BACKEND = process.env.CNX_BACKEND || "http://127.0.0.1:8790";
const OUT = "D:/moodle/_qoder_seed_ord0489/evidence/ord0489_screens";

const counts = async () => {
  const out = {};
  for (const city of ["CN-TIANJIN", "CN-BEIJING", "CN-FUZHOU"]) {
    const rows = await (await fetch(`${BACKEND}/api/v1/places?city_code=${city}`)).json();
    out[city] = rows.length;
  }
  for (const [key, url] of [
    ["journeys", `${BACKEND}/api/v1/journeys`],
    ["candidates", `${BACKEND}/api/v1/journeys/${JOURNEY}/provider-mesh`],
    ["hydrations", `${BACKEND}/api/v1/catalog-hydrations`],
  ]) {
    const res = await fetch(url);
    out[key] = { status: res.status, len: res.ok ? (await res.json()).length ?? null : null };
  }
  return out;
};

let JOURNEY = null;

(async () => {
  const journeys = await (await fetch(`${BACKEND}/api/v1/journeys`)).json();
  JOURNEY = journeys.find((j) => j.city_code === "CN-TIANJIN").id;
  const report = { preview: PREVIEW, journey_id: JOURNEY, started_at: new Date().toISOString() };
  report.before = await counts();

  const browser = await chromium.launch();
  const ctx = await browser.newContext({ viewport: { width: 390, height: 844 }, hasTouch: true, isMobile: true, locale: "zh-CN" });
  const page = await ctx.newPage();
  await page.goto(`${PREVIEW}/v8/${JOURNEY}`, { waitUntil: "domcontentloaded" });
  await page.waitForTimeout(2200);
  await page.goto(`${PREVIEW}/v8/discover`, { waitUntil: "domcontentloaded" });
  await page.waitForTimeout(6000);
  report.after_discover_route = await counts();
  report.discover_screen_testids = await page.evaluate(() =>
    Array.from(document.querySelectorAll("[data-testid]")).map((el) => el.getAttribute("data-testid")).filter((t) => /discover|real-city|hydrat|prepar/i.test(t))
  );
  report.outgoing_requests = await page.evaluate(() =>
    performance.getEntriesByType("resource").map((e) => e.name).filter((n) => /api\/v1/.test(n)).slice(-25)
  );
  const file = path.join(OUT, "discover_screen_r6.png");
  await page.screenshot({ path: file, fullPage: true });
  report.shot = { file: file.replace(/\\/g, "/"), bytes: fs.statSync(file).size };

  /* the control: a route that must not touch the catalogue */
  await page.goto(`${PREVIEW}/v8/trips`, { waitUntil: "domcontentloaded" });
  await page.waitForTimeout(6000);
  report.after_control_route = await counts();
  await ctx.close();
  await browser.close();
  report.finished_at = new Date().toISOString();
  const stamp = report.finished_at.replace(/[-:]/g, "").slice(0, 13);
  const out = path.join(OUT, `discover_write_side_effect_r6_${stamp}.json`);
  fs.writeFileSync(out, JSON.stringify(report, null, 1), "utf-8");
  console.log(JSON.stringify({ evidence: out.replace(/\\/g, "/"), before: report.before, after: report.after_discover_route }));
})().catch((exc) => {
  console.error("R6_FAILED", exc && exc.message ? exc.message : exc);
  process.exit(1);
});
