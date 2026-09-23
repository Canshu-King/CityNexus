/**
 * ORD-0267 shaping probe: what does a phone get when the whole site is down, per client state?
 *
 * The config declares two layers already (vite.config.ts: `navigateFallback: "/index.html"`,
 * `navigateFallbackAllowlist: [/^\/(?:v8|index)/]`, plus a NetworkFirst rule for `/v8/` documents).
 * So "deep link falls to chrome-error://" can only be explained by *which* layer was absent for that
 * client, and that is what this probe separates. Each case runs in its own profile, and the SW facts
 * are read from the browser, not from the config file.
 *
 * usage: node q267_probe.js --base http://127.0.0.1:4441 --out FILE
 */
const fs = require("fs");
const PW = "D:/moodle/_qoder_integration_20260919/frontend/node_modules/playwright";
const { chromium } = require(PW);
function arg(n, d) { const i = process.argv.indexOf("--" + n); return i === -1 ? d : process.argv[i + 1]; }

const BASE = arg("base", "http://127.0.0.1:4441");
const OUT = arg("out", "D:/moodle/_qoder_b_ord0263_20260923/q267_probe.json");
const PROFILE_ONLINE = arg("p1", "D:/moodle/_qoder_b_ord0267_20260923/profile_install");
const PROFILE_COLD = arg("p2", "D:/moodle/_qoder_b_ord0267_20260923/profile_cold");

/* Everything below runs INSIDE the page: `page.evaluate(fn)` serialises `fn`, so a helper that
   itself calls `p.evaluate` cannot be passed in (that was my first version's bug -- it silently read
   as "no service worker" when it was really "my instrument threw"). Each reader returns its own error
   string instead of a swallowed undefined. */
const facts = async () => {
  try {
    return {
      url: location.href,
      controlled: Boolean(navigator.serviceWorker && navigator.serviceWorker.controller),
      onLine: navigator.onLine,
      title: document.title,
      body_head: (document.body ? document.body.innerText : "").replace(/\s+/g, " ").slice(0, 160),
      app_mounted: Boolean(document.querySelector("#root") && document.querySelector("#root").children.length),
    };
  } catch (e) { return { eval_error: "facts: " + String(e && e.message) }; }
};
const regState = async () => {
  try {
    const all = await navigator.serviceWorker.getRegistrations();
    const urlOf = (s) => (s && s.scriptURL ? s.scriptURL.replace(/^https?:\/\/[^/]+/, "") : null);
    return {
      count: all.length,
      controller_script: (navigator.serviceWorker.controller || {}).scriptURL
        ? navigator.serviceWorker.controller.scriptURL.replace(/^https?:\/\/[^/]+/, "") : null,
      list: all.map(r => ({
        scope: r.scope, update_via_cache: r.updateViaCache,
        active: urlOf(r.active), installing: urlOf(r.installing), waiting: urlOf(r.waiting),
      })),
    };
  } catch (e) { return { eval_error: "registrations: " + String(e && e.message) }; }
};
const cacheState = async () => {
  try {
    const keys = await caches.keys();
    const precache = keys.find(k => /precache/i.test(k));
    let n = 0, hasIndexHtml = null, names = [];
    if (precache) {
      const c = await caches.open(precache);
      const ks = await c.keys();
      n = ks.length;
      names = ks.map(r => { try { return new URL(r.url).pathname; } catch { return String(r.url); } })
                .sort().slice(0, 12);
      hasIndexHtml = names.some(pn => pn.endsWith("/index.html"));
    }
    return { cache_names: keys, precache_name: precache || null, precache_entries: n,
             precache_has_index_html: hasIndexHtml, precache_sample_paths: names };
  } catch (e) { return { eval_error: "cache_state: " + String(e && e.message) }; }
};

async function visit(ctx, path, tag, res) {
  const p = ctx.pages()[0] || (await ctx.newPage());
  const nav = await p.goto(BASE + path, { waitUntil: "domcontentloaded", timeout: 12000 })
    .then(r => ({ ok: true, status: r && r.status() }))
    .catch(e => ({ ok: false, error: String(e.message).split("\n")[0].slice(0, 140) }));
  await p.waitForTimeout(1200);
  const grab = async (fn, label) => {
    try { return await p.evaluate(fn); } catch (e) { return { eval_error: label + ": " + String(e && e.message).slice(0, 160) }; }
  };
  const f = await grab(facts, "facts");
  res.push({ case: tag, path, navigation: nav, facts: f,
             registrations: await grab(regState, "registrations"),
             cache_state: await grab(cacheState, "cache_state") });
}

(async () => {
  const phase = arg("phase", "up");
  const out = { at: new Date().toISOString(), base: BASE, phase, steps: [] };
  const OPTS = { viewport: { width: 390, height: 844 }, isMobile: true, hasTouch: true, locale: "zh-CN" };

  if (phase === "up") {
    const ctxA = await chromium.launchPersistentContext(PROFILE_ONLINE, OPTS);
    await visit(ctxA, "/v8/hub", "A_install_while_online", out.steps);
    await visit(ctxA, "/v8/hub", "A2_second_navigation_while_online", out.steps);
    await ctxA.close();
  } else {
    const ctxB = await chromium.launchPersistentContext(PROFILE_ONLINE, OPTS);
    await visit(ctxB, "/v8/hub", "B_returning_client_offline_deeplink", out.steps);
    await visit(ctxB, "/", "B2_returning_client_offline_root", out.steps);
    await visit(ctxB, "/v8/discover", "B3_returning_client_offline_other_deep_link", out.steps);
    await ctxB.close();
    const ctxC = await chromium.launchPersistentContext(PROFILE_COLD, OPTS);
    await visit(ctxC, "/v8/hub", "C_never_visited_offline_deeplink", out.steps);
    await ctxC.close();
  }
  out.steps.forEach(s => {
    const cs = s.cache_state || {}, rg = s.registrations || {};
    console.log(`${s.case.padEnd(40)} nav=${s.navigation.ok ? s.navigation.status : "FAIL"} `
      + `url=${(s.facts.url || "").slice(BASE.length) || "-"} sw=${JSON.stringify(s.facts.controlled)} `
      + `regs=${rg.count} precache=${cs.precache_entries}/${JSON.stringify(cs.precache_has_index_html)} `
      + `app=${JSON.stringify(s.facts.app_mounted)}`);
  });

  const outFile = OUT.replace(/\.json$/, "") + "_" + phase + ".json";
  fs.writeFileSync(outFile, JSON.stringify(out, null, 1), "utf8");
  console.log("->", outFile);
})().catch(e => { console.error("PROBE THREW: " + (e && e.stack || e)); process.exit(9); });
