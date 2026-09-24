/**
 * ORD-0274 B2b: does the traveller's half-filled trip survive the automatic convergence, value by value?
 *
 * B2b is not "the draft key still exists".  The contract is per value: `step` must come back, and city /
 * partySize / budget / specialRequirements (plus the two dates) must be EQUAL one by one, while the bundle
 * the document executes really moves old -> new.  A reload that restores the fields but drops the step, or
 * restores the step onto empty fields, is still RED - so this probe reads both the stored draft AND the
 * rendered inputs, and reports them side by side.
 *
 * Nothing is submitted here: the wizard is filled and left open, so the only thing that changes the page is
 * the product's own handover.  The probe performs one navigation; every later load is the product's.
 *
 * usage: node q274_b2b_probe.js --base URL --profile DIR --out FILE --window 60
 */
const path = require("path");
const fs = require("fs");
const PW = "D:/moodle/_qoder_integration_20260919/frontend/node_modules/playwright";
const { chromium } = require(PW);
function arg(n, d) { const i = process.argv.indexOf("--" + n); return i === -1 ? d : process.argv[i + 1]; }

const BASE = arg("base"), PROFILE = arg("profile"), OUT = arg("out");
const WINDOW = Number(arg("window", "60"));
/* Which generation the judge expects to land in.  Each B2b arm converges into its OWN target
   bundle (the restoring code is the incoming one), so the marker is a parameter, not a constant. */
const TARGET_TAG = arg("tag", "gen2-standin");
const DRAFT_KEY = "citynexus.v8.trial_draft";
const RELOAD_KEY = "citynexus.sw.controller-transition";
const PENDING_KEY = "citynexus.sw.generation-handover-pending";

/* The fields B2b names, plus the two dates.  Values are deliberately unlike the product defaults
   (defaultDraft is 2 people / 3000 / "" / relaxed), so a restore that silently fell back to defaults
   cannot pass a per-value comparison. */
const TYPED = {
  "trial-city": "厦门",
  "trial-arrival": "厦门高崎国际机场 T4",
  "trial-departure": "厦门站",
  "trial-party": "4",
  "trial-budget": "4321",
  "trial-special": "需要无障碍通道 · B2b",
  /* the two dates are typed too: `startAt`/`endAt` default to futureLocalAt(1,10)/(3,20), so leaving them
     alone would compare a default against itself and call that "dates preserved". */
  "trial-start": "2026-10-05T08:30",
  "trial-end": "2026-10-09T19:45",
};
const READ_IDS = ["trial-city", "trial-arrival", "trial-departure", "trial-party", "trial-budget",
                  "trial-special", "trial-start", "trial-end"];

function observer() {
  const w = window;
  w.__cnx274b = { events: [], loads: JSON.parse(sessionStorage.getItem("cnx274loads") || "[]") };
  const id = w.__cnx274b.loads.length + 1;
  w.__cnx274b.loads.push({ id, at: Date.now(), gen_tag: w.__cnxGenerationTag || null });
  sessionStorage.setItem("cnx274loads", JSON.stringify(w.__cnx274b.loads));
  const rec = (kind, extra) => w.__cnx274b.events.push(Object.assign(
    { kind, load_id: id, t: Date.now(), iso: new Date().toISOString() }, extra || {}));
  rec("document-start", { gen_tag: w.__cnxGenerationTag || null });
  w.addEventListener("citynexus:generation-handover-pending", () => rec("handover-pending"));
  navigator.serviceWorker.addEventListener("controllerchange", () => rec("controllerchange"));
}

/* page.evaluate runs in the browser, so nothing from this file's scope reaches it: the id list and the
   storage keys are passed in as the argument. */
