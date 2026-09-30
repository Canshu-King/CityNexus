/* ORD-0485 -- two cells share_r1 could not close:
 *   J1  the receiving screen opened with a token that is STILL LIVE (share_r1 read the first
 *       grant row, whose token had been revoked, so the visitor arm showed the revoked refusal --
 *       a true reading of a revoked grant and not the live one this cell asks for);
 *   J2  the whole create-a-trip leg on a phone: pick a city, name the anchors, step to the
 *       review, confirm, and watch what the screen says while the server works.
 *
 * Every write is captured with its HTTP status, because "the phone demoed it" has to name the
 * route that answered.
 */
const { chromium } = require("D:\\moodle\\_qoder_phone_ord0485_20260930\\export\\frontend\\node_modules\\playwright");
const fs = require("fs");
const path = require("path");

const BASE = "http://127.0.0.1:4861";
const OUT_DIR = "D:/moodle/_qoder_phone_ord0485_20260930/evidence/wizard_r1";
const W = 390, H = 844;
fs.mkdirSync(OUT_DIR, { recursive: true });

const run = { schema: "CNX_PHONE_WIZARD_R1", base: BASE, started_local: new Date().toString(),
  screens: [], writes: [], page_errors: 0 };

async function readScreen(page, tag, extra) {
  const snap = await page.evaluate(() => {
    const vis = (el) => {
      if (!el) return false;
      const b = el.getBoundingClientRect();
      const s = getComputedStyle(el);
      return b.width > 0 && b.height > 0 && s.display !== "none" &&
        s.visibility !== "hidden" && Number(s.opacity) !== 0;
    };
    const all = (sel) => Array.from(document.querySelectorAll(sel)).filter(vis);
    const strip = (s) => String(s || "").replace(/\s+/g, " ").trim();
    const bodyText = document.body.innerText || "";
    return {
      path: location.pathname,
      chars: bodyText.length,
      head: bodyText.slice(0, 1600),
      testids: all("[data-testid]").map((e) => e.getAttribute("data-testid")),
      buttons: all("button,a,summary").map((e) => strip(e.innerText)).filter((x) => x),
      headings: all("h1,h2,h3,legend").map((e) => strip(e.innerText)).filter((x) => x),
      busy_text: (() => {
        const el = document.querySelector("[data-testid='trial-wait-outcome'], .trial-phase, [data-testid='trial-create-error']");
        return el ? strip(el.innerText) : null;
      })(),
      lookalikes: Array.from(new Set(
        (bodyText.match(/[A-Za-z][A-Za-z0-9]{2,}\.[A-Za-z][A-Za-z0-9]+/g) || [])
          .concat(bodyText.match(/[A-Z][A-Z0-9]{2,}(?:_[A-Z0-9]+)+/g) || []))),
    };
  });
  const row = { arm: tag, route_read_from_location: snap.path, rendered_text_chars: snap.chars,
    rendered_text_head: snap.head, visible_testid_count: snap.testids.length,
    visible_testids: snap.testids, visible_buttons: snap.buttons.slice(0, 60),
    visible_headings: snap.headings, machine_or_key_lookalikes: snap.lookalikes,
    page_errors_total_at_read: run.page_errors, extra: extra || null };
  run.screens.push(row);
  return row;
}

async function shot(page, name) {
  const file = path.join(OUT_DIR, name.replace(/[^A-Za-z0-9_.-]/g, "_") + ".png");
  try {
    await page.screenshot({ path: file, timeout: 9000, animations: "disabled" });
    return { png: path.basename(file), bytes: fs.statSync(file).size };
  } catch (e) {
    return { png: null, reason: "SHOT_NOT_TAKEN_" + String(e.message).slice(0, 60) };
  }
}

function arm(page, label) {
  page.on("request", (r) => {
    if (r.method() !== "GET") pending.push({ arm: label, method: r.method(), url: r.url() });
  });
  page.on("response", async (res) => {
    const req = res.request();
    if (req.method() === "GET") return;
    let status = null;
    try { status = res.status(); } catch (e) { status = "STATUS_UNREADABLE"; }
    run.writes.push({ arm: label, method: req.method(), url: req.url(), http_status: status });
  });
  page.on("pageerror", (e) => {
    run.page_errors += 1;
    (run.page_error_list = run.page_error_list || []).push({ arm: label,
      text: String(e && e.message ? e.message : e).slice(0, 200) });
  });
}
const pending = [];

