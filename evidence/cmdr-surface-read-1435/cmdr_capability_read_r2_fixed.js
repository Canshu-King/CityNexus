/* Commander's attribution read, revision r2 -- same question as r1, asked on the surface a traveller
   actually opens.

Why r2 exists (measured 2026-09-26 14:33 with r1 against `http://127.0.0.1:4781`): eleven capability
calls all came back HTTP 500 / text/plain / 0 B, NOT from the service worker, while the identical
request I sent myself to the auth proxy `http://127.0.0.1:4782` answered HTTP 200 with a real payload
(北京 -> HYDRATABLE / COVERAGE_INCOMPLETE, 贡山 -> unresolved + NO_CANONICAL_IDENTITY).  The two
readings are not a contradiction about the product: :4781 is vite preview, whose /api proxy targets
the default backend port unless CITYNEXUS_BACKEND_PORT is given, and that port is deliberately not
served -- so the 500 is the proxy answering for a refused upstream, the shape already documented in
ORD-0263.  Judging the user's screen on :4781 therefore judges a surface the user does not open.

r2 drives the proxy surface with the Basic credentials read from the auth FILE (values never printed),
and prints only status / content-type / byte length / the two fields the panel actually reads.

usage: node cmdr_capability_read_r2.js --base http://127.0.0.1:4782 \
        --auth-file D:/moodle/_qoder_preview_20260920/run/preview_auth.txt --out file.json
*/
const path = require("path");
const fs = require("fs");
const NM = "D:/moodle/CityNexus/frontend/node_modules";
const { chromium, devices } = require(path.join(NM, "playwright"));

const arg = (k, d) => {
  const i = process.argv.indexOf(k);
  return i > 0 && process.argv[i + 1] ? process.argv[i + 1] : d;
};
const BASE = arg("--base", "http://127.0.0.1:4782");
const AUTH_FILE = arg("--auth-file", "D:/moodle/_qoder_preview_20260920/run/preview_auth.txt");
const OUT = arg("--out", "patrol/capability_read_r2.json");

// TAB-separated user/secret, exactly how the proxy's own loader parses it.  Consumed in-process;
// never echoed, never written to the receipt.
function credentials() {
  const raw = fs.readFileSync(AUTH_FILE, "utf8").trim().split("\t");
  if (raw.length < 2) throw new Error("AUTH_FILE_SHAPE_UNEXPECTED names=" + raw.length);
  return { username: raw[0], password: raw[1] };
}

(async () => {
  const browser = await chromium.launch();
  const ctx = await browser.newContext({
    ...devices["Pixel 5"], locale: "zh-CN", httpCredentials: credentials(),
  });
  const page = await ctx.newPage();
  const rows = [];
  const failures = [];

  page.on("response", async (res) => {
    const url = res.url();
    if (!url.includes("/destinations/capability")) return;
    let head = null, size = null, shape = null;
    try {
      const body = await res.body();
      size = body.length;
      head = body.toString("utf8").slice(0, 150);
      try {
        const j = JSON.parse(body.toString("utf8"));
        shape = { query: j.query ?? null, capability: j.capability ?? null,
                  reason_code: j.reason_code ?? null };
      } catch (e) { shape = { parse_error: true }; }
    } catch (e) { head = "<unreadable>"; }
    let fromSW = null;
    try { fromSW = res.fromServiceWorker(); } catch (e) { fromSW = "unknown"; }
    // decode FIRST, then truncate: cutting a percent-encoded string mid-escape throws URIError,
    // and the first version of this arm died on that before printing anything.
    let label = (url.split("query=")[1] || "").slice(0, 40);
    try { label = decodeURIComponent(label); } catch (e) { /* leave the raw prefix */ }
    rows.push({ status: res.status(), content_type: res.headers()["content-type"] ?? null,
                served_by_service_worker: fromSW, body_bytes: size,
                shape, query_in_url: label.slice(0, 20) });
  });
  page.on("requestfailed", (req) => {
    if (req.url().includes("/destinations/capability")) {
      failures.push({ url: req.url(), failure: req.failure() && req.failure().errorText });
    }
  });

  const out = { base: BASE, surface: "auth proxy (the surface the phone opens)",
                responses: rows, request_failures: failures };
  try {
    await page.goto(BASE + "/", { waitUntil: "networkidle", timeout: 90000 });
    await page.waitForTimeout(3000);
    const toggle = page.getByText("看支持的目的地", { exact: false }).first();
    if (await toggle.count()) {
      await toggle.click({ timeout: 10000 });
      await page.waitForTimeout(8000);
    }
    out.first_paint = (await page.locator("body").innerText().catch(() => ""))
      .replace(/\s+/g, " ").slice(0, 500);
    out.after_open_destinations = (await page.locator("body").innerText().catch(() => ""))
      .replace(/\s+/g, " ").slice(0, 900);
    out.asset_served = await page.evaluate(() => {
      const s = Array.from(document.querySelectorAll("script[src]")).map(x => x.getAttribute("src"));
      return s.filter(u => /\/assets\/index-.*\.js/.test(u));
    }).catch(() => null);
  } catch (e) {
    out.error = String(e).slice(0, 200);
  } finally {
    const ok = rows.filter(r => r.status === 200 && r.shape && r.shape.capability);
    out.verdict = rows.length === 0 ? "NO_CAPABILITY_CALL_OBSERVED"
      : ok.length === rows.length ? "ALL_JSON_200_ON_THE_USER_SURFACE"
      : "SOME_LEG_FAILED_ON_THE_USER_SURFACE";
    out.counts = { observed: rows.length, json_with_capability: ok.length,
                   failed: failures.length };
    fs.mkdirSync(path.dirname(OUT), { recursive: true });
    fs.writeFileSync(OUT, JSON.stringify(out, null, 1));
    console.log(JSON.stringify({ verdict: out.verdict, counts: out.counts,
                                 asset_served: out.asset_served, error: out.error ?? null }, null, 1));
    for (const r of rows) {
      console.log(" -", r.status, r.content_type, "sw=" + r.served_by_service_worker,
                  r.body_bytes + "B", r.query_in_url, JSON.stringify(r.shape).slice(0, 90));
    }
    console.log("out = " + OUT);
    await browser.close();
  }
})();