async function screenState(page) {
  return page.evaluate((payload) => {
    const val = (testid) => {
      const n = document.querySelector(`[data-testid="${testid}"]`);
      if (!n) return { present: false };
      return { present: true, value: String(n.value !== undefined && n.value !== "" ? n.value
                                          : (n.innerText || "")).slice(0, 60),
               raw: n.value !== undefined ? n.value : null,
               tag: n.tagName.toLowerCase(), type: n.getAttribute("type") };
    };
    /* The product marks the current step two ways, and both are on screen: the list item carries
       className "active"/"done"/"", and only the current step's body is rendered.  `aria-current` is not
       used here, so reading it would have reported nothing and I would have judged the step off the
       storage key alone - which is the side a mutant can keep honest while the screen lies. */
    const stepMarks = Array.from(document.querySelectorAll('[data-testid^="trial-step-"]')).map((n) => ({
      id: n.getAttribute("data-testid"),
      class_name: String(n.className || "").slice(0, 24),
      marker: (n.querySelector(".trial-step-dot") || {}).innerText || null,
    }));
    const bodyMarks = ["trial-step1-body", "trial-step2-body", "trial-step3-body", "trial-review-body"]
      .filter((t) => document.querySelector(`[data-testid="${t}"]`));
    const draftRaw = localStorage.getItem(payload.keys.draft);
    let draft = null;
    try { draft = draftRaw ? JSON.parse(draftRaw) : null; } catch (e) { draft = { parse_error: true }; }
    return {
      gen_tag: window.__cnxGenerationTag || null,
      executing_bundle: ((document.querySelector('script[type="module"]') || {}).src || "")
        .replace(location.origin, "") || null,
      fields: Object.fromEntries(payload.ids.map((id) => [id, val(id)])),
      step_marks: stepMarks,
      visible_bodies: bodyMarks,
      onboarding_present: Boolean(document.querySelector('[data-testid="trial-setup"]')),
      submit_label: ((document.querySelector('[data-testid="trial-create"]') || {}).innerText || "").slice(0, 20),
      cta_text: ((document.querySelector('[data-testid="trial-sticky-cta"]') || {}).innerText || "").slice(0, 80),
      draft,
      loads: JSON.parse(sessionStorage.getItem("cnx274loads") || "[]").length,
      reload_key: sessionStorage.getItem(payload.keys.reload),
      pending_key: sessionStorage.getItem(payload.keys.pending),
      mounted: Boolean((document.querySelector("#root") || { children: { length: 0 } }).children.length),
    };
  }, { ids: READ_IDS, keys: { draft: DRAFT_KEY, reload: RELOAD_KEY, pending: PENDING_KEY } });
}

