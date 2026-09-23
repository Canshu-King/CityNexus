/**
 * ORD-0267 · the worker's own install reading (no product change, no browser mock).
 *
 * Question on the table: a controlled client shows CacheStorage for the origin = [] even though the
 * generated worker calls `precacheAndRoute([...9 entries...])`, `NavigationRoute(createHandlerBoundToURL
 * ("/index.html"))` and two runtime routes. Why does nothing land?
 *
 * Three readings, all from the browser:
 *   1. CDP `Log.entryAdded` on a BROWSER-level session -- the only channel that carries a service
 *      worker's own console/uncaught-rejection text (source: "scriptWorker");
 *   2. a cache timeline: CacheStorage sampled every 500 ms for ~20 s after the first install, so
 *      "appeared then vanished" is distinguished from "never appeared";
 *   3. `response.fromServiceWorker()` on a navigation and on an asset request while the site is UP --
 *      if no workbox route ever ran, nothing is ever served by the worker.
 *
 * Static hypotheses were already settled before this run (and are recorded as such): the page-side
 * `removeLegacyServiceWorkerCaches()` deletes only the three unsuffixed names, which no workbox cache
 * matches; `workbox-*.js` does call `define(["exports"], ...)`, so "the chunk registers no module" is
 * refuted by reading the file. This run is about what the worker actually says at runtime.
 *
 * usage: node q267_install_probe.js --base http://127.0.0.1:4441 --out FILE
 */
const fs = require("fs");
const PW = "D:/moodle/_qoder_integration_20260919/frontend/node_modules/playwright";
const { chromium } = require(PW);
function arg(n, d) { const i = process.argv.indexOf("--" + n); return i === -1 ? d : process.argv[i + 1]; }

const BASE = arg("base", "http://127.0.0.1:4441");
const OUT = arg("out", "D:/moodle/_qoder_b_ord0267_20260923/q267_install_probe.json");
const WINDOW_S = Number(arg("window", "20"));

