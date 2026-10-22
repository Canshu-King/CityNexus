/* ORD-0715 screen proof, arm four: same ladder as arm three, but the pasted text is an argument.

Why the paste needs to be a parameter: each write consumes the journey's addable places -- the second run
against the same store answers "already on that day" and paints no success sentence at all, which would
read as "the line disappeared" rather than "there was nothing to add".  Two locales, two different place
names, one store.

argv: node walk_import_day_source_r4.cjs <base> <out.json> <zh|en> [shot.png] [pasted text]
*/
const { chromium } = require("D:/moodle/_qoder_phone_ord0485_20260930/tip_walk/frontend/node_modules/playwright");
const fs = require("fs");

const BASE = process.argv[2] || "http://127.0.0.1:4899";
const OUT = process.argv[3] || "D:/moodle/_qoder_phone_ord0485_20260930/evidence/import_day_source_r4.json";
const WANT = process.argv[4] === "en" ? "en" : "zh";
const SHOT = process.argv[5] || "";
const PASTE = process.argv[6] || "Central Food Hall 午饭";
const CODE = /\b[A-Z][A-Z0-9_]{4,}\b/g;
const run = { schema: "CNX_IMPORT_DAY_SOURCE_R4", base: BASE, want_locale: WANT, paste: PASTE,
  viewport: { width: 390, height: 844 }, started: new Date().toString(), page_errors: [],
  outcome: "INCOMPLETE" };

const text = (page, testid) => page.evaluate((t) => { const el = document.querySelector("[data-testid='" + t + "']");
  return el ? String(el.textContent || "").replace(/\s+/g, " ").trim() : null; }, testid);

async function press(page, testid, tag) {
  const loc = page.locator("[data-testid='" + testid + "']").first();
  if (!(await loc.count())) return { tag, testid, pressed: false, why: "TESTID_NOT_IN_DOM" };
  await loc.evaluate((e) => e.scrollIntoViewIfNeeded()).catch(() => {});
  await page.waitForTimeout(250);
  const box = await loc.boundingBox();
  if (!box) return { tag, testid, pressed: false, why: "NO_BOX" };
  if (await loc.evaluate((e) => !!e.disabled || e.getAttribute("aria-disabled") === "true"))
    return { tag, testid, pressed: false, why: "CONTROL_DISABLED", box: [Math.round(box.width), Math.round(box.height)] };
  const hit = await page.evaluate(([t, x, y]) => { const self = document.querySelector("[data-testid='" + t + "']");
    const el = document.elementFromPoint(x, y);
    if (!el || !self) return { ok: false, what: el ? (el.getAttribute("data-testid") || el.tagName) : null };
    return { ok: self === el || self.contains(el), what: el.getAttribute("data-testid") || el.tagName }; },
  [testid, box.x + box.width / 2, box.y + box.height / 2]);
  if (!hit.ok) return { tag, testid, pressed: false, why: "CENTRE_LANDS_ON_" + hit.what };
  try { await loc.click({ timeout: 6000 }); } catch (e) {
    return { tag, testid, pressed: false, why: "CLICK_THREW_" + String(e).slice(0, 40) }; }
  await page.waitForTimeout(1400);
  return { tag, testid, pressed: true, box: [Math.round(box.width), Math.round(box.height)] };
}

/* Two statements on the glass are only two statements if they are not glued: measure the rendered boxes. */
async function lineShape(page) {
  return await page.evaluate(() => {
    const a = document.querySelector("[data-testid='poi-import-added']");
    const b = document.querySelector("[data-testid='poi-import-added-source']");
    if (!a || !b) return null;
    const ra = a.getBoundingClientRect(), rb = b.getBoundingClientRect();
    const range = document.createRange();
    range.selectNodeContents(a);
    return { added_box: [Math.round(ra.width), Math.round(ra.height)],
      source_box: [Math.round(rb.width), Math.round(rb.height)],
      source_starts_below_added: rb.top >= ra.top + (ra.height / 2),
      source_display: getComputedStyle(b).display,
      added_text: String(a.textContent || "").replace(/\s+/g, " ").trim(),
      glued: /[a-z)\.] ?[A-Z][a-z]/.test(String(a.textContent || "").slice(-90))
        && !/[.。]\s/.test(String(a.textContent || "")) };
  });
}

