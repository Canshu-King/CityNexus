/**
 * ORD-0267 step 2 probe: cold bootstrap under a partially failing origin.
 *
 *   --phase install   first visit ever (fresh profile): what lands in the precache, what does not,
 *                     what the page itself reports; the worker's own manifest is fetched and parsed so
 *                     "expected" is the worker's list, not my guess.
 *   --phase offline   after the origin is gone: does an ordinary navigation render, and which
 *                     sub-resources fail -- i.e. is this a half generation that pretends to be whole?
 *
 * usage: node q267b_probe.js --base URL --profile DIR --out FILE --phase install|offline
 */
const path = require("path");
const fs = require("fs");
const PW = "D:/moodle/_qoder_integration_20260919/frontend/node_modules/playwright";
const { chromium } = require(PW);

function arg(n, d) {
  const i = process.argv.indexOf("--" + n);
  return i === -1 ? d : process.argv[i + 1];
}

const BASE = arg("base"), PROFILE = arg("profile"), OUT = arg("out"), PHASE = arg("phase", "install");

(async () => {
  const ctx = await chromium.launchPersistentContext(PROFILE, {
    viewport: { width: 390, height: 844 }, isMobile: true, hasTouch: true,
    deviceScaleFactor: 2, locale: "zh-CN", timezoneId: "Asia/Shanghai",
  });
  const page = ctx.pages()[0] || (await ctx.newPage());
  const pageErrors = [], consoleErrors = [], failed = [], non200 = [];
  page.on("pageerror", (e) => pageErrors.push(String(e && e.message).slice(0, 160)));
  page.on("console", (m) => { if (m.type() === "error") consoleErrors.push(m.text().slice(0, 200)); });
  page.on("requestfailed", (r) => failed.push({ url: r.url().replace(BASE, ""), why: String(r.failure() && r.failure().errorText) }));
  page.on("response", (r) => { if (r.status() !== 200) non200.push({ url: r.url().replace(BASE, ""), status: r.status(),
                                                                      sw: (() => { try { return r.serviceWorker().started; } catch { return null; } })() }); });

  const nav = await page.goto(BASE + "/v8/hub", { waitUntil: "domcontentloaded", timeout: 30000 })
    .then((r) => ({ ok: true, status: r && r.status() }))
    .catch((e) => ({ ok: false, error: String(e.message).slice(0, 160) }));
  await page.waitForTimeout(PHASE === "install" ? 12000 : 4000);

  const facts = await page.evaluate(async () => {
    const text = document.body ? document.body.innerText.replace(/\s+/g, " ").trim().slice(0, 260) : "";
    const regs = await navigator.serviceWorker.getRegistrations().catch(() => null);
    let workerSrc = null, manifestUrls = null;
    try {
      const w = await fetch("/v10-sw.js", { cache: "no-store" });
      workerSrc = { status: w.status, ok: w.ok };
      const t = await w.text();
      const m = t.match(/precacheAndRoute\(\[([\s\S]*?)\]\)/);
      if (m) manifestUrls = Array.from(m[1].matchAll(/\{[^}]*url:\s*["']([^"']+)["']/g)).map((x) => x[1]);
      workerSrc.rev = (t.match(/revision:"([^"]+)"/g) || []).length;
      workerSrc.precacheCalls = (t.match(/precacheAndRoute/g) || []).length;
    } catch (e) { workerSrc = { error: String(e && e.message).slice(0, 120) }; }
    let caches = null;
    try {
      const names = await caches_keys();
      caches = {};
      for (const n of names) {
        const c = await caches_open(n);
        const keys = await c.keys();
        caches[n] = { entries: keys.length, urls: Array.from(keys).map((k) => (k.url || "").replace(location.origin, "")).sort() };
      }
    } catch (e) { caches = { error: String(e && e.message).slice(0, 120) }; }
    async function caches_keys() { return (await cachesList()).slice(); }
    async function cachesList() { return window.caches.keys ? (await Array.fromAsync(window.caches.keys())) : []; }
    async function caches_open(n) { return window.caches.open(n); }
    return {
      url: location.href, title: document.title,
      controlled: Boolean(navigator.serviceWorker && navigator.serviceWorker.controller),
      controller_script: navigator.serviceWorker && navigator.serviceWorker.controller
        ? navigator.serviceWorker.controller.scriptURL.replace(location.origin, "") : null,
      onLine: navigator.onLine,
      app_mounted: Boolean(document.querySelector("#root") && document.querySelector("#root").children.length),
      registrations: (regs || []).map((r) => ({ scope: r.scope.replace(location.origin, ""),
                                                active: r.active && r.active.scriptURL.replace(location.origin, ""),
                                                active_state: r.active && r.active.state,
                                                waiting: r.waiting && r.waiting.scriptURL.replace(location.origin, ""),
                                                installing: r.installing && r.installing.scriptURL.replace(location.origin, "") })),
      worker_source: workerSrc, manifest_urls: manifestUrls, caches,
      rendered_head: text,
      leaf_count: document.querySelectorAll("body *").length,
    };
  }).catch((e) => ({ evaluate_error: String(e && e.message).slice(0, 200) }));

  let assetOutcome = null;
  if (PHASE === "offline") {
    assetOutcome = await page.evaluate(async () => {
      const urls = Array.from(document.querySelectorAll('link[rel="modulepreload"],script[src],link[href$=".css"]'))
        .map((n) => n.src || n.href);
      const out = [];
      for (const u of urls.slice(0, 8)) {
        try {
          const r = await fetch(u.replace(location.origin, ""), { cache: "no-store" });
          out.push({ url: u.replace(location.origin, ""), status: r.status, from_sw: (r.serviceWorker ? "n/a" : "n/a") });
        } catch (e) { out.push({ url: u.replace(location.origin, ""), error: String(e && e.message).slice(0, 80) }); }
      }
      return out;
    }).catch((e) => ({ error: String(e.message).slice(0, 120) }));
  }

  let probeAssetFetch = null;
  if (PHASE === "install") {
    /* A file that is deliberately NOT in the worker's precache list. Without this request the fourth
       arm observes nothing at all, so the number below is the evidence that the arm ran. */
    probeAssetFetch = await page.evaluate(async () => {
      try {
        const r = await fetch("/assets/probe-extra.js", { cache: "no-store" });
        return { status: r.status, ok: r.ok };
      } catch (e) { return { error: String(e && e.message).slice(0, 100) }; }
    }).catch((e) => ({ error: String(e && e.message).slice(0, 100) }));
    await page.waitForTimeout(2500);
  }

  const result = { phase: PHASE, at: new Date().toISOString(), base: BASE, profile: PROFILE,
                   navigation: nav, facts, page_errors: pageErrors, console_errors: consoleErrors,
                   nonmember_request: probeAssetFetch,
                   requests_failed: failed, non_200_responses: non200, offline_asset_probe: assetOutcome };
  if (PHASE === "install" && facts.manifest_urls && facts.caches && !facts.caches.error) {
    const cached = new Set([].concat(...Object.values(facts.caches).map((c) => c.urls || [])));
    result.missing_from_cache = facts.manifest_urls.filter((u) => !cached.has(u));
    result.manifest_count = facts.manifest_urls.length;
    result.cached_count = cached.size;
  }
  fs.writeFileSync(OUT, JSON.stringify(result, null, 1), "utf8");
  console.log(`${PHASE}: nav=${JSON.stringify(nav)} controlled=${facts.controlled} mounted=${facts.app_mounted}`
    + ` caches=${Object.keys(facts.caches || {}).length} missing=${JSON.stringify(result.missing_from_cache || null).slice(0, 120)}`
    + ` non200=${non200.length} failed=${failed.length} -> ${path.basename(OUT)}`);
  await ctx.close();
})().catch((e) => { console.error("PROBE THREW: " + (e && e.stack || e)); process.exit(9); });
