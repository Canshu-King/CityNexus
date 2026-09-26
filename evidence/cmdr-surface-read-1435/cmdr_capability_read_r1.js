/* Commander's attribution read for the destination panel's SERVER_ERROR on the deployed phone chain.

Why: my click-read (cmdr_click_read_r1.js) shows the panel putting 北京 under "没读到 / SERVER_ERROR",
while the SAME route answered HTTP 200 with a real payload when I asked it directly with urllib
through :4782 (北京 -> capability HYDRATABLE / COVERAGE_INCOMPLETE).  Those two readings can only be
reconciled by looking at what the BROWSER actually received, so this instrument records every
response whose URL contains /destinations/capability: status, content-type, who served it
(service worker or network), and the first 180 characters of the body.

It never prints credentials and never sends an Authorization header: the proxy's Basic gate is
satisfied the same way a visitor's is -- by the cookie the proxy already set for this browser.

usage: node cmdr_capability_read_r1.js [--base http://127.0.0.1:4781] [--out file.json]
*/
const path = require("path");
const fs = require("fs");
const NM = "D:/moodle/CityNexus/frontend/node_modules";
const { chromium, devices } = require(path.join(NM, "playwright"));

const arg = (k, d) => {
  const i = process.argv.indexOf(k);
  return i > 0 && process.argv[i + 1] ? process.argv[i + 1] : d;
};
const BASE = arg("--base", "http://127.0.0.1:4781");
const OUT = arg("--out", "patrol/capability_read_r1.json");

(async () => {
  const browser = await chromium.launch();
  const ctx = await browser.newContext({ ...devices["Pixel 5"], locale: "zh-CN" });
  const page = await ctx.newPage();
  const rows = [];
  const failures = [];

  page.on("response", async (res) => {
    const url = res.url();
    if (!url.includes("/destinations/capability")) return;
    let head = null, size = null, jsonShape = null;
    try {
      const body = await res.body();
      size = body.length;
      head = body.toString("utf8").slice(0, 180);
      try {
        const j = JSON.parse(body.toString("utf8"));
        jsonShape = { has_capability: "capability" in j, query: j.query ?? null,
                     capability: j.capability ?? null, reason_code: j.reason_code ?? null };
      } catch (e) { jsonShape = { parse_error: String(e).slice(0, 60) }; }
    } catch (e) { head = "<body unreadable: " + String(e).slice(0, 60) + ">"; }
    let fromSW = null;
    try { fromSW = res.fromServiceWorker(); } catch (e) { fromSW = "unknown"; }
    rows.push({ url: url.replace(BASE, ""), status: res.status(),
                content_type: res.headers()["content-type"] ?? null,
                served_by_service_worker: fromSW, body_bytes: size,
                json_shape: jsonShape, body_head: head });
  });
  page.on("requestfailed", (req) => {
    if (req.url().includes("/destinations/capability")) {
      failures.push({ url: req.url().replace(BASE, ""), failure: req.failure() && req.failure().errorText });
    }
  });

  const out = { base: BASE, responses: rows, request_failures: failures };
  try {
    await page.goto(BASE + "/", { waitUntil: "networkidle", timeout: 60000 });
    await page.waitForTimeout(2500);
    const toggle = page.getByText("看支持的目的地", { exact: false }).first();
    if (await toggle.count()) {
      await toggle.click({ timeout: 8000 });
      await page.waitForTimeout(6000);          // let every per-city read land
    }
    out.panel_text = (await page.locator("body").innerText().catch(() => "")).replace(/\s+/g, " ").slice(0, 900);
    out.sw_registrations = await page.evaluate(async () => {
      if (!("serviceWorker" in navigator)) return "no sw api";
      const rs = await navigator.serviceWorker.getRegistrations();
      return rs.map(r => ({ scope: r.scope, state: r.active ? r.active.state : "none" }));
    }).catch(e => "eval failed: " + String(e).slice(0, 80));
    out.caches = await page.evaluate(async () => {
      if (!("caches" in window)) return "no caches api";
      return (await caches.keys());
    }).catch(e => "eval failed: " + String(e).slice(0, 80));
  } catch (e) {
    out.error = String(e).slice(0, 200);
  } finally {
    const ok = rows.filter(r => r.status === 200 && r.json_shape && r.json_shape.has_capability);
    out.verdict = rows.length === 0 ? "NO_CAPABILITY_CALL_OBSERVED"
      : ok.length === rows.length ? "ALL_JSON_200"
      : "SOME_LEG_FAILED";
    out.counts = { observed: rows.length, json_200: ok.length, failed: failures.length };
    fs.mkdirSync(path.dirname(OUT), { recursive: true });
    fs.writeFileSync(OUT, JSON.stringify(out, null, 1));
    console.log(JSON.stringify({ verdict: out.verdict, counts: out.counts,
                                 error: out.error ?? null }, null, 1));
    for (const r of rows) {
      console.log(" -", r.status, r.content_type, "sw=" + r.served_by_service_worker,
                  r.body_bytes + "B", String(r.url).slice(0, 60));
    }
    for (const f of failures) console.log(" FAILED", f.url, f.failure);
    console.log("out = " + OUT);
    await browser.close();
  }
})();
