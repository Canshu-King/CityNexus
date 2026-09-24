/**
 * ORD-0274 B2c: what happens to an ALREADY-OPEN document when a new generation takes over while one of
 * the product's own non-idempotent requests is still in flight.
 *
 * The write is not faked from the probe: the traveller's own path (open the trip wizard, fill it, press
 * 确认创建) is what fires `POST /api/v1/travelers` and `POST /api/v1/journeys` through v8Request, which is
 * the only thing that can raise `hasNonIdempotentRequestInFlight()` inside the bundle.  A synthetic fetch
 * from here would increment nothing and the arm would be vacuous.
 *
 * The swap is timed against the ORIGIN's own count (`/__admin/inflight`), not against a guessed sleep, and
 * every sample carries that count next to the load counter, so "the reload cut the write in half" is a
 * pair of numbers on one timeline rather than a story.
 *
 * Generation identity is a byte reading: `bundle_sha256` is the digest of the bytes fetched from the ref
 * the document is executing, and `gen_tag` is a statement that exists only in the next generation's
 * bundle.  Neither is a file name.
 *
 * usage: node q274_b2c_probe.js --base URL --profile DIR --out FILE --phase install|b2c [--window 60]
 */
const path = require("path");
const fs = require("fs");
const PW = "D:/moodle/_qoder_integration_20260919/frontend/node_modules/playwright";
const { chromium } = require(PW);
function arg(n, d) { const i = process.argv.indexOf("--" + n); return i === -1 ? d : process.argv[i + 1]; }

const BASE = arg("base"), PROFILE = arg("profile"), OUT = arg("out"), PHASE = arg("phase");
const WINDOW = Number(arg("window", "60"));
const RELOAD_KEY = "citynexus.sw.controller-transition";
const PENDING_KEY = "citynexus.sw.generation-handover-pending";
const DRAFT_KEY = "citynexus.v8.trial_draft";

/* One function, handed to addInitScript: a string would lose the closures, and this has to be in the
   document before the product's own module runs or the pending event is simply missed. */
function observer() {
  const w = window;
  w.__cnx274 = { events: [], loads: JSON.parse(sessionStorage.getItem("cnx274loads") || "[]") };
  const id = w.__cnx274.loads.length + 1;
  w.__cnx274.loads.push({ id, at: Date.now(), href: location.href,
                          gen_tag: w.__cnxGenerationTag || null });
  sessionStorage.setItem("cnx274loads", JSON.stringify(w.__cnx274.loads));
  const rec = (kind, extra) => w.__cnx274.events.push(Object.assign(
    { kind, load_id: id, t: Date.now(), iso: new Date().toISOString() }, extra || {}));
  rec("document-start", { gen_tag: w.__cnxGenerationTag || null });
  w.addEventListener("citynexus:generation-handover-pending", () => rec("handover-pending"));
  w.addEventListener("beforeunload", () => rec("beforeunload",
    { writes_open_probe: null }));
  navigator.serviceWorker.addEventListener("controllerchange", () => rec("controllerchange",
    { controller: navigator.serviceWorker.controller
      ? navigator.serviceWorker.controller.scriptURL.replace(location.origin, "") : null }));
}

async function byteIdentity(page) {
  return page.evaluate(async () => {
    const ref = ((document.querySelector('script[type="module"]') || {}).src || "");
    if (!ref) return { ref: null, sha256: null, gen_tag: window.__cnxGenerationTag || null };
    const r = await fetch(ref, { cache: "no-store" });
    const buf = await r.arrayBuffer();
    const digest = await crypto.subtle.digest("SHA-256", buf);
    const hex = Array.from(new Uint8Array(digest)).map((b) => b.toString(16).padStart(2, "0")).join("");
    const ctype = r.headers.get("content-type") || "";
    /* HTML answering a .js URL is the stale-client shape, not a byte identity: a document that never
       converged asks for a bundle the new generation no longer has, and an SPA fallback hands back the
       shell.  The digest of that is meaningless, so it is named here instead of being averaged in. */
    return { ref: ref.replace(location.origin, ""), sha256: hex, bytes: buf.byteLength,
             gen_tag: window.__cnxGenerationTag || null, served_status: r.status, content_type: ctype,
             html_at_js_url: /html/i.test(ctype) };
  }).catch(() => ({ ref: null, sha256: null, error: "evaluate_failed" }));
}

