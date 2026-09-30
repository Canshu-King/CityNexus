/* ORD-0485 -- the share legs on the phone, walked as a person walks them.
 *
 * Owner side: /v8/access -> pick the trip -> pick a visibility -> 发出邀请 -> open the token
 * fold, and read the token out of the RENDERED SENTENCE, not out of an attribute.
 * Visitor side: a fresh profile with no journey on the device opens /v8/shared/<token>, and
 * then the same address with a broken token, so the refusal is read too.
 */
const { chromium } = require("D:\\moodle\\_qoder_phone_ord0485_20260930\\export\\frontend\\node_modules\\playwright");
const fs = require("fs");
const path = require("path");

const BASE = "http://127.0.0.1:4861";
const OUT_DIR = "D:/moodle/_qoder_phone_ord0485_20260930/evidence/share_r1";
const W = 390, H = 844;
fs.mkdirSync(OUT_DIR, { recursive: true });

const run = { schema: "CNX_PHONE_SHARE_R1", base: BASE, started_local: new Date().toString(),
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
      rendered_text_chars: bodyText.length,
      rendered_text_full: bodyText,
      visible_testids: all("[data-testid]").map((e) => e.getAttribute("data-testid")),
      visible_buttons: all("button,a,summary").map((e) => strip(e.innerText)).filter((x) => x),
      visible_headings: all("h1,h2,h3,legend").map((e) => strip(e.innerText)).filter((x) => x),
      key_lookalikes: (() => {
        const hits = bodyText.match(/[A-Za-z][A-Za-z0-9]{2,}\.[A-Za-z][A-Za-z0-9]+/g) || [];
        const snake = bodyText.match(/[A-Z][A-Z0-9]{2,}(?:_[A-Z0-9]+)+/g) || [];
        return Array.from(new Set(hits.concat(snake)));
      })(),
    };
  });
  const row = {
    arm: tag, route_read_from_location: snap.path,
    rendered_text_chars: snap.rendered_text_chars,
    rendered_text_head: snap.rendered_text_full.slice(0, 1500),
    visible_testid_count: snap.visible_testids.length,
    visible_testids: snap.visible_testids,
    visible_buttons: snap.visible_buttons.slice(0, 60),
    visible_headings: snap.visible_headings,
    machine_or_key_lookalikes: snap.key_lookalikes,
    page_errors_total_at_read: run.page_errors,
    extra: extra || null,
  };
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
    if (r.method() !== "GET") run.writes.push({ arm: label, method: r.method(), url: r.url() });
  });
  page.on("pageerror", (e) => {
    run.page_errors += 1;
    (run.page_error_list = run.page_error_list || []).push({ arm: label,
      text: String(e && e.message ? e.message : e).slice(0, 200) });
  });
}