(async () => {
  const browser = await chromium.launch({ args: ["--enable-logging=stderr", "--v=1"], dumpio: true });
  const log = [];
  let cdp_state;
  try {
    const cdp = await browser.newBrowserCDPSession();
    cdp.on("Log.entryAdded", (e) => {
      const en = e.entry || {};
      log.push({ source: en.source, level: en.level, url: en.url,
                 text: String(en.text || "").slice(0, 400), line: en.lineNumber, timestamp: en.timestamp });
    });
    await cdp.send("Log.enable");
    cdp_state = "enabled";
  } catch (e) {
    cdp_state = "UNAVAILABLE: " + String(e && e.message).split("\n")[0].slice(0, 130);
    console.log("CDP-LOG: " + cdp_state + " -> relying on Chrome stderr (dumpio) only");
  }

  const ctx = await browser.newContext({ viewport: { width: 390, height: 844 }, isMobile: true,
                                         hasTouch: true, locale: "zh-CN" });
  const p = await ctx.newPage();
  const t0 = Date.now();
  const nav = await p.goto(BASE + "/v8/hub", { waitUntil: "domcontentloaded", timeout: 30000 })
    .then(r => ({ ok: true, status: r.status(), from_service_worker: r.fromServiceWorker() }))
    .catch(e => ({ ok: false, error: String(e.message).split("\n")[0].slice(0, 140) }));

  const timeline = [];
  while ((Date.now() - t0) / 1000 < WINDOW_S) {
    const sample = await p.evaluate(async () => {
      const keys = await caches.keys();
      const regs = await navigator.serviceWorker.getRegistrations();
      const urlOf = s => (s && s.scriptURL ? s.scriptURL.replace(/^https?:\/\/[^/]+/, "") : null);
      const per = {};
      for (const k of keys) {
        try { const c = await caches.open(k); per[k] = (await c.keys()).length; } catch { per[k] = null; }
      }
      return { t_ms: Date.now(), cache_names: keys, entries_per_cache: per,
               controller: urlOf(navigator.serviceWorker.controller),
               registrations: regs.map(r => ({ scope: r.scope, active: urlOf(r.active),
                                               installing: urlOf(r.installing), waiting: urlOf(r.waiting) })) };
    }).catch(e => ({ eval_error: String(e.message).slice(0, 160) }));
    timeline.push(sample);
    await p.waitForTimeout(500);
  }

  // does the worker answer ANYTHING while the site is up?
  const MANIFEST = JSON.parse(fs.readFileSync(
    "D:/moodle/_qoder_spike_20260921/q267_precache_manifest.json", "utf8")).entries.map(e => e.url);
  const manifestStatus = await p.evaluate(async (urls) => {
    const o = {};
    for (const u of urls) {
      try { const r = await fetch(u, { cache: "reload" }); o[u] = { status: r.status }; }
      catch (e) { o[u] = { error: String(e.name) }; }
    }
    return o;
  }, MANIFEST);
  const preloadState = await p.evaluate(async () => {
    try {
      const regs = await navigator.serviceWorker.getRegistrations();
      return regs.map(r => ({ scope: r.scope,
        navigation_preload: r.navigationPreload
          ? { enabled: r.navigationPreload.isEnabled(), value: r.navigationPreload.getValue() }
          : "no_api" }));
    } catch (e) { return { eval_error: String(e.message).slice(0, 120) }; }
  });
  const assetProbe = await p.evaluate(async () => {
    const urls = ["/v8/hub", "/assets/" + "index-dummy", "/index.html", "/v10-sw.js"];
    const outp = {};
    for (const u of urls) {
      try { const r = await fetch(u, { cache: "no-store" });
        outp[u] = { status: r.status, ct: r.headers.get("content-type") }; }
      catch (e) { outp[u] = { error: String(e.name) }; }
    }
    return outp;
  });
  const secondNav = await p.goto(BASE + "/v8/discover", { waitUntil: "domcontentloaded", timeout: 20000 })
    .then(r => ({ ok: true, status: r.status(), from_service_worker: r.fromServiceWorker() }))
    .catch(e => ({ ok: false, error: String(e.message).split("\n")[0].slice(0, 140) }));

  const swLog = log.filter(e => /worker/i.test(e.source || "") ||
    /v10-sw|workbox|precache|install/i.test(e.text || ""));
  fs.writeFileSync(OUT, JSON.stringify({
    at: new Date().toISOString(), base: BASE, window_s: WINDOW_S, cdp_log_channel: cdp_state,
    first_navigation: nav, second_navigation: secondNav,
    cache_timeline: timeline.map(s => ({ ...s, t_ms: s.t_ms ? s.t_ms - t0 : null })),
    precache_manifest_urls: MANIFEST, manifest_url_status_online: manifestStatus,
    navigation_preload_state: preloadState,
    asset_probe_online: assetProbe,
    log_entries_total: log.length,
    log_entries_worker_shaped: swLog,
    log_entries_all: log.slice(0, 60),
  }, null, 1), "utf8");

  console.log("nav1:", JSON.stringify(nav), " nav2:", JSON.stringify(secondNav));
  const first = timeline.find(t => (t.cache_names || []).length) || timeline[timeline.length - 1];
  console.log("caches ever seen:", timeline.some(t => (t.cache_names || []).length),
              "| final:", JSON.stringify((first.cache_names || []).slice(0, 4)),
              "controller:", first.controller, "regs:", JSON.stringify(first.registrations));
  console.log("worker-shaped log entries:", swLog.length, "of", log.length);
  swLog.slice(0, 8).forEach(e => console.log(`  [${e.source}/${e.level}] ${e.url || "-"} :: ${e.text.slice(0, 170)}`));
  await browser.close();
})().catch(e => { console.error("PROBE THREW: " + (e && e.stack || e)); process.exit(9); });
