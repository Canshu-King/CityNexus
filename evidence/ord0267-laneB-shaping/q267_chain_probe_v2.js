/**
 * ORD-0267 next shot, v2. v1 (`q267_chain_probe.js`) is kept as it is: it produced 0 events and its own
 * error was "Unexpected token '^'" -- a string-injected observer that Playwright's serialisation mangled.
 * An instrument that reports nothing is not a reading, so v2 passes the observer as a real function and
 * reports its own page errors in the artifact.
 *
 * What it measures, on a brand-new context with nothing persisted:
 *   - the observer is installed at document start, i.e. BEFORE the app's own register() runs;
 *   - CacheStorage is snapshotted at every worker state transition and every 25 ms;
 *   - `fromServiceWorker()` on the first navigation and on a reload.
 * Nothing is mocked and no product byte is changed.
 */
const fs = require("fs");
const PW = "D:/moodle/_qoder_integration_20260919/frontend/node_modules/playwright";
const { chromium } = require(PW);
function arg(n, d) { const i = process.argv.indexOf("--" + n); return i === -1 ? d : process.argv[i + 1]; }
const BASE = arg("base", "http://127.0.0.1:4441");
const OUT = arg("out", "D:/moodle/_qoder_b_ord0267_20260923/q267_chain_v2.json");
const WINDOW_S = Number(arg("window", "18"));

function observer() {
  window.__chain = [];
  const strip = u => (u ? String(u).replace(/^https?:\/\/[^/]+/, "") : null);
  const snap = async (label, extra) => {
    let keys = [], per = {};
    try {
      keys = await caches.keys();
      for (const k of keys) {
        try { const c = await caches.open(k); per[k] = (await c.keys()).length; } catch (e) { per[k] = "open threw"; }
      }
    } catch (e) { keys = ["caches.keys threw: " + e.name]; }
    let regs = [];
    try {
      const all = await navigator.serviceWorker.getRegistrations();
      regs = all.map(r => ({ active: strip(r.active && r.active.scriptURL),
                             active_state: r.active && r.active.state,
                             installing: strip(r.installing && r.installing.scriptURL),
                             waiting: strip(r.waiting && r.waiting.scriptURL) }));
    } catch (e) { regs = ["regs threw"]; }
    window.__chain.push(Object.assign({ t_ms: Math.round(performance.now()), label,
                                        cache_names: keys, entries: per, registrations: regs }, extra || {}));
  };
  snap("document-start");
  navigator.serviceWorker.getRegistration().then(r0 => {
    snap("registration-lookup", { had_any: !!r0 });
    return navigator.serviceWorker.getRegistrations();
  }).then(regs => {
    const watchWorker = w => {
      if (!w || w.__watched) return;
      w.__watched = true;
      w.addEventListener("statechange", () => snap("statechange", { script: strip(w.scriptURL), state: w.state }));
    };
    regs.forEach(r => {
      r.addEventListener("updatefound", () => {
        const w = r.installing;
        if (w) { watchWorker(w); snap("updatefound", { script: strip(w.scriptURL), state: w.state }); }
      });
      [r.installing, r.waiting, r.active].forEach(watchWorker);
    });
    snap("registrations-observed", { count: regs.length });
  });
  navigator.serviceWorker.addEventListener("controllerchange", () =>
    snap("controllerchange", { controller: strip((navigator.serviceWorker.controller || {}).scriptURL) }));
  setInterval(() => snap("poll"), 25);
}

(async () => {
  const browser = await chromium.launch();
  const ctx = await browser.newContext({ viewport: { width: 390, height: 844 }, isMobile: true,
                                         hasTouch: true, locale: "zh-CN" });
  const p = await ctx.newPage();
  const errors = [];
  p.on("pageerror", e => errors.push(String(e && e.message).slice(0, 200)));
  await p.addInitScript(observer);
  const nav = await p.goto(BASE + "/v8/hub", { waitUntil: "domcontentloaded", timeout: 30000 })
    .then(r => ({ ok: true, status: r.status(), from_service_worker: r.fromServiceWorker() }))
    .catch(e => ({ ok: false, error: String(e.message).split("\n")[0].slice(0, 140) }));
  await p.waitForTimeout(WINDOW_S * 1000);
  const chain = await p.evaluate(() => window.__chain || []);
  const reloadNav = await p.reload({ waitUntil: "domcontentloaded", timeout: 20000 })
    .then(r => ({ ok: true, status: r.status(), from_service_worker: r.fromServiceWorker() })).catch(() => ({ ok: false }));
  const afterReload = await p.evaluate(async () => {
    const keys = await caches.keys();
    const regs = await navigator.serviceWorker.getRegistrations();
    const c = navigator.serviceWorker.controller;
    return { cache_names: keys, controller: c ? c.scriptURL : null,
             active_states: regs.map(r => r.active && r.active.state) };
  });
  const nonPoll = chain.filter(s => s.label !== "poll");
  const polls = chain.filter(s => s.label === "poll");
  const states = {};
  chain.forEach(s => (s.registrations || []).forEach(r => {
    if (!r || !r.active) return;
    const k = JSON.stringify([r.active, r.active_state, r.installing, r.waiting]);
    if (states[k] === undefined) states[k] = s.t_ms;
  }));
  const allCaches = [...new Set(chain.flatMap(s => s.cache_names || []))];
  fs.writeFileSync(OUT, JSON.stringify({
    at: new Date().toISOString(), base: BASE, profile: "brand-new context, nothing persisted",
    observer: "addInitScript(function) at document start", sample_interval_ms: 25,
    first_navigation: nav, reload_navigation: reloadNav, state_after_reload: afterReload,
    instrument_page_errors: errors.slice(0, 10),
    events_total: chain.length, polls: polls.length, non_poll_events: nonPoll,
    cache_names_ever_seen: allCaches,
    first_poll_with_any_cache: (polls.find(s => (s.cache_names || []).length) || { t_ms: null }).t_ms,
    first_nonpoll_event_with_any_cache: (nonPoll.find(s => (s.cache_names || []).length) || { t_ms: null }).t_ms,
    registration_states_first_seen: states,
  }, null, 1), "utf8");
  console.log("nav1:", JSON.stringify(nav), "| reload:", JSON.stringify(reloadNav));
  console.log("events:", chain.length, "(polls " + polls.length + ") page errors:", JSON.stringify(errors.slice(0, 2)));
  console.log("caches ever seen:", JSON.stringify(allCaches));
  nonPoll.slice(0, 14).forEach(s => console.log(`  t=${String(s.t_ms).padStart(5)}ms ${s.label} `
    + `${s.state || ""} ${s.controller || s.script || ""} regs=${JSON.stringify(s.registrations).slice(0, 84)} caches=${JSON.stringify(s.cache_names)}`));
  console.log("after reload:", JSON.stringify(afterReload));
  await browser.close();
})().catch(e => { console.error("CHAIN PROBE v2 THREW: " + (e && e.stack || e)); process.exit(9); });