async function domState(page) {
  return page.evaluate(() => ({
    url: location.pathname,
    testids: Array.from(document.querySelectorAll("[data-testid]")).map((n) => n.getAttribute("data-testid")).slice(0, 40),
    buttons: Array.from(document.querySelectorAll("button")).map((b) => ({
      id: b.getAttribute("data-testid"), text: (b.innerText || "").slice(0, 24),
      disabled: b.disabled === true, aria_disabled: b.getAttribute("aria-disabled"),
    })).slice(0, 14),
    hint: ((document.querySelector('[data-testid="trial-next-reason"]') || {}).innerText || "").slice(0, 160),
    body_head: (document.body.innerText || "").slice(0, 200),
  })).catch((e) => ({ error: String(e && e.message).slice(0, 120) }));
}

async function fillWizard(page) {
  /* The traveller's own fields.  Values are chosen so a per-value comparison after a reload cannot be
     satisfied by a default: 4 people, 4321, and a special-requirement sentence the defaults never hold. */
  const setField = async (testid, value) => {
    const node = page.locator(`[data-testid="${testid}"]`);
    await node.scrollIntoViewIfNeeded().catch(() => {});
    await node.fill(String(value)).catch((e) => page.__fillErrors.push(`${testid}:${String(e.message).slice(0, 70)}`));
  };
  const press = async (testid) => {
    const node = page.locator(`[data-testid="${testid}"]`);
    const count = await node.count().catch(() => -1);
    if (count !== 1) { page.__fillErrors.push(`${testid}:count=${count}`); return; }
    await node.scrollIntoViewIfNeeded().catch(() => {});
    await node.click({ timeout: 6000 }).catch((e) => page.__fillErrors.push(`${testid}:click:${String(e.message).slice(0, 70)}`));
  };
  await setField("trial-city", "厦门");
  await setField("trial-arrival", "厦门高崎国际机场 T4");
  await setField("trial-departure", "厦门站");
  page.__dom.push({ at: "step1_filled", state: await domState(page) });
  await press("trial-next");
  await page.waitForTimeout(900);
  page.__dom.push({ at: "on_step2", state: await domState(page) });
  await setField("trial-party", "4");
  await setField("trial-budget", "4321");
  await setField("trial-special", "需要无障碍通道 · B2c");
  await press("trial-next");
  await page.waitForTimeout(900);
  page.__dom.push({ at: "on_step3", state: await domState(page) });
  await press("trial-create");
  page.__dom.push({ at: "after_create_click", state: await domState(page) });
  return page.evaluate((k) => localStorage.getItem(k), DRAFT_KEY);
}

