/* Building walk, cell eleven, arm three: close the 「导入地点」 loop the way a person must, and read the
 * 「足迹」 screen against the server.

Arms one and two of this instrument taught me two things, both recorded here so the next reader does not
repeat them:
  * the demo journey's city is CNX-DEMO and its catalogue holds eight English-named places, so pasting
    Chinese sight names correctly answers "对上 0 个" -- that is the data, not a defect;
  * 「加进计划」 is disabled until rows are ticked, and the tick is a `role="checkbox"` element, not an
    <input type=checkbox>, so a census that only looks for inputs reports a screen with no selectors at all.

This arm therefore drives the real ladder: paste -> 识别 -> tick rows (both the per-row box and 全选可加的行,
measuring each box as it goes) -> 加进计划 -> read the success sentence off the glass and compare it with a
fresh request from the same page, then open 足迹 and compare its tally with a fresh GET of the same rows the
panel claims to show.

argv: node walk_import_footprint_r3.cjs <base> <out.json> [shotdir]
*/
const { chromium } = require("D:/moodle/_qoder_phone_ord0485_20260930/tip_walk/frontend/node_modules/playwright");
const fs = require("fs");
const path = require("path");

const BASE = process.argv[2] || "http://127.0.0.1:4895";
const OUT = process.argv[3] || "D:/moodle/_qoder_phone_ord0485_20260930/evidence/import_footprint_r3.json";
const SHOTS = process.argv[4] || "";
const PASTE = ["Nexus City Park 傍晚散步", "Riverside Museum", "Old Town Gate 城门", "Design Library",
  "一家没听过的馆子"].join("\n");
const SEL = "button,[role='button'],[role='checkbox'],a[href],input[type='submit']";

const run = { schema: "CNX_IMPORT_FOOTPRINT_R3", base: BASE, viewport: { width: 390, height: 844 },
  started: new Date().toString(), steps: [], page_errors: [], console_errors: [], outcome: "INCOMPLETE" };

async function snap(page, tag) {
  return await page.evaluate(([tag, SEL]) => {
    const s = (x) => String(x || "").replace(/\s+/g, " ").trim();
    const vis = (el) => { const b = el.getBoundingClientRect(); const c = getComputedStyle(el);
      return b.width > 0 && b.height > 0 && c.display !== "none" && c.visibility !== "hidden"
        && Number(c.opacity) !== 0; };
    const testids = {};
    for (const el of document.querySelectorAll("[data-testid]")) {
      const t = el.getAttribute("data-testid");
      if (!testids[t]) testids[t] = { n: 0, visible: 0, words: [], boxes: [] };
      testids[t].n += 1;
      if (vis(el)) { const b = el.getBoundingClientRect();
        testids[t].visible += 1;
        testids[t].boxes.push([Math.round(b.width), Math.round(b.height)]);
        const w = s(el.innerText || el.getAttribute("aria-label") || el.value);
        if (w && testids[t].words.length < 4) testids[t].words.push(w.slice(0, 110)); }
    }
    const controls = Array.from(document.querySelectorAll(SEL)).filter(vis).map((el) => {
      const b = el.getBoundingClientRect();
      // elementFromPoint only answers inside the viewport: below the fold reads as "not on screen", and
      // counting that as "covered" once reported nine healthy buttons as unreachable.
      const on_screen = b.top >= 0 && b.bottom <= window.innerHeight && b.left >= 0 && b.right <= window.innerWidth;
      const hit = on_screen ? document.elementFromPoint(b.left + b.width / 2, b.top + b.height / 2) : null;
      return { testid: el.getAttribute("data-testid") || null, role: el.getAttribute("role") || el.tagName,
        words: s(el.innerText || el.getAttribute("aria-label") || el.value).slice(0, 40),
        w: Math.round(b.width), h: Math.round(b.height), top: Math.round(b.top), on_screen,
        checked: el.getAttribute("aria-checked") || (el.checked === true ? "true" : null),
        disabled: !!el.disabled || el.getAttribute("aria-disabled") === "true" ? true : null,
        centre_on_self: !!hit && (hit === el || el.contains(hit)) }; });
    const doc = document.documentElement;
    return { tag, path: location.pathname, body: s(document.body.innerText).slice(0, 1200), testids,
      controls, controls_under_44: controls.filter((c) => c.h < 44).length,
      controls_off_screen: controls.filter((c) => !c.on_screen).length,
      controls_covered: controls.filter((c) => c.on_screen && !c.centre_on_self).length,
      horizontal_overflow: doc.scrollWidth > doc.clientWidth + 2 };
  }, [tag, SEL]);
}

