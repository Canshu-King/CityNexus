/**
 * ORD-0267, the approved next shot: the install -> activate -> cache chain on a never-used profile.
 *
 * The previous pass said "CacheStorage is empty while observed"; it did NOT pin the causal chain, because
 * nothing sampled CacheStorage at the moment each worker state changed. This probe does exactly that:
 *
 *   - a brand-new browser context (no persisted profile, nothing installed),
 *   - page-side listeners on the registration itself: `updatefound` -> each worker's `statechange`
 *     (installed -> activating -> activated), and at EVERY transition it immediately snapshots
 *     `caches.keys()` plus per-cache entry counts,
 *   - plus a 100 ms poll, so a cache that appears and disappears between transitions is still caught,
 *   - and `caches.open/delete` timing is observed only from the page (the worker is not modified).
 *
 * No product code is changed and nothing is mocked: the only levers are my own server being up.
 */
const fs = require("fs");
const PW = "D:/moodle/_qoder_integration_20260919/frontend/node_modules/playwright";
const { chromium } = require(PW);
function arg(n, d) { const i = process.argv.indexOf("--" + n); return i === -1 ? d : process.argv[i + 1]; }
const BASE = arg("base", "http://127.0.0.1:4441");
const OUT = arg("out", "D:/moodle/_qoder_b_ord0267_20260923/q267_chain.json");
const WINDOW_S = Number(arg("window", "18"));

const INSTALLER = `(() => {
  window.__chain = [];
  const snap = async (label, extra) => {
    const keys = await caches.keys();
    const per = {};
    for (const k of keys) { try { const c = await caches.open(k); per[k] = (await c.keys()).length; }
                            catch (e) { per[k] = "open threw"; } }
    window.__chain.push(Object.assign({ t_ms: Math.round(performance.now()), label, cache_names: keys,
                                        entries: per }, extra || {}));
  };
  snap("before registration lookup");
  navigator.serviceWorker.getRegistration().then(async (r0) => {
    snap("registration looked up", { had_registration: !!r0 });
    const regs = await navigator.serviceWorker.getRegistrations();
    window.__watch = [];
    const watch = (reg) => {
      const seen = new Set();
      const name = (w) => (w && w.scriptURL ? w.scriptURL.replace(/^https?:\\/\\/[^/]+/, "") : null);
      const describe = (w, state) => ({ scope: reg.scope.replace(/^https?:\\/\\/[^/]+/, ""),
                                        script: name(w), state });
      const onUpdate = () => {
        const w = reg.installing;
        if (!w || seen.has(w)) return;
        seen.add(w);
        w.addEventListener("statechange", () => snap("statechange", Object.assign(describe(w, w.state), {})));
        snap("updatefound (installing)", describe(w, w.state));
      };
      reg.addEventListener("updatefound", onUpdate);
      ["installing", "waiting", "active"].forEach(k => { if (reg[k] && !seen.has(reg[k])) {
        seen.add(reg[k]);
        reg[k].addEventListener("statechange", () => snap("statechange", describe(reg[k], reg[k].state)));
      }});
      snap("registration observed", { scope: reg.scope.replace(/^https?:\\/\\/[^/]+/, ""),
        installing: name(reg.installing), waiting: name(reg.waiting), active: name(reg.active) });
    };
    regs.forEach(watch);
    navigator.serviceWorker.addEventListener("controllerchange",
      () => snap("controllerchange", { controller: (navigator.serviceWorker.controller || {}).scriptURL
        ? navigator.serviceWorker.controller.scriptURL.replace(/^https?:\\/\\/[^/]+/, "") : null }));
  });
  const regline = async () => {
    try { const regs = await navigator.serviceWorker.getRegistrations();
          const nm = w => (w && w.scriptURL ? w.scriptURL.replace(/^https?:[^/]*\/\/[^/]+/, "") : null);
          return regs.map(r => ({ inst: nm(r.installing), wait: nm(r.waiting), act: nm(r.active),
                                  act_state: r.active && r.active.state })); }
    catch (e) { return "reg read threw"; }
  };
  window.__poll = setInterval(async () => snap("poll", { registrations: await regline() }), 25);  /* cleared when the caller stops */
})()`;

