/**
 * ORD-0274-SW: does the product's own reload-on-controller-change ever fire across a generation swap?
 *
 * Phases, run against ONE persistent profile while the origin on the same port swaps generations:
 *   install  first visit while the old generation is served -> registration + executed bundle
 *   watch    one ordinary navigation after the origin became the new generation. Everything the page
 *            does on its own is recorded here: worker lifecycle events, the two scriptURLs the product
 *            compares, the product's own sessionStorage marker, whether the document reloaded itself,
 *            and the bundle that is actually executing at the end of the window.
 *   again    a SECOND ordinary navigation (only reached if the product did not converge on its own),
 *            so "the contract allows 1 navigation, the build needs 2" is a count and not an opinion.
 *
 * The observer is installed as a FUNCTION via addInitScript (a string would lose every regex and
 * closure), and each load writes into sessionStorage so a self-reload is visible as a second load id.
 *
 * usage: node q274_transition_probe.js --base URL --profile DIR --out FILE --phase install|watch|again [--window 45]
 */
const path = require("path");
const fs = require("fs");
const PW = "D:/moodle/_qoder_integration_20260919/frontend/node_modules/playwright";
const { chromium } = require(PW);
function arg(n, d) { const i = process.argv.indexOf("--" + n); return i === -1 ? d : process.argv[i + 1]; }

const BASE = arg("base"), PROFILE = arg("profile"), OUT = arg("out"), PHASE = arg("phase");
const WINDOW = Number(arg("window", "45"));
const PRODUCT_KEY = "citynexus.sw.controller-transition";

function observer() {
  const w = window;
  w.__cnxProbe = { loads: (JSON.parse(sessionStorage.getItem("cnx274loads") || "[]")), events: [],
                   scriptURL_at_load: null, bundle_at_load: null };
  const id = w.__cnxProbe.loads.length + 1;
  w.__cnxProbe.loads.push({ id, at: performance.now(), href: location.href });
  sessionStorage.setItem("cnx274loads", JSON.stringify(w.__cnxProbe.loads));
  const push = (kind, extra) => w.__cnxProbe.events.push(Object.assign({
    kind, t_ms: Math.round(performance.now()), load_id: id,
    controller: navigator.serviceWorker && navigator.serviceWorker.controller
      ? navigator.serviceWorker.controller.scriptURL.replace(location.origin, "") : null,
    bundle: (document.querySelector('script[type="module"]') || {}).src
      ? document.querySelector('script[type="module"]').src.replace(location.origin, "") : null,
  }, extra || {}));
  push("document-start");
  navigator.serviceWorker.addEventListener("controllerchange", () => push("controllerchange"));
  (async () => {
    try {
      const reg = await navigator.serviceWorker.getRegistration("/");
      if (!reg) { push("no-registration"); return; }
      w.__cnxProbe.scriptURL_at_load = navigator.serviceWorker.controller
        ? navigator.serviceWorker.controller.scriptURL.replace(location.origin, "") : null;
      const snap = () => ({ installing: reg.installing && reg.installing.state,
                            waiting: reg.waiting && reg.waiting.state,
                            active: reg.active && reg.active.state,
                            active_script: reg.active && reg.active.scriptURL.replace(location.origin, "") });
      push("registration-looked-up", snap());
      reg.addEventListener("updatefound", () => {
        push("updatefound", snap());
        const nw = reg.installing;
        if (nw) nw.addEventListener("statechange", () => push("statechange:" + nw.state, snap()));
      });
    } catch (e) { push("observer-error", { error: String(e && e.message).slice(0, 120) }); }
  })();
  setTimeout(() => {
    w.__cnxProbe.bundle_at_load = (document.querySelector('script[type="module"]') || {}).src || null;
    w.__cnxProbe.product_reload_key = sessionStorage.getItem("citynexus.sw.controller-transition");
  }, 200);
}

