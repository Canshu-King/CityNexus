/**
 * ORD-0268 cells 2 and 3 instrument: one client, one forced "offline + generation swap".
 *
 * Sequence for a brand-new profile:
 *   1. online, served from gen A            -> the worker installs/claims; record what the screen shows
 *   2. the SAME port now serves gen B       -> (a real swap: different shell bytes, different asset name)
 *   3. the whole site is then taken down    -> revisit /v8/hub and read, in two columns, whether the
 *                                               traveller gets the new generation or the old shell
 * The killer (cell 3) is the same sequence against a gen-B build whose `additionalManifestEntries`
 * line was removed in a scratch export: cell 2's conclusion must FLIP, otherwise cell 2 proves nothing
 * about the double entry.
 */
const fs = require("fs");
const PW = "D:/moodle/_qoder_integration_20260919/frontend/node_modules/playwright";
const { chromium } = require(PW);
function arg(n, d) { const i = process.argv.indexOf("--" + n); return i === -1 ? d : process.argv[i + 1]; }
const BASE = arg("base", "http://127.0.0.1:4441");
const OUT = arg("out", "D:/moodle/_qoder_b_ord0268_20260923/q268_step.json");
const STEP = arg("step", "online_a");
const PROFILE = arg("profile", "D:/moodle/_qoder_b_ord0268_20260923/profile");

async function readDoc(p) {
  return p.evaluate(() => {
    const scripts = [...document.querySelectorAll("script[src]")].map(s => s.getAttribute("src"));
    const links = [...document.querySelectorAll("link[rel=stylesheet]")].map(l => l.getAttribute("href"));
    return {
      url: location.href,
      controlled: Boolean(navigator.serviceWorker && navigator.serviceWorker.controller),
      controller: navigator.serviceWorker && navigator.serviceWorker.controller
        ? navigator.serviceWorker.controller.scriptURL.replace(/^https?:\/\/[^/]+/, "") : null,
      onLine: navigator.onLine,
      body_head: (document.body ? document.body.innerText : "").replace(/\s+/g, " ").slice(0, 200),
      script_srcs: scripts, style_hrefs: links,
      cache_names: null,
    };
  }).catch(() => ({ url: p.url(), unreadable: true }));
}

(async () => {
  const ctx = await chromium.launchPersistentContext(PROFILE, { viewport: { width: 390, height: 844 },
                                                                isMobile: true, hasTouch: true, locale: "zh-CN" });
  const p = ctx.pages()[0] || (await ctx.newPage());
  const errs = [];
  p.on("pageerror", e => errs.push(String(e.message).slice(0, 160)));
  const nav = await p.goto(BASE + "/v8/hub", { waitUntil: "domcontentloaded", timeout: 15000 })
    .then(r => ({ ok: true, status: r.status(), from_service_worker: r.fromServiceWorker() }))
    .catch(e => ({ ok: false, error: String(e.message).split("\n")[0].slice(0, 120) }));
  await p.waitForTimeout(STEP === "online_a" ? 5000 : 2500);
  let caches = [];
  try { caches = await p.evaluate(async () => await caches.keys()); } catch (e) { caches = ["read threw"]; }
  const doc = await readDoc(p);
  doc.cache_names = caches;
  fs.writeFileSync(OUT, JSON.stringify({ at: new Date().toISOString(), step: STEP, base: BASE,
                                         navigation: nav, document_read: doc, page_errors: errs.slice(0, 5) },
                                       null, 1), "utf8");
  console.log(`[${STEP}] nav=${nav.ok ? nav.status + " sw=" + nav.from_service_worker : "FAIL:" + nav.error} `
    + `ctrl=${doc.controller} caches=${JSON.stringify(caches)} scripts=${JSON.stringify(doc.script_srcs || [])} `
    + `head="${(doc.body_head || "").slice(0, 46)}"`);
  await ctx.close();
})().catch(e => { console.error("STEP THREW: " + (e && e.stack || e)); process.exit(9); });