(async () => {
  const browser = await chromium.launch();

  // ---- J1: a grant that is still live --------------------------------------
  const owner = await browser.newContext({ viewport: { width: W, height: H }, hasTouch: true,
    isMobile: true, locale: "zh-CN" });
  const op = await owner.newPage();
  arm(op, "owner_access_live");
  await op.goto(BASE + "/", { waitUntil: "domcontentloaded" });
  await op.waitForTimeout(5000);
  await op.locator("[data-testid='trial-tianjin-demo']").first().click({ timeout: 8000 });
  await op.waitForTimeout(9000);
  await op.locator("[data-testid='v8-mobile-menu']").first().click({ timeout: 8000 });
  await op.waitForTimeout(1200);
  await op.locator("[data-testid='v8-drawer-entry-access']").first().click({ timeout: 8000 });
  await op.waitForTimeout(5000);
  await op.locator("[data-testid='access-journey-picker']").selectOption(
    (await op.locator("[data-testid='access-journey-picker'] option").evaluateAll(
      (os) => os.map((o) => o.value).filter((v) => v)))[0]);
  await op.waitForTimeout(6000);
  await op.locator("[data-testid='access-invite-visibility']").selectOption("INVITEES_ONLY");
  await op.locator("[data-testid='access-invite-submit']").click({ timeout: 8000 });
  await op.waitForTimeout(6000);
  // open EVERY grant row's own fold, then read the token out of each row's rendered sentence
  const rowInfo = await op.evaluate(() => {
    const rows = Array.from(document.querySelectorAll("[data-testid='access-grant-row']"));
    return rows.map((r, i) => ({ index: i, open: !!(r.querySelector("details") || {}).open,
      text: (r.innerText || "").replace(/\s+/g, " ").trim() }));
  });
  const summaries = op.locator("[data-testid='access-grant-row'] details summary");
  const n = await summaries.count();
  for (let i = 0; i < n; i += 1) {
    try { await summaries.nth(i).click({ timeout: 4000 }); } catch (e) { }
  }
  await op.waitForTimeout(1200);
  const rowsAfter = await op.evaluate(() => Array.from(
    document.querySelectorAll("[data-testid='access-grant-row']")).map((r) =>
    (r.innerText || "").replace(/\s+/g, " ").trim()));
  run.grant_rows_before_folds = rowInfo;
  run.grant_rows_after_folds = rowsAfter;
  const live = rowsAfter.find((t) => !/撤销。/.test(t) && /邀请令牌/.test(t)) || null;
  const lm = live ? (live.match(/邀请令牌（服务器原样给的）：([A-Za-z0-9_-]{16,})/) || []) : [];
  const liveToken = lm[1] || null;
  run.live_token_read_from_rendered_sentence = liveToken;
  run.live_row_text = live;
  const own = await readScreen(op, "J1_access_with_live_grant");
  own.screenshot = await shot(op, "J1_access_live");
  await owner.close();

  const guest = await browser.newContext({ viewport: { width: W, height: H }, hasTouch: true,
    isMobile: true, locale: "zh-CN" });
  const gp = await guest.newPage();
  arm(gp, "guest_live");
  if (liveToken) {
    await gp.goto(BASE + "/v8/shared/" + liveToken, { waitUntil: "domcontentloaded" });
    await gp.waitForTimeout(7000);
    const g = await readScreen(gp, "J2_shared_receive_live_token");
    g.screenshot = await shot(gp, "J2_receive_live");
  } else {
    run.screens.push({ arm: "J2_shared_receive_live_token", ABORT: "NO_LIVE_TOKEN_ON_SCREEN" });
  }
  await guest.close();

  // ---- J2: the create-a-trip leg, typed and stepped like a traveller -------
  const ctx = await browser.newContext({ viewport: { width: W, height: H }, hasTouch: true,
    isMobile: true, locale: "zh-CN" });
  const wp = await ctx.newPage();
  arm(wp, "wizard");
  await wp.goto(BASE + "/", { waitUntil: "domcontentloaded" });
  await wp.waitForTimeout(5000);
  await readScreen(wp, "K1_wizard_step1_empty");

  // the blocked button must answer out loud before anything is typed
  const next = wp.locator("[data-testid='trial-next']");
  await next.click({ timeout: 6000 }).catch((e) => run.wizard_blocked_click_error =
    String(e.message).slice(0, 90));
  await wp.waitForTimeout(700);
  run.wizard_blocked_reason_text = await wp.evaluate(() => {
    const hint = document.querySelector("[data-testid='trial-required-hint']");
    const spoken = document.querySelector("[data-testid='trial-next-reason']");
    const vis = (el) => { if (!el) return false; const b = el.getBoundingClientRect();
      return b.width > 0 && b.height > 0; };
    const btn = document.querySelector("[data-testid='trial-next']");
    return { hint_visible: !!hint && vis(hint), hint: hint ? hint.innerText.trim() : null,
      spoken: spoken ? spoken.innerText.trim() : null,
      aria_disabled: btn ? btn.getAttribute("aria-disabled") : null,
      disabled_attribute: btn ? !!btn.disabled : null };
  });

  await wp.locator("[data-testid='trial-city']").fill("天津");
  await wp.waitForTimeout(2500);
  const inferred = await wp.evaluate(() => {
    const el = document.querySelector("[data-testid='trial-inferred']");
    const warn = document.querySelector("[data-testid='trial-city-warning']");
    return { inferred: el ? el.innerText.trim() : null, warning: warn ? warn.innerText.trim() : null };
  });
  run.wizard_city_recognition = inferred;
  await wp.locator("[data-testid='trial-arrival']").fill("天津站");
  await wp.locator("[data-testid='trial-departure']").fill("滨海国际机场");
  await readScreen(wp, "K2_wizard_step1_filled");
  await next.click({ timeout: 6000 });
  await wp.waitForTimeout(2500);
  await readScreen(wp, "K3_wizard_step2");
  await next.click({ timeout: 6000 });
  await wp.waitForTimeout(2500);
  await readScreen(wp, "K4_wizard_review");
  const create = wp.locator("[data-testid='trial-create']");
  await create.click({ timeout: 8000 });
  const samples = [];
  for (let i = 0; i < 24; i += 1) {
    await wp.waitForTimeout(10000);
    const s = await wp.evaluate(() => {
      const strip = (x) => String(x || "").replace(/\s+/g, " ").trim();
      const q = (sel) => document.querySelector(sel);
      const err = q("[data-testid='trial-create-error']");
      const phase = q(".trial-phase, [data-testid='trial-phase']");
      return { path: location.pathname,
        wizard_mounted: !!q("[data-testid='trial-setup']"),
        busy: !!q("[data-testid='trial-sticky-cta']") &&
          /正在|Reading|Creating|搜索/.test(strip(document.body.innerText)),
        phase: phase ? strip(phase.innerText) : null,
        error: err ? strip(err.innerText) : null,
        cta: strip((q("[data-testid='trial-sticky-cta']") || {}).innerText || ""),
        chars: (document.body.innerText || "").length };
    });
    samples.push(Object.assign({ at_seconds: (i + 1) * 10 }, s));
    if (!s.wizard_mounted || s.error) break;
  }
  run.wizard_wait_samples = samples;
  const landed = await readScreen(wp, "K5_after_wait");
  landed.screenshot = await shot(wp, "K5_after_wait");
  landed.journeys_on_server = null;
  run.wizard_final_route = landed.route_read_from_location;
  await ctx.close();

  run.finished_local = new Date().toString();
  fs.writeFileSync(path.join(OUT_DIR, "wizard_r1.json"), JSON.stringify(run, null, 2), "utf8");
  console.log("SCREENS=" + run.screens.length + " WRITES=" + run.writes.length +
    " PAGEERRORS=" + run.page_errors + " LIVE_TOKEN=" + (liveToken ? "yes" : "no") +
    " WAIT_SAMPLES=" + samples.length + " FINAL_ROUTE=" + run.wizard_final_route);
  await browser.close();
})().catch((e) => {
  run.FATAL = String(e && e.stack ? e.stack : e).slice(0, 800);
  fs.writeFileSync(path.join(OUT_DIR, "wizard_r1.json"), JSON.stringify(run, null, 2), "utf8");
  console.log("FATAL_SEE_JSON");
  process.exitCode = 1;
});