(async () => {
  const browser = await chromium.launch();
  const ctx = await browser.newContext({ viewport: { width: 390, height: 844 }, deviceScaleFactor: 2,
    isMobile: true, hasTouch: true, serviceWorkers: "block" });
  const page = await ctx.newPage();
  page.on("pageerror", (e) => run.page_errors.push(String(e).slice(0, 200)));
  await page.goto(BASE + "/", { waitUntil: "networkidle", timeout: 60000 });
  await page.waitForTimeout(1200);
  const demo = page.locator("[data-testid='trial-tianjin-demo']").first();
  if (await demo.count()) { await demo.evaluate((e) => e.scrollIntoViewIfNeeded()); await demo.click(); }
  await page.waitForTimeout(2000);
  run.lang_before_toggle = await page.evaluate(() => document.documentElement.lang || null);
  if ((run.lang_before_toggle || "").toLowerCase().indexOf(WANT) !== 0) {
    run.toggle_press = await press(page, "topbar-language", "toggle_language");
    await page.waitForTimeout(1200);
  } else {
    run.toggle_press = { tag: "toggle_language", pressed: false, why: "ALREADY_IN_WANTED_LOCALE" };
  }
  run.lang_after_toggle = await page.evaluate(() => document.documentElement.lang || null);
  run.locale_reached = (run.lang_after_toggle || "").toLowerCase().indexOf(WANT) === 0;
  if (!run.locale_reached) {
    fs.writeFileSync(OUT, JSON.stringify(Object.assign(run, { outcome: "ABORT_LOCALE_NOT_REACHED" }), null, 1));
    console.log(JSON.stringify({ outcome: "ABORT_LOCALE_NOT_REACHED", want: WANT,
      before: run.lang_before_toggle, after: run.lang_after_toggle }));
    await browser.close();
    process.exitCode = 3;
    return;
  }
  await press(page, "v8-mobile-menu", "open_drawer");
  const entry = await page.evaluate(() => { const s = (x) => String(x || "").replace(/\s+/g, " ").trim();
    const el = Array.from(document.querySelectorAll("[data-testid^='v8-drawer-entry-']"))
      .find((e) => /导入地点|Import|import/i.test(s(e.innerText)));
    return el ? el.getAttribute("data-testid") : null; });
  run.drawer_entry_words = entry ? await text(page, entry) : null;
  if (entry) await press(page, entry, "entry_import");
  await press(page, "poi-import-mode-text", "text_mode");
  await page.locator("[data-testid='poi-import-text']").first().fill(PASTE);
  await page.waitForTimeout(600);
  run.parse_press = await press(page, "poi-import-parse", "parse");
  await page.waitForTimeout(2600);
  run.counts = await text(page, "poi-import-counts");
  run.select_all_press = await press(page, "poi-import-select-all", "select_all");
  run.add_press = await press(page, "poi-import-add", "add");
  await page.waitForTimeout(3400);
  if (SHOT) await page.screenshot({ path: SHOT });
  run.added_line = await text(page, "poi-import-added");
  run.added_source_words = await text(page, "poi-import-added-source");
  run.already_present_line = await text(page, "poi-import-already-present");
  run.line_shape = await lineShape(page);
  if (await page.locator("[data-testid='poi-import-added-source-fold']").count()) {
    await page.evaluate(() => { const d = document.querySelector("[data-testid='poi-import-added-source-fold']");
      if (d) d.open = true; });
    await page.waitForTimeout(400);
  }
  run.token_after_open = await text(page, "poi-import-added-source-token");
  run.codes_in_traveller_cells = [];
  for (const cell of [run.added_line, run.added_source_words, run.already_present_line]) {
    const m = cell ? cell.match(CODE) : null;
    if (m) run.codes_in_traveller_cells.push(...Array.from(new Set(m)));
  }
  run.outcome = "COMPLETE";
  fs.writeFileSync(OUT, JSON.stringify(run, null, 1));
  console.log(JSON.stringify({ outcome: run.outcome, want: WANT, paste: PASTE, entry_words: run.drawer_entry_words,
    counts: run.counts, add_press: run.add_press, added_line: run.added_line,
    added_source_words: run.added_source_words, already: run.already_present_line,
    line_shape: run.line_shape, token_after_open: run.token_after_open,
    codes_in_traveller_cells: run.codes_in_traveller_cells, page_errors: run.page_errors.length }, null, 1));
  await browser.close();
})();
