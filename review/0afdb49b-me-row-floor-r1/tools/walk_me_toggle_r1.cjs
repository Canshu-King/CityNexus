/* Building walk: can a person actually switch the auto-execution setting on a phone?

The painted-box census found this control at 13x13 -- the smallest pressable thing measured anywhere in the
phone chain, and it is the one gate that decides whether the agent may act without asking.  Before changing
any CSS or any word, the fact to establish is what a traveller who does not know where the tiny box is would
experience: they read the sentence and tap it.  So this probe taps the LABEL and the row, not the input, and
reads the state word before and after, then restores it.

A control whose label is not a working target is a different defect from a control that is merely small, and
the two need different fixes -- which is why this tool reports both, and decides nothing itself.

argv: node walk_me_toggle_r1.cjs <base> <out.json> <shot.png>
 */
const { chromium } = require("D:/moodle/_qoder_phone_ord0485_20260930/tip_walk/frontend/node_modules/playwright");
const fs = require("fs");
const path = require("path");

const BASE_URL = process.argv[2] || "http://127.0.0.1:4894";
const OUT = process.argv[3] || "D:/moodle/_qoder_phone_ord0485_20260930/evidence/me_toggle.json";
const SHOT = process.argv[4] || "D:/moodle/_qoder_phone_ord0485_20260930/evidence/me_toggle.png";

const run = { schema: "CNX_BUILDING_ME_TOGGLE_R1", base: BASE_URL, viewport: { width: 390, height: 844 },
  started: new Date().toString(), steps: [], readings: [], presses: [], verdict: null,
  page_errors: [], console_errors: [] };

async function readState(page, tag) {
  return await page.evaluate((tag) => {
    const strip = (x) => String(x || "").replace(/\s+/g, " ").trim();
    const box = (el) => { if (!el) return null; const b = el.getBoundingClientRect();
      return { x: Math.round(b.x), y: Math.round(b.y), w: Math.round(b.width), h: Math.round(b.height) }; };
    const hits = (el) => { if (!el) return null; const b = el.getBoundingClientRect();
      const top = document.elementFromPoint(b.left + b.width / 2, b.top + b.height / 2);
      return !!top && (top === el || el.contains(top) || (top.contains && top.contains(el))); };
    const input = document.querySelector("[data-testid='me-mode-toggle']");
    const label = input ? (input.closest("label") || (input.id ? document.querySelector("label[for='" + input.id + "']") : null)) : null;
    const row = input ? input.closest("li,div,p,section") : null;
    const words = row ? strip(row.innerText) : null;
    const stateWord = (() => {
      const t = strip((row ? row.innerText : "") + " " + (document.body.innerText || ""));
      const on = /自动执行已开启|已开启自动执行|自动执行 开/.test(t);
      const off = /仅提供建议|开启自动执行/.test(t);
      return { on, off, both: on && off };
    })();
    return { tag, path: location.pathname,
             input: { box: box(input), checked: input ? input.checked : null,
                      type: input ? input.type : null, clickable_at_centre: hits(input),
                      aria: input ? (input.getAttribute("aria-label") || null) : null,
                      id: input ? (input.id || null) : null },
             label: label ? { text: strip(label.innerText).slice(0, 80), box: box(label),
                              clickable_at_centre: hits(label), tagName: label.tagName } : null,
             row: row ? { text: words ? words.slice(0, 160) : null, box: box(row) } : null,
             state: stateWord,
             body_tail: strip(document.body.innerText).slice(-320) };
  }, tag);
}

async function tapAt(page, selector, tag, where) {
  const loc = page.locator(selector).first();
  if (await loc.count() === 0) return { tag, pressed: false, why: "NO_SUCH_ELEMENT" };
  const geo = await loc.evaluate((el, where) => {
    el.scrollIntoViewIfNeeded();
    const b = el.getBoundingClientRect();
    const x = where === "centre" ? b.left + b.width / 2 : b.left + 8;
    const y = b.top + b.height / 2;
    const top = document.elementFromPoint(x, y);
    return { x: Math.round(x), y: Math.round(y), w: Math.round(b.width), h: Math.round(b.height),
             landed: !!top && (top === el || el.contains(top) || (top.contains && top.contains(el))),
             hit_tag: top ? top.tagName : null,
             hit_testid: top && top.getAttribute ? (top.getAttribute("data-testid") || null) : null };
  }, where);
  if (!geo.landed) return { tag, pressed: false, why: "HIT_TEST_MISSED", geo };
  await page.touchscreen.tap(geo.x, geo.y);
  await page.waitForTimeout(1200);
  return { tag, pressed: true, geo };
}