async function press(page, testid, tag, nth) {
  const loc = page.locator("[data-testid='" + testid + "']").nth(nth || 0);
  if (!(await loc.count())) return { tag, testid, pressed: false, why: "TESTID_NOT_IN_DOM" };
  await loc.evaluate((e) => e.scrollIntoViewIfNeeded()).catch(() => {});
  await page.waitForTimeout(250);
  const box = await loc.boundingBox();
  if (!box) return { tag, testid, pressed: false, why: "NO_BOX" };
  const st = await loc.evaluate((e) => ({ disabled: !!e.disabled || e.getAttribute("aria-disabled") === "true" }));
  if (st.disabled) return { tag, testid, pressed: false, why: "CONTROL_DISABLED",
    box: [Math.round(box.width), Math.round(box.height)] };
  const hit = await page.evaluate(([x, y]) => { const el = document.elementFromPoint(x, y);
    return el ? (el.getAttribute("data-testid") || el.tagName) : null; },
  [box.x + box.width / 2, box.y + box.height / 2]);
  if (hit !== testid) return { tag, testid, pressed: false, why: "CENTRE_LANDS_ON_" + hit,
    box: [Math.round(box.width), Math.round(box.height)] };
  try { await loc.click({ timeout: 6000 }); } catch (e) {
    return { tag, testid, pressed: false, why: "CLICK_THREW_" + String(e).slice(0, 50),
      box: [Math.round(box.width), Math.round(box.height)] }; }
  await page.waitForTimeout(1400);
  return { tag, testid, pressed: true, box: [Math.round(box.width), Math.round(box.height)] };
}

const word = (snap, testid) => (((snap.testids[testid] || {}).words || [])[0] || null);

async function openDrawerEntry(page, words) {
  await press(page, "v8-mobile-menu", "open_drawer_for_" + words);
  const testid = await page.evaluate((words) => {
    const s = (x) => String(x || "").replace(/\s+/g, " ").trim();
    const el = Array.from(document.querySelectorAll("[data-testid^='v8-drawer-entry-']"))
      .find((e) => s(e.innerText).indexOf(words) >= 0);
    return el ? el.getAttribute("data-testid") : null;
  }, words);
  if (testid) await press(page, testid, "entry_" + words);
  return testid;
}

