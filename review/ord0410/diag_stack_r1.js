/* ORD-0410 lane diagnostic — what does this stack actually paint on /v8/map, and which API calls
 * answered what.  The r5 instrument reports `state:null` / 0 markers here, which is "the screen
 * never rendered", not "the button is inert"; the two must not be conflated, so this reads the
 * page's own text and the /api/* receipts.
 * Usage: node _diag_stack_r1.js <base> <out-dir>
 */
const { chromium } = require("D:/moodle/CityNexus/frontend/node_modules/playwright");
const fs = require("fs");
const BASE = process.argv[2] || "http://127.0.0.1:4811/";
const OUT = process.argv[3] || "D:/moodle/_qoder_r_ord0410/run/_diag/";
fs.mkdirSync(OUT, { recursive: true });

const snap = (p, tag) => p.evaluate(() => ({
  url: location.pathname,
  testids: Array.from(document.querySelectorAll("[data-testid]")).map((e) => e.getAttribute("data-testid")).slice(0, 60),
  buttons: Array.from(document.querySelectorAll("button")).map((b) => (b.innerText || b.getAttribute("aria-label") || "").trim()).filter(Boolean).slice(0, 30),
  bodyChars: (document.body.innerText || "").length,
  bodyHead: (document.body.innerText || "").replace(/\s+/g, " ").slice(0, 700),
  journeyId: localStorage.getItem("citynexus.v8.journey_id"),
})).then((s) => ({ tag, ...s }));

(async () => {
  const br = await chromium.launch({ channel: "chrome", headless: true });
  const p = await br.newPage({ viewport: { width: 390, height: 844 } });
  const errs = [], api = [];
  p.on("pageerror", (e) => errs.push(String(e).slice(0, 200)));
  p.on("response", async (r) => {
    const u = r.url();
    if (!u.includes("/api/")) return;
    let n = null;
    try { n = (await r.text()).length; } catch { n = -1; }
    api.push({ url: u.replace(BASE, "").slice(0, 120), status: r.status(), bytes: n });
  });
  await p.goto(BASE, { waitUntil: "networkidle", timeout: 60000 });
  await p.waitForTimeout(3000);
  const steps = [await snap(p, "landing")];
  const seal = p.getByText("使用封存的演示行程", { exact: false }).first();
  steps.push({ tag: "seal_present", count: await seal.count() });
  if (await seal.count()) { await seal.click(); await p.waitForTimeout(6000); steps.push(await snap(p, "after_seal")); }
  await p.goto(BASE.replace(/\/$/, "") + "/v8/map", { waitUntil: "networkidle", timeout: 60000 });
  await p.waitForTimeout(6000);
  steps.push(await snap(p, "v8_map"));
  await p.screenshot({ path: OUT + "v8_map.png" });
  const rec = { at: new Date().toISOString(), base: BASE, steps, api, pageerrors: errs };
  fs.writeFileSync(OUT + "diag.json", JSON.stringify(rec, null, 1), "utf-8");
  console.log(JSON.stringify(rec, null, 1).slice(0, 4000));
  await br.close();
})().catch((e) => { console.log("FATAL", String(e).slice(0, 300)); process.exit(9); });