(async () => {
  const browser = await chromium.launch();

  // ---- owner: issue the invitation through the screen itself ---------------
  const owner = await browser.newContext({ viewport: { width: W, height: H }, hasTouch: true,
    isMobile: true, locale: "zh-CN" });
  const op = await owner.newPage();
  arm(op, "owner_access");
  await op.goto(BASE + "/", { waitUntil: "domcontentloaded" });
  await op.waitForTimeout(5000);
  await op.locator("[data-testid='trial-tianjin-demo']").first().click({ timeout: 8000 });
  await op.waitForTimeout(10000);
  await op.locator("[data-testid='v8-mobile-menu']").first().click({ timeout: 8000 });
  await op.waitForTimeout(1200);
  await op.locator("[data-testid='v8-drawer-entry-access']").first().click({ timeout: 8000 });
  await op.waitForTimeout(6000);
  await readScreen(op, "H1_access_before_choice");

  const picker = op.locator("[data-testid='access-journey-picker']");
  const options = await picker.evaluate((el) => Array.from(el.options).map((o) => ({
    value: o.value, label: o.textContent.trim() })));
  const real = options.find((o) => o.value);
  run.owner_picker_options = options;
  if (real) {
    await picker.selectOption(real.value);
    await op.waitForTimeout(7000);
  }
  const vis = op.locator("[data-testid='access-invite-visibility']");
  const vopts = await vis.evaluate((el) => Array.from(el.options).map((o) => o.value));
  run.owner_visibility_options = vopts;
  const wantLevel = vopts.includes("LINK_READ") ? "LINK_READ" : vopts[vopts.length - 1];
  await vis.selectOption(wantLevel);
  await op.waitForTimeout(800);
  const submit = op.locator("[data-testid='access-invite-submit']");
  run.submit_disabled_before = await submit.evaluate((e) => !!e.disabled);
  await submit.click({ timeout: 8000 });
  await op.waitForTimeout(7000);
  const issued = await readScreen(op, "H2_access_after_invite");
  issued.screenshot = await shot(op, "H2_after_invite");
  issued.expected_level_chosen = wantLevel;

  // open the token fold and read the sentence the traveller reads
  const summary = op.locator("[data-testid='access-grant-row'] summary").first();
  run.grant_rows_in_dom = await op.locator("[data-testid='access-grant-row']").count();
  if ((await summary.count()) > 0) {
    await summary.click({ timeout: 6000 });
    await op.waitForTimeout(1500);
  }
  const foldText = await op.evaluate(() => {
    const rows = Array.from(document.querySelectorAll("[data-testid='access-grant-row']"));
    return rows.map((r) => (r.innerText || "").replace(/\s+/g, " ").trim());
  });
  run.grant_row_rendered_text = foldText;
  const m = (foldText.join(" ").match(/([A-Za-z0-9_-]{20,})/) || []);
  const token = m[1] || null;
  run.token_read_from_rendered_sentence = token;
  const fold = await readScreen(op, "H3_access_token_fold_open");
  fold.screenshot = await shot(op, "H3_token_fold");
  await owner.close();

  // ---- visitor: a device that owns no journey ------------------------------
  const guest = await browser.newContext({ viewport: { width: W, height: H }, hasTouch: true,
    isMobile: true, locale: "zh-CN" });
  const gp = await guest.newPage();
  arm(gp, "guest_shared");
  if (token) {
    await gp.goto(BASE + "/v8/shared/" + token, { waitUntil: "domcontentloaded" });
    await gp.waitForTimeout(7000);
    const g = await readScreen(gp, "H4_shared_receive_with_token");
    g.screenshot = await shot(gp, "H4_receive");
  } else {
    run.screens.push({ arm: "H4_shared_receive_with_token", ABORT: "NO_TOKEN_ON_SCREEN" });
  }
  await gp.goto(BASE + "/v8/shared/" + (token ? token.slice(0, -4) + "ZZZZ" : "nottoken"),
    { waitUntil: "domcontentloaded" });
  await gp.waitForTimeout(6000);
  const bad = await readScreen(gp, "H5_shared_receive_bad_token");
  bad.screenshot = await shot(gp, "H5_bad_token");

  await gp.goto(BASE + "/v8/shared/", { waitUntil: "domcontentloaded" });
  await gp.waitForTimeout(5000);
  await readScreen(gp, "H6_shared_no_token_at_all");
  await guest.close();

  run.finished_local = new Date().toString();
  fs.writeFileSync(path.join(OUT_DIR, "share_r1.json"), JSON.stringify(run, null, 2), "utf8");
  console.log("SCREENS=" + run.screens.length + " WRITES=" + run.writes.length +
    " PAGEERRORS=" + run.page_errors + " TOKEN_FROM_SCREEN=" + (token ? "yes" : "no") +
    " GRANT_ROWS=" + run.grant_rows_in_dom);
  await browser.close();
})().catch((e) => {
  run.FATAL = String(e && e.stack ? e.stack : e).slice(0, 800);
  fs.writeFileSync(path.join(OUT_DIR, "share_r1.json"), JSON.stringify(run, null, 2), "utf8");
  console.log("FATAL_SEE_JSON");
  process.exitCode = 1;
});