(async () => {
  if (SHOTS && !fs.existsSync(SHOTS)) fs.mkdirSync(SHOTS, { recursive: true });
  const browser = await chromium.launch();
  const ctx = await browser.newContext({ viewport: { width: 390, height: 844 }, deviceScaleFactor: 2,
    isMobile: true, hasTouch: true, serviceWorkers: "block" });
  const page = await ctx.newPage();
  page.on("pageerror", (e) => run.page_errors.push(String(e).slice(0, 200)));
  page.on("console", (m) => { if (m.type() === "error") run.console_errors.push(m.text().slice(0, 160)); });
  await page.goto(BASE + "/", { waitUntil: "networkidle", timeout: 60000 });
  await page.waitForTimeout(1200);
  const demo = page.locator("[data-testid='trial-tianjin-demo']").first();
  if (await demo.count()) { await demo.evaluate((e) => e.scrollIntoViewIfNeeded()); await demo.click(); }
  await page.waitForTimeout(1800);
  run.journey_id = await page.evaluate(() => localStorage.getItem("citynexus.v8.journey_id"));

  /* ---------- 导入地点 ---------- */
  run.import_entry = await openDrawerEntry(page, "导入地点");
  let st = await snap(page, "import_opened");
  run.steps.push({ step: "import_opened", snap: st });
  await press(page, "poi-import-mode-text", "text_mode");
  await page.locator("[data-testid='poi-import-text']").first().fill(PASTE);
  await page.waitForTimeout(600);
  run.steps.push({ step: "import_after_paste", snap: await snap(page, "import_after_paste") });
  run.import_parse_press = await press(page, "poi-import-parse", "press_parse");
  await page.waitForTimeout(2600);
  st = await snap(page, "import_after_parse");
  run.steps.push({ step: "import_after_parse", snap: st });
  if (SHOTS) await page.screenshot({ path: path.join(SHOTS, "import_after_parse.png") });
  run.import_counts = word(st, "poi-import-counts");
  run.import_selection_before = word(st, "poi-import-selection-count");
  run.import_add_disabled_before = (st.controls.find((c) => c.testid === "poi-import-add") || {}).disabled;
  run.import_pick_boxes = st.controls.filter((c) => c.testid === "poi-card-select")
    .map((c) => ({ box: [c.w, c.h], top: c.top, on_screen: c.on_screen, checked: c.checked }));
  run.import_select_all_box = st.controls.filter((c) => c.testid === "poi-import-select-all")
    .map((c) => ({ box: [c.w, c.h], on_screen: c.on_screen, checked: c.checked }));

  // step one a person can take: tick ONE row with its own box, and see whether the glass answers
  run.import_row_press = await press(page, "poi-card-select", "press_first_row_select", 0);
  st = await snap(page, "import_after_row_tick");
  run.steps.push({ step: "import_after_row_tick", snap: st });
  run.import_selection_after_row = word(st, "poi-import-selection-count");
  run.import_add_state_after_row = st.controls.filter((c) => c.testid === "poi-import-add")
    .map((c) => ({ disabled: !!c.disabled, box: [c.w, c.h] }));
  if (SHOTS) await page.screenshot({ path: path.join(SHOTS, "import_after_row_tick.png") });

  // step two: the row that ticks them all
  run.import_select_all_press = await press(page, "poi-import-select-all", "press_select_all");
  st = await snap(page, "import_after_select_all");
  run.steps.push({ step: "import_after_select_all", snap: st });
  run.import_selection_after_all = word(st, "poi-import-selection-count");

  // step three: write.  The glass must then say what the server took, in words.
  run.import_add_press = await press(page, "poi-import-add", "press_add");
  await page.waitForTimeout(3200);
  st = await snap(page, "import_after_add");
  run.steps.push({ step: "import_after_add", snap: st });
  if (SHOTS) await page.screenshot({ path: path.join(SHOTS, "import_after_add.png") });
  run.import_added_words = word(st, "poi-import-added");
  run.import_added_source = word(st, "poi-import-added-source");
  run.import_already_present = word(st, "poi-import-already-present");
  run.import_readback_failed = word(st, "poi-import-readback-failed");
  run.import_open_plan_words = word(st, "poi-import-open-plan");
  const plan = await page.evaluate(async (j) => {
    const r = await fetch("/api/v1/journeys/" + encodeURIComponent(j) + "/plans", { headers: { accept: "application/json" } });
    const j2 = await r.json().catch(() => null);
    const arr = Array.isArray(j2) ? j2 : (j2 && (j2.items || j2.plans)) || [];
    const items = (arr[0] && (arr[0].items || arr[0].stops)) || [];
    return { http_status: r.status, plans: Array.isArray(arr) ? arr.length : null,
      first_plan_items: items.length,
      first_plan_titles: items.slice(0, 12).map((x) => String(x.place_name || x.title || "").slice(0, 30)) };
  }, run.journey_id);
  run.server_plans = plan;

  /* ---------- 足迹 ---------- */
  run.footprint_entry = await openDrawerEntry(page, "足迹");
  st = await snap(page, "footprint_opened");
  run.steps.push({ step: "footprint_opened", snap: st });
  if (SHOTS) await page.screenshot({ path: path.join(SHOTS, "footprint_opened.png") });
  run.footprint_tally_words = word(st, "footprint-tally");
  run.footprint_empty_words = word(st, "footprint-empty");
  run.footprint_rows = st.controls.filter((c) => c.testid === "footprint-row").length;
  run.server_checkins = await page.evaluate(async (j) => {
    const r = await fetch("/api/v1/journeys/" + encodeURIComponent(j) + "/checkins", { headers: { accept: "application/json" } });
    const b = await r.json().catch(() => null);
    const items = Array.isArray(b) ? b : (b && (b.items || b.checkins || b.data)) || [];
    return { http_status: r.status, n: Array.isArray(items) ? items.length : null,
      payload_keys: b && typeof b === "object" && !Array.isArray(b) ? Object.keys(b).slice(0, 10) : null };
  }, run.journey_id);
  run.footprint_empty_action_words = word(st, "footprint-empty-action");
  if (run.footprint_empty_action_words) {
    run.footprint_empty_action_press = await press(page, "footprint-empty-action", "press_empty_action");
    st = await snap(page, "footprint_after_empty_action");
    run.steps.push({ step: "footprint_after_empty_action", snap: st });
    if (SHOTS) await page.screenshot({ path: path.join(SHOTS, "footprint_after_empty_action.png") });
    run.after_action_path = st.path;
    run.after_action_checkin_controls = st.controls
      .filter((c) => /checkin|打卡/.test(String(c.testid) + c.words))
      .map((c) => ({ testid: c.testid, words: c.words, box: [c.w, c.h], on_screen: c.on_screen }));
  }
  run.outcome = "COMPLETE";
  fs.writeFileSync(OUT, JSON.stringify(run, null, 1));
  console.log(JSON.stringify({ outcome: run.outcome, counts: run.import_counts,
    selection: [run.import_selection_before, run.import_selection_after_row, run.import_selection_after_all],
    pick_boxes: run.import_pick_boxes, select_all_box: run.import_select_all_box,
    row_press: run.import_row_press, select_all_press: run.import_select_all_press,
    add_press: run.import_add_press, added: run.import_added_words, added_source: run.import_added_source,
    already: run.import_already_present, readback_failed: run.import_readback_failed,
    server_plans: run.server_plans, footprint_tally: run.footprint_tally_words,
    server_checkins: run.server_checkins, empty_action: run.footprint_empty_action_words,
    empty_action_press: run.footprint_empty_action_press, after_action_path: run.after_action_path,
    page_errors: run.page_errors.length, console_errors: run.console_errors.length }, null, 1));
  await browser.close();
})();