(async () => {
  const ctx = await chromium.launchPersistentContext(PROFILE, {
    viewport: { width: 390, height: 844 }, isMobile: true, hasTouch: true,
    deviceScaleFactor: 2, locale: "zh-CN", timezoneId: "Asia/Shanghai",
  });
  await ctx.addInitScript(observer);
  const page = ctx.pages()[0] || (await ctx.newPage());
  page.__fillErrors = [];
  page.__dom = [];
  const consoleErrors = [], pageErrors = [];
  const netWrites = [];
  page.on("console", (m) => { if (m.type() === "error") consoleErrors.push(m.text().slice(0, 160)); });
  page.on("pageerror", (e) => pageErrors.push(String(e && e.message).slice(0, 160)));
  page.on("request", (r) => { if (!["GET", "HEAD"].includes(r.method())) netWrites.push({
    method: r.method(), url: r.url().replace(BASE, ""), at: Date.now() }); });

  const inflight = () => page.evaluate(async () => {
    try { const r = await fetch("/__admin/inflight", { cache: "no-store" }); return await r.json(); }
    catch (e) { return { error: String(e && e.message).slice(0, 80) }; }
  });

  await page.goto(BASE + "/", { waitUntil: "domcontentloaded", timeout: 40000 })
    .catch((e) => pageErrors.push("goto:" + String(e.message).slice(0, 90)));
  await page.waitForTimeout(PHASE === "install" ? 9000 : 6000);

  let draftBefore = null, swapInfo = null, samples = [];
  if (PHASE === "b2c" || PHASE === "idle") {
    if (PHASE === "b2c") draftBefore = await fillWizard(page);
    else await page.locator('[data-testid="trial-city"]').scrollIntoViewIfNeeded().catch(() => {});
    const doSwap = async () => page.evaluate(async () => {
      const r = await fetch("/__admin/swap", { cache: "no-store" });
      const j = await r.json().catch(() => null);
      const reg = await navigator.serviceWorker.getRegistration("/");
      let after = null;
      if (reg) { try { await reg.update(); } catch (e) {}
                 after = { installing: reg.installing && reg.installing.state,
                           waiting: reg.waiting && reg.waiting.state,
                           active: reg.active && reg.active.state }; }
      return { swap_response: j, registration_after_update: after };
    });
    if (PHASE === "idle") {
      /* The control that keeps the fix honest: with nothing outstanding, the same handover must converge
         immediately.  An arm that only ever defers would pass B2c's write case and fail here. */
      const before = await inflight();
      swapInfo = { writes_open_before_swap: before, ...(await doSwap().catch((e) => ({
        error: String(e && e.message).slice(0, 120) }))) };
    } else {
      await page.locator('[data-testid="trial-create"]').click().catch(() => {});
      let held = null;
      for (let i = 0; i < 12; i += 1) {
        const s = await inflight();
        if ((s.writes_open || 0) >= 1) { held = s; break; }
        await page.waitForTimeout(500);
      }
      swapInfo = held ? { held_at_swap: held, ...(await doSwap().catch((e) => ({
        error: String(e && e.message).slice(0, 120) })) ) }
        : { error: "NO_WRITE_WAS_HELD - the arm cannot judge B2c without an open non-idempotent request" };
    }
    for (let i = 0; i < WINDOW; i += 1) {
      await page.waitForTimeout(1000);
      const s = await page.evaluate(async (keys) => ({
        t_s: Math.round(performance.now() / 10) / 10,
        wall: Date.now(),
        bundle: ((document.querySelector('script[type="module"]') || {}).src || "").replace(location.origin, "") || null,
        gen_tag: window.__cnxGenerationTag || null,
        loads: JSON.parse(sessionStorage.getItem("cnx274loads") || "[]").length,
        reload_key: sessionStorage.getItem(keys.reload),
        pending_key: sessionStorage.getItem(keys.pending),
        draft_present: Boolean(localStorage.getItem(keys.draft)),
        mounted: Boolean(document.querySelector("#root") && document.querySelector("#root").children.length),
        events: (window.__cnx274 || {}).events || [],
      }), { reload: RELOAD_KEY, pending: PENDING_KEY, draft: DRAFT_KEY }).catch(() => ({ dead: true }));
      const fly = await inflight();
      s.writes_open = fly.writes_open === undefined ? null : fly.writes_open;
      s.open_writes = fly.open || null;
      samples.push(s);
    }
  }

  const seen = await page.evaluate(async (keys) => {
    const reg = await navigator.serviceWorker.getRegistration("/");
    const node = document.querySelector('script[type="module"]') || {};
    return {
      loads: JSON.parse(sessionStorage.getItem("cnx274loads") || "[]"),
      probe_events: (window.__cnx274 || {}).events || [],
      gen_tag: window.__cnxGenerationTag || null,
      executing_bundle: node.src ? node.src.replace(location.origin, "") : null,
      controller_now: navigator.serviceWorker.controller
        ? navigator.serviceWorker.controller.scriptURL.replace(location.origin, "") : null,
      registrations: reg ? [{ scope: reg.scope.replace(location.origin, ""),
                             active: reg.active && reg.active.scriptURL.replace(location.origin, ""),
                             waiting: reg.waiting && reg.waiting.scriptURL.replace(location.origin, ""),
                             waiting_state: reg.waiting && reg.waiting.state }] : [],
      reload_key: sessionStorage.getItem(keys.reload),
      pending_key: sessionStorage.getItem(keys.pending),
      draft: localStorage.getItem(keys.draft),
      mounted: Boolean(document.querySelector("#root") && document.querySelector("#root").children.length),
      onLine: navigator.onLine,
    };
  }, { reload: RELOAD_KEY, pending: PENDING_KEY, draft: DRAFT_KEY })
    .catch((e) => ({ evaluate_error: String(e && e.message).slice(0, 160) }));

  const bytes = await byteIdentity(page);
  const result = { phase: PHASE, at: new Date().toISOString(), base: BASE, window_s: WINDOW,
                   seen, executed_bytes: bytes, draft_before_submit: draftBefore,
                   swap_request: swapInfo, samples, net_writes: netWrites.slice(0, 12),
                   fill_errors: page.__fillErrors.slice(0, 8), dom_trace: page.__dom,
                   console_errors: consoleErrors.slice(0, 6), page_errors: pageErrors.slice(0, 4),
                   profile: PROFILE };
  fs.writeFileSync(OUT, JSON.stringify(result, null, 1), "utf8");
  const fly = samples.filter((s) => (s.writes_open || 0) > 0).length;
  console.log(`${PHASE}: tag=${seen.gen_tag} bundle=${(seen.executing_bundle || "").slice(-22)} `
    + `sha=${(bytes.sha256 || "").slice(0, 12)} loads=${(seen.loads || []).length} `
    + `reload_key=${JSON.stringify(seen.reload_key)} pending=${JSON.stringify(seen.pending_key)} `
    + `samples_with_open_write=${fly} -> ${path.basename(OUT)}`);
  await ctx.close();
})().catch((e) => { console.error("PROBE THREW: " + (e && e.stack || e)); process.exit(9); });