(async () => {
  const browser = await chromium.launch();
  const ctx = await browser.newContext({ viewport: { width: 390, height: 844 }, isMobile: true,
                                         hasTouch: true, locale: "zh-CN" });
  const p = await ctx.newPage();
  const initErrors = [];
  p.on("pageerror", e => initErrors.push(String(e && e.message).slice(0, 220)));
  p.on("console", m => { if (m.type() === "error") initErrors.push("console: " + m.text().slice(0, 220)); });
  /* The listener must exist before the app registers the worker, otherwise "no statechange happened"
     is an artifact of attaching too late rather than a reading about the install. addInitScript runs at
     document start on every navigation; it only observes, it changes no product code and mocks nothing. */
  await p.addInitScript(INSTALLER.replace("%POLL_MS%", String(WINDOW_S * 1000 * 2)));
  const nav = await p.goto(BASE + "/v8/hub", { waitUntil: "domcontentloaded", timeout: 30000 })
    .then(r => ({ ok: true, status: r.status(), from_service_worker: r.fromServiceWorker() }))
    .catch(e => ({ ok: false, error: String(e.message).split("\n")[0].slice(0, 140) }));
  await p.waitForTimeout(WINDOW_S * 1000);
  const chain = await p.evaluate(() => window.__chain || []);
  const reloadNav = await p.reload({ waitUntil: "domcontentloaded", timeout: 20000 })
    .then(r => ({ ok: true, status: r.status(), from_service_worker: r.fromServiceWorker() })).catch(e => ({ ok: false }));
  const afterReload = await p.evaluate(async () => {
    const keys = await caches.keys();
    const regs = await navigator.serviceWorker.getRegistrations();
    const nm = s => (s && s.scriptURL ? s.scriptURL.replace(/^https?:\/\/[^/]+/, "") : null);
    return { cache_names: keys, controller: nm(navigator.serviceWorker.controller),
             registrations: regs.map(r => ({ installing: nm(r.installing), waiting: nm(r.waiting),
                                             active: nm(r.active) })) };
  });
  fs.writeFileSync(OUT, JSON.stringify({
    at: new Date().toISOString(), base: BASE, profile: "brand-new context (nothing persisted)",
    first_navigation: nav, chain_events: chain, chain_event_count: chain.length,
    instrument_errors: initErrors.slice(0, 12),
    cache_names_ever_seen: [...new Set(chain.flatMap(s => s.cache_names || []))],
    transitions: chain.filter(s => s.label === "statechange" || s.label === "updatefound (installing)"
                                   || s.label === "controllerchange"),
    reload_navigation: reloadNav, state_after_reload: afterReload,
  }, null, 1), "utf8");
  const kinds = {};
  chain.forEach(s => { kinds[s.label] = (kinds[s.label] || 0) + 1; });
  console.log("nav1:", JSON.stringify(nav), "| reload:", JSON.stringify(reloadNav));
  console.log("events:", chain.length, "kinds:", JSON.stringify(kinds));
  console.log("cache names ever seen:", JSON.stringify([...new Set(chain.flatMap(s => s.cache_names || []))]));
  (chain.filter(s => s.label !== "poll")).slice(0, 14).forEach(s =>
    console.log(`  t=${s.t_ms}ms ${s.label} state=${s.state || "-"} script=${s.script || s.installing || "-"} caches=${JSON.stringify(s.cache_names)}`));
  console.log("after reload:", JSON.stringify(afterReload));
  await browser.close();
})().catch(e => { console.error("CHAIN PROBE THREW: " + (e && e.stack || e)); process.exit(9); });