(async () => {
  const ctx = await chromium.launchPersistentContext(PROFILE, {
    viewport: { width: 390, height: 844 }, isMobile: true, hasTouch: true,
    deviceScaleFactor: 2, locale: "zh-CN", timezoneId: "Asia/Shanghai",
  });
  await ctx.addInitScript(observer);
  const page = ctx.pages()[0] || (await ctx.newPage());
  const consoleLines = [], errors = [];
  page.on("console", (m) => { if (m.type() === "error") consoleLines.push(m.text().slice(0, 160)); });
  page.on("pageerror", (e) => errors.push(String(e && e.message).slice(0, 160)));

  const t0 = Date.now();
  await page.goto(BASE + "/v8/hub", { waitUntil: "domcontentloaded", timeout: 40000 })
    .catch((e) => errors.push("goto:" + String(e.message).slice(0, 90)));

  let swapInfo = null;
  const samples = [];
  if (PHASE === "inplace") {
    /* The point of this phase: the document that is ALREADY OPEN must live through the swap. Restarting
       the origin between navigations measures a different thing (a fresh document gets the new shell by
       definition), and that is exactly the mistake my first version made. */
    await page.waitForTimeout(3000);
    swapInfo = await page.evaluate(async () => {
      const r = await fetch("/__admin/swap", { cache: "no-store" });
      const j = await r.json().catch(() => null);
      const reg = await navigator.serviceWorker.getRegistration("/");
      let after = null;
      if (reg) { try { await reg.update(); } catch (e) {} 
                 after = { installing: reg.installing && reg.installing.state,
                           waiting: reg.waiting && reg.waiting.state,
                           active: reg.active && reg.active.state }; }
      return { swap_response: j, registration_after_update: after };
    }).catch((e) => ({ error: String(e && e.message).slice(0, 120) }));
    for (let i = 0; i < WINDOW; i += 1) {
      await page.waitForTimeout(1000);
      samples.push(await page.evaluate(() => ({
        t_s: Math.round(performance.now() / 100) / 10,
        bundle: ((document.querySelector('script[type="module"]') || {}).src || "").replace(location.origin, "") || null,
        controller: navigator.serviceWorker.controller
          ? navigator.serviceWorker.controller.scriptURL.replace(location.origin, "") : null,
        loads: JSON.parse(sessionStorage.getItem("cnx274loads") || "[]").length,
        reload_key: sessionStorage.getItem("citynexus.sw.controller-transition"),
      })).catch(() => ({ evaluate_failed: true })));
    }
  } else {
    await page.waitForTimeout(PHASE === "install" ? 9000 : WINDOW * 1000);
  }

  const seen = await page.evaluate(async (key) => {
    const reg = await navigator.serviceWorker.getRegistration("/");
    const doc = document.querySelector('script[type="module"]') || {};
    return {
      loads: (window.__cnxProbe && window.__cnxProbe.loads) || null,
      events: (window.__cnxProbe && window.__cnxProbe.events) || null,
      controller_now: navigator.serviceWorker && navigator.serviceWorker.controller
        ? navigator.serviceWorker.controller.scriptURL.replace(location.origin, "") : null,
      registrations: reg ? [{ scope: reg.scope.replace(location.origin, ""),
                             active: reg.active && reg.active.scriptURL.replace(location.origin, ""),
                             active_state: reg.active && reg.active.state,
                             waiting: reg.waiting && reg.waiting.scriptURL.replace(location.origin, ""),
                             waiting_state: reg.waiting && reg.waiting.state,
                             installing: reg.installing && reg.installing.state }] : [],
      product_reload_key: sessionStorage.getItem(key),
      executing_bundle: doc.src ? doc.src.replace(location.origin, "") : null,
      shell_in_document: Array.from(document.querySelectorAll('link[rel="modulepreload"],script[src]'))
        .map((n) => (n.href || n.src).replace(location.origin, "")).filter((u) => u.includes("/assets/")),
      mounted: Boolean(document.querySelector("#root") && document.querySelector("#root").children.length),
      onLine: navigator.onLine,
    };
  }, PRODUCT_KEY).catch((e) => ({ evaluate_error: String(e && e.message).slice(0, 160) }));

  const result = { phase: PHASE, at: new Date().toISOString(), base: BASE, window_s: WINDOW,
                   observed_for_ms: Date.now() - t0, seen, console_errors: consoleLines.slice(0, 6),
                   page_errors: errors.slice(0, 4), swap_request: swapInfo, samples, profile: PROFILE };
  fs.writeFileSync(OUT, JSON.stringify(result, null, 1), "utf8");
  const loads = (seen.loads || []).length;
  console.log(`${PHASE}: bundle=${seen.executing_bundle} controller=${seen.controller_now} `
    + `loads=${loads} reload_key=${JSON.stringify(seen.product_reload_key)} `
    + `waiting=${(seen.registrations[0] || {}).waiting_state || null} events=${(seen.events || []).length} `
    + `-> ${path.basename(OUT)}`);
  await ctx.close();
})().catch((e) => { console.error("PROBE THREW: " + (e && e.stack || e)); process.exit(9); });