(async () => {
  const browser = await chromium.launch();
  const ctx = await browser.newContext({ viewport: { width: 390, height: 844 }, deviceScaleFactor: 2,
    isMobile: true, hasTouch: true, serviceWorkers: "block" });
  const page = await ctx.newPage();
  page.on("pageerror", (e) => run.page_errors.push(String(e).slice(0, 200)));
  page.on("console", (m) => { if (m.type() === "error") run.console_errors.push(m.text().slice(0, 200)); });

  await page.goto(BASE_URL + "/", { waitUntil: "networkidle", timeout: 60000 });
  await page.waitForTimeout(1200);
  const anchor = page.locator("[data-testid='trial-tianjin-demo']").first();
  if (await anchor.count()) { await anchor.evaluate((el) => el.scrollIntoViewIfNeeded()); await anchor.click(); }
  await page.waitForTimeout(1600);
  run.steps.push({ tag: "open_drawer", ...(await (async () => {
    const loc = page.locator("[data-testid='v8-mobile-menu']").first();
    await loc.evaluate((el) => el.scrollIntoViewIfNeeded());
    await loc.click(); await page.waitForTimeout(900);
    return { pressed: true };
  })()) });
  run.steps.push(await tapAt(page, "[data-testid='v8-drawer-entry-me']", "enter_me", "centre"));
  await page.waitForTimeout(1200);

  const before = await readState(page, "before");
  run.readings.push(before);

  const SEL = "[data-testid='me-mode-toggle']";
  const labelSel = await page.evaluate((sel) => {
    const el = document.querySelector(sel);
    if (!el) return null;
    const lab = el.closest("label") || (el.id ? document.querySelector("label[for='" + el.id + "']") : null);
    if (!lab) return null;
    lab.setAttribute("data-cnx-label-probe", "1");
    return "[data-cnx-label-probe='1']";
  }, SEL);
  const tapLabel = labelSel
    ? await tapAt(page, labelSel, "tap_the_words_not_the_box", "left")
    : { tag: "tap_the_words_not_the_box", pressed: false, why: "NO_LABEL_ELEMENT" };
  run.presses.push(tapLabel);
  const afterLabel = await readState(page, "after_tapping_the_words");
  run.readings.push(afterLabel);

  let restored = null;
  if (afterLabel.state.on !== before.state.on || afterLabel.input.checked !== before.input.checked) {
    const back = await tapAt(page, "[data-testid='me-mode-toggle']", "tap_to_restore", "centre");
    run.presses.push(back);
    restored = await readState(page, "after_restore");
    run.readings.push(restored);
  }
  fs.mkdirSync(path.dirname(SHOT), { recursive: true });
  await page.screenshot({ path: SHOT, fullPage: true });
  run.shot = SHOT;

  const changed = (afterLabel.input.checked !== before.input.checked)
    || (afterLabel.state.on !== before.state.on);
  const labelIsSeparateTarget = !!before.label && before.label.text && before.label.text !== "";
  run.changed_by_control_itself = changed;
  run.label_present = labelIsSeparateTarget;
  run.restored = restored ? (restored.input.checked === before.input.checked) : null;
  if (!before.input.box) run.verdict = "NO_TOGGLE_ON_SCREEN";
  else if (!changed) run.verdict = "TAP_ON_CONTROL_DID_NOT_CHANGE_STATE";
  else if (before.input.box.h < 44) run.verdict = "STATE_CHANGES_BUT_TARGET_IS_UNDER_FLOOR";
  else run.verdict = "OK";
  run.finished = new Date().toString();
  fs.mkdirSync(path.dirname(OUT), { recursive: true });
  fs.writeFileSync(OUT, JSON.stringify(run, null, 1));
  console.log(JSON.stringify({ verdict: run.verdict, path: before.path,
    input_box: before.input.box, input_checked: before.input.checked,
    label: before.label, row_text: before.row ? before.row.text : null,
    changed_by_control_itself: run.changed_by_control_itself,
    after: { box: afterLabel.input.box, checked: afterLabel.input.checked, state: afterLabel.state },
    restored: run.restored, presses: run.presses,
    page_errors: run.page_errors.length, console_errors: run.console_errors.length }, null, 1));
  await browser.close();
})();