(async () => {
  const ctx = await chromium.launchPersistentContext(PROFILE, {
    viewport: { width: 390, height: 844 }, isMobile: true, hasTouch: true,
    deviceScaleFactor: 2, locale: "zh-CN", timezoneId: "Asia/Shanghai",
  });
  await ctx.addInitScript(observer);
  const page = ctx.pages()[0] || (await ctx.newPage());
  const errs = [], perrs = [];
  page.on("console", (m) => { if (m.type() === "error") errs.push(m.text().slice(0, 150)); });
  page.on("pageerror", (e) => perrs.push(String(e && e.message).slice(0, 150)));

  await page.goto(BASE + "/", { waitUntil: "domcontentloaded", timeout: 40000 })
    .catch((e) => perrs.push("goto:" + String(e.message).slice(0, 90)));
  await page.waitForTimeout(7000);

  const setAndCheck = async (testid, value) => {
    const node = page.locator(`[data-testid="${testid}"]`);
    if ((await node.count().catch(() => -1)) !== 1) { errs.push(`${testid}:count`); return; }
    await node.scrollIntoViewIfNeeded().catch(() => {});
    await node.fill(String(value)).catch((e) => errs.push(`${testid}:fill:${String(e.message).slice(0, 50)}`));
  };
  const press = async (testid) => {
    const node = page.locator(`[data-testid="${testid}"]`);
    if ((await node.count().catch(() => -1)) !== 1) { errs.push(`${testid}:press:count`); return; }
    await node.scrollIntoViewIfNeeded().catch(() => {});
    await node.click({ timeout: 6000 }).catch((e) => errs.push(`${testid}:press:${String(e.message).slice(0, 50)}`));
  };

  await setAndCheck("trial-city", TYPED["trial-city"]);
  await page.waitForTimeout(600);
  await setAndCheck("trial-arrival", TYPED["trial-arrival"]);
  await setAndCheck("trial-departure", TYPED["trial-departure"]);
  /* Both dates live on step 1, so they are typed there; the product's own defaults are
     futureLocalAt(1,10) / futureLocalAt(3,20), and a comparison against those would compare a default. */
  await setAndCheck("trial-start", TYPED["trial-start"]);
  await setAndCheck("trial-end", TYPED["trial-end"]);
  const beforeStep1 = await screenState(page);
  await press("trial-next");
  await page.waitForTimeout(900);
  await setAndCheck("trial-party", TYPED["trial-party"]);
  await setAndCheck("trial-budget", TYPED["trial-budget"]);
  await setAndCheck("trial-special", TYPED["trial-special"]);
  const beforeSwap = await screenState(page);

  const swap = await page.evaluate(async () => {
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

  const samples = [];
  for (let i = 0; i < WINDOW; i += 1) {
    await page.waitForTimeout(1000);
    const s = await screenState(page).catch(() => ({ dead: true }));
    s.t_s = i + 1;
    samples.push(s);
    if (s.gen_tag === TARGET_TAG) break;
  }
  const afterOnLandedStep = samples.length ? samples[samples.length - 1] : {};
  /* The wizard renders only the CURRENT step's body, so the fields that live on step 1 are not in the DOM
     while the page sits on step 2 - reading them there would report "missing" for values that are perfectly
     preserved.  So the traveller's own way of checking is used: go back, and read them on their own screen.
     Both sides of every comparison are taken on the step where that field actually renders. */
  let afterOnStep1 = null, backPress = null;
  if ((afterOnLandedStep.draft || {}).step === 2 || (afterOnLandedStep.visible_bodies || []).includes("trial-step2-body")) {
    const back = page.locator('[data-testid="trial-back"]');
    backPress = { present: (await back.count().catch(() => -1)) === 1 };
    if (backPress.present) {
      await back.scrollIntoViewIfNeeded().catch(() => {});
      await back.click({ timeout: 6000 }).catch((e) => { backPress.error = String(e.message).slice(0, 60); });
      await page.waitForTimeout(900);
      afterOnStep1 = await screenState(page);
    }
  }
  const after = Object.assign({}, afterOnLandedStep);
  const bytes = await page.evaluate(async () => {
    const ref = ((document.querySelector('script[type="module"]') || {}).src || "");
    if (!ref) return { ref: null, sha256: null };
    const r = await fetch(ref, { cache: "no-store" });
    const buf = await r.arrayBuffer();
    const d = await crypto.subtle.digest("SHA-256", buf);
    return { ref: ref.replace(location.origin, ""), bytes: buf.byteLength,
             content_type: r.headers.get("content-type") || "",
             sha256: Array.from(new Uint8Array(d)).map((b) => b.toString(16).padStart(2, "0")).join("") };
  }).catch(() => ({ error: "byte_read_failed" }));

  const result = { at: new Date().toISOString(), base: BASE, window_s: WINDOW,
                   before_step1: beforeStep1, before_swap: beforeSwap, swap,
                   samples, after, after_on_landed_step: afterOnLandedStep,
                   after_on_step1: afterOnStep1, back_press: backPress,
                   executed_bytes: bytes,
                   probe_events: (await page.evaluate(() => (window.__cnx274b || {}).events || []).catch(() => [])),
                   loads: await page.evaluate(() => JSON.parse(sessionStorage.getItem("cnx274loads") || "[]"))
                     .catch(() => []),
                   console_errors: errs.slice(0, 8), page_errors: perrs.slice(0, 4), profile: PROFILE };
  fs.writeFileSync(OUT, JSON.stringify(result, null, 1), "utf8");
  const f = (after.fields) || {};
  console.log(`b2b: tag=${after.gen_tag} step_marks=${JSON.stringify(after.step_marks).slice(0, 70)} `
    + `city=${JSON.stringify((f["trial-city"] || {}).value)} party=${JSON.stringify((f["trial-party"] || {}).value)} `
    + `budget=${JSON.stringify((f["trial-budget"] || {}).value)} draft_step=${((after.draft || {}).step)} `
    + `loads=${(result.loads || []).length} sha=${(bytes.sha256 || "").slice(0, 12)} -> ${path.basename(OUT)}`);
  await ctx.close();
})().catch((e) => { console.error("PROBE THREW: " + (e && e.stack || e)); process.exit(9); });
