/* _agent_dp2_scan_r1.cjs — two-theme paired sweep with a TEXT-FREE join key.
 *
 * Why this exists: _cmdr_dark_pair_scan_r2.cjs pairs the light and dark readings by
 *   screen || selector || testid || innerText.slice(0,18)
 * (its line 63). Any element whose rendered text moves between the two page loads
 * (live clocks, "just now" strings, async tile labels, status words) gets a different key in the
 * two runs, silently leaves the paired set, and is therefore never reported. That is exactly how
 * .v8-agent-progress at 320px escaped the scan while a single-element read caught it.
 *
 * This instrument pairs instead by
 *   screen || tagName || <full class list, sorted> || testid || <nth occurrence of that key in the screen>
 * which never touches text, and keeps a per-screen occurrence counter so two identical cards are
 * compared as two pairs instead of one swallowing the other. When the two runs disagree on how many
 * occurrences a key has, the surplus indices are left unpaired and named in the output.
 *
 * Measurement only. No product file is touched, nothing is built.
 * Usage:  node _agent_dp2_scan_r1.cjs            (full run: 3 widths x 2 arms x 2 themes x 6 screens)
 *         node _agent_dp2_scan_r1.cjs --no-control   (skip the light/light negative control)
 */
const fs = require("fs");
const { chromium } = require("D:/moodle/CityNexus/frontend/node_modules/playwright/index.js");

/* --smoke: one width, real arm only, writes to a scratch file so the delivered readings file stays
   untouched. Used to validate the pairing logic cheaply before the full 72-load sweep. */
const SMOKE = process.argv.indexOf("--smoke") >= 0;
const DO_CONTROL = process.argv.indexOf("--no-control") < 0 && !SMOKE;
const OUT = SMOKE
  ? "D:/moodle/_cmdr_fe_rev_1016/_agent_dp2_readings_smoke.json"
  : "D:/moodle/_cmdr_fe_rev_1016/_agent_dp2_readings.json";
const PAGE_URL = "http://127.0.0.1:8121/";
const JOURNEY_ID = "22222222-2222-4222-8222-222222222222";
const LOCALE = "zh-CN";

const STEPS = [
  ["hub", null],
  ["live", '[data-testid="today-hero-cta"]'],
  ["copilot", '[data-testid="nav-agent"]'],
  ["trips", '[data-testid="nav-trips"]'],
  ["map", '[data-testid="nav-map"]'],
  ["me", '[data-testid="nav-me"]'],
];
const ALL_WIDTHS = [{ w: 1280, h: 860 }, { w: 390, h: 780 }, { w: 320, h: 780 }];
const WIDTHS = SMOKE ? [ALL_WIDTHS[2]] : ALL_WIDTHS;
const ARMS = [{ name: "real", themes: ["light", "dark"] }];
if (DO_CONTROL) ARMS.push({ name: "control_light_vs_light", themes: ["light", "light"] });

/* Red-list criteria (kept exactly as specified; the two lists are never merged). */
const LUM_CUT = 0.72;      // "light fill" threshold on relative luminance
const CONTRAST_CUT = 1.5;  // LIST A: dark ink almost indistinguishable from dark fill
const MIN_PAIRED = 150;    // vacuity guard: paired elements per width must exceed this
const MIN_DISTINCT_HEADINGS = 4;
/* Known-good truth after the landed fix: these two must be clean in both lists. */
const WATCH = [
  { selector: "article.v8-me-card", screen: "me" },
  { selector: "div.v8-agent-progress", screen: "copilot" },
];

function toLinear(c) { c = c / 255.0; return c <= 0.03928 ? c / 12.92 : Math.pow((c + 0.055) / 1.055, 2.4); }
function lumOf(t) { return 0.2126 * toLinear(t[0]) + 0.7152 * toLinear(t[1]) + 0.0722 * toLinear(t[2]); }
function parseRgb(s) {
  const m = /rgba?\(([^)]+)\)/.exec(s || "");
  if (!m) return null;
  const n = m[1].split(",").map((x) => parseFloat(x.trim()));
  if (n.length >= 4 && n[3] === 0) return null;          // fully transparent own background
  if (isNaN(n[0]) || isNaN(n[1]) || isNaN(n[2])) return null;
  return [n[0], n[1], n[2]];
}
function contrast(a, b) { return (Math.max(lumOf(a), lumOf(b)) + 0.05) / (Math.min(lumOf(a), lumOf(b)) + 0.05); }
function r3(n) { return n == null ? null : Math.round(n * 1000) / 1000; }
/* ASCII-escape so CJK heading text cannot mojibake the Windows console; the JSON file keeps real UTF-8. */
function asc(s) { return JSON.stringify(String(s == null ? "" : s)).replace(/[^\x20-\x7e]/g, (c) => "\\u" + c.charCodeAt(0).toString(16).padStart(4, "0") + c.slice(1)); }

/* Runs inside the page. Returns every laid-out visible element in document order plus the page heading.
 *
 * NO viewport clipping here. _cmdr_dark_pair_scan_r2.cjs also dropped anything with
 *   r.top > innerHeight || r.bottom < 0
 * and _agent_dp2_probe_coverage_r1.cjs measured what that costs: .v8-agent-progress on the copilot
 * screen sits at top=925 (w390) / top=989 (w320) while the viewport is 780 tall, so the old scan
 * never read that element at all at narrow widths - a second silent-drop path, independent of the
 * text-in-key bug. `in_view` is recorded instead, as information, never as a filter.
 */
const SNAP = () => {
  const rows = [];
  for (const el of document.querySelectorAll("body *")) {
    if (!el.checkVisibility({ checkOpacity: true, checkVisibilityCSS: true })) continue;
    const b = el.getBoundingClientRect();
    if (b.width < 24 || b.height < 12) continue;
    if (b.width === 0 || b.height === 0) continue;
    const cs = getComputedStyle(el);
    const raw = typeof el.className === "string" ? el.className : (el.getAttribute("class") || "");
    const cls = raw.trim().split(/\s+/).filter(Boolean).sort().join(".");
    /* informational only: nearest own-or-ancestor non-transparent background, never used in a criterion */
    let eff = "rgba(0, 0, 0, 0)";
    for (let a = el; a && a !== document.documentElement; a = a.parentElement) {
      const cb = getComputedStyle(a).backgroundColor;
      const mm = /rgba?\(([^)]+)\)/.exec(cb || "");
      if (mm) { const nn = mm[1].split(",").map((x) => parseFloat(x.trim())); if (!(nn.length >= 4 && nn[3] === 0)) { eff = cb; break; } }
    }
    rows.push({
      tag: el.tagName.toLowerCase(),
      cls,
      tid: el.getAttribute("data-testid") || "",
      own_bg: cs.backgroundColor,
      color: cs.color,
      eff_bg: eff,
      text: (el.innerText || "").replace(/\s+/g, " ").trim(),
      area: Math.round(b.width * b.height),
      vw: Math.round(b.width),
      vh: Math.round(b.height),
      in_view: !(b.top > window.innerHeight || b.bottom < 0),
    });
  }
  const h = document.querySelector(".v8-page h1") || document.querySelector(".v8-page-intro h1");
  return { heading: h ? h.innerText.replace(/\s+/g, " ").trim() : "", rows };
};

async function openScreen(browser, width, height, theme, sel) {
  const page = await browser.newPage({ viewport: { width, height } });
  await page.addInitScript((t) => {
    localStorage.setItem("citynexus.v8.journey_id", "22222222-2222-4222-8222-222222222222");
    localStorage.setItem("citynexus.theme", t);
    localStorage.setItem("citynexus.locale", "zh-CN");
  }, theme);
  await page.goto(PAGE_URL, { waitUntil: "networkidle" });
  await page.waitForTimeout(1800);
  if (sel) {
    /* DOM click(), not a handle click: at wide viewports the bottom nav item has no bounding box,
       which makes Playwright's element click timeout. */
    await page.evaluate((s) => { const e = document.querySelector(s); if (e) e.click(); }, sel);
    await page.waitForTimeout(1200);
  }
  const snap = await page.evaluate(SNAP);
  await page.close();
  return snap;
}

/* Attach the text-free key + per-screen occurrence index to every scanned row. */
function keyRows(rows, screen) {
  const counters = new Map();
  const out = [];
  for (const r of rows) {
    const base = screen + "||" + r.tag + "||" + r.cls + "||" + r.tid;
    const nth = counters.has(base) ? counters.get(base) : 0;
    counters.set(base, nth + 1);
    out.push(Object.assign({}, r, { screen, base, nth, key: base + "||" + nth, selector: r.tag + (r.cls ? "." + r.cls : "") }));
  }
  return { map: out, baseCounts: counters };
}

function buildRow(a, b, width, arm) {
  /* b = second theme run ("dark" in the real arm): every reported colour comes from it. */
  const darkBg = parseRgb(b.own_bg);
  const darkInk = parseRgb(b.color);
  const bgLum = darkBg ? lumOf(darkBg) : null;
  const inkLum = darkInk ? lumOf(darkInk) : null;
  return {
    screen: b.screen,
    width,
    arm,
    selector: b.selector,
    testid: b.tid,
    nth: b.nth,
    key: b.key,
    text: b.text.slice(0, 60),
    dark_bg: b.own_bg,
    dark_color: b.color,
    bg_lum: bgLum == null ? null : r3(bgLum),
    color_lum: inkLum == null ? null : r3(inkLum),
    contrast_dark_bg_vs_dark_color: (darkBg && darkInk) ? r3(contrast(darkBg, darkInk)) : null,
    light_bg: a.own_bg,
    light_color: a.color,
    light_bg_lum: (parseRgb(a.own_bg) ? r3(lumOf(parseRgb(a.own_bg))) : null),
    bg_identical_across_themes: a.own_bg === b.own_bg,
    /* Direct evidence for why the old instrument was blind: r2 joined on innerText.slice(0,18), so a
       pair whose text drifted between the two page loads never matched and was never reported.
       text_stable_across_themes=false means exactly "the r2 key would have dropped this element". */
    light_text: a.text.slice(0, 60),
    text_stable_across_themes: a.text.slice(0, 18) === b.text.slice(0, 18),
    area: b.area,
    box: b.vw + "x" + b.vh,
    in_view_at_load: b.in_view,
    eff_bg_dark: b.eff_bg,
  };
}

function passesFilter(row) {
  return row.bg_lum != null && row.color_lum != null;
}

function listAOf(rows) {
  return rows.filter((x) => passesFilter(x) && x.bg_lum > LUM_CUT && x.contrast_dark_bg_vs_dark_color < CONTRAST_CUT);
}
function listBOf(rows) {
  return rows.filter((x) => passesFilter(x) && x.bg_identical_across_themes && x.bg_lum > LUM_CUT);
}
function dedupe(rows) {
  const m = new Map();
  for (const x of rows) {
    const k = x.screen + "||" + x.selector + "||" + x.testid;
    if (!m.has(k)) {
      m.set(k, {
        screen: x.screen, selector: x.selector, testid: x.testid, sample_text: x.text,
        widths: [], occurrences: 0, max_area: 0, min_contrast: null,
        dark_bg: x.dark_bg, dark_color: x.dark_color, bg_lum: x.bg_lum, color_lum: x.color_lum,
        contrast: x.contrast_dark_bg_vs_dark_color, light_bg: x.light_bg,
        bg_identical_across_themes: x.bg_identical_across_themes, per_reading: [],
      });
    }
    const g = m.get(k);
    g.occurrences += 1;
    g.widths.push(x.width);
    g.max_area = Math.max(g.max_area, x.area);
    if (g.min_contrast == null || x.contrast_dark_bg_vs_dark_color < g.min_contrast) g.min_contrast = x.contrast_dark_bg_vs_dark_color;
    g.per_reading.push({
      width: x.width, nth: x.nth, area: x.area, box: x.box, in_view_at_load: x.in_view_at_load,
      dark_bg: x.dark_bg, light_bg: x.light_bg,
      dark_color: x.dark_color, bg_lum: x.bg_lum, color_lum: x.color_lum,
      contrast: x.contrast_dark_bg_vs_dark_color, bg_identical_across_themes: x.bg_identical_across_themes,
    });
  }
  return Array.from(m.values()).sort((p, q) => q.max_area - p.max_area);
}

(async () => {
  const browser = await chromium.launch({ channel: "chrome", headless: true });
  const problems = [];
  const guard = {
    paired_per_width_per_arm: {}, scanned_per_run: {}, headings_by_screen: {}, text_drift_per_width: {},
    distinct_heading_count_by_run: {}, count_mismatch_keys: [], unpaired_keys: {},
    min_paired_required: MIN_PAIRED, min_distinct_headings_required: MIN_DISTINCT_HEADINGS,
  };
  const tables = {};
  const headingByScreen = {};

  for (const arm of ARMS) {
    for (const width of WIDTHS) {
      const runs = {};
      for (const [screen, sel] of STEPS) {
        runs[screen] = [];
        for (const theme of arm.themes) {
          const snap = await openScreen(browser, width.w, width.h, theme, sel);
          runs[screen].push({ theme, heading: snap.heading, kr: keyRows(snap.rows, screen) });
          const seen = (headingByScreen[screen] = headingByScreen[screen] || {});
          const k = arm.name + "/" + theme + "/" + width.w;
          seen[k] = snap.heading;
        }
      }
      /* --- vacuity guard: wrong screen shows up as a heading that is empty or unstable --- */
      const hs = STEPS.map(([s]) => runs[s][0].heading);
      const distinct = new Set(hs.filter(Boolean)).size;
      guard.distinct_heading_count_by_run[arm.name + "/" + width.w] = distinct;
      if (distinct < MIN_DISTINCT_HEADINGS) {
        problems.push("arm " + arm.name + " width " + width.w + ": only " + distinct
          + " of 6 screen headings are distinct (need >= " + MIN_DISTINCT_HEADINGS + ") - the nav walk did not land on six different screens");
      }
      for (const [screen] of STEPS) {
        const all = [];
        for (const run of runs[screen]) {
          if (!run.heading) problems.push("arm " + arm.name + " width " + width.w + " screen " + screen
            + " theme " + run.theme + ": no visible heading (.v8-page h1 / .v8-page-intro h1) - page did not render the screen");
          all.push(run.heading);
        }
        if (new Set(all).size > 1) {
          problems.push("arm " + arm.name + " width " + width.w + " screen " + screen
            + ": heading differs between runs, so at least one page ended on the wrong screen: " + JSON.stringify(all));
        }
      }

      /* --- pair by text-free key --- */
      const first = arm.themes[0], second = arm.themes[1];
      const mapA = new Map(), mapB = new Map();
      const cntA = new Map(), cntB = new Map();
      const onlyA = new Map(), onlyB = new Map();
      for (const [screen] of STEPS) {
        const rA = runs[screen].find((x) => x.theme === first);
        const rB = runs[screen].find((x) => x.theme === second);
        for (const x of rA.kr.map) mapA.set(x.key, x);
        for (const x of rB.kr.map) mapB.set(x.key, x);
        for (const [k, v] of rA.kr.baseCounts) cntA.set(k, v);
        for (const [k, v] of rB.kr.baseCounts) cntB.set(k, v);
        for (const x of rB.kr.map) if (!mapA.has(x.key)) onlyB.set(x.key, x);
        for (const x of rA.kr.map) if (!mapB.has(x.key)) onlyA.set(x.key, x);
        guard.scanned_per_run[arm.name + "/" + width.w + "/" + screen] = {
          [first]: rA.kr.map.length, [second]: rB.kr.map.length,
        };
      }
      const paired = [];
      for (const [k, b] of mapB) { const a = mapA.get(k); if (a) paired.push(buildRow(a, b, width.w, arm.name)); }
      (tables[arm.name] = tables[arm.name] || {})[width.w] = paired;
      guard.paired_per_width_per_arm[arm.name + "/" + width.w] = paired.length;
      guard.text_drift_per_width[arm.name + "/" + width.w] = {
        paired: paired.length,
        text_changed_between_the_two_runs: paired.filter((x) => !x.text_stable_across_themes).length,
        note: "every row in the second number would have gotten a different join key in the two runs of _cmdr_dark_pair_scan_r2.cjs and left its paired set",
      };
      guard.unpaired_keys[arm.name + "/" + width.w] = {
        second_run_only: Array.from(onlyB.keys()), first_run_only: Array.from(onlyA.keys()),
        second_run_only_count: onlyB.size, first_run_only_count: onlyA.size,
      };
      const mismatches = [];
      for (const [base, n] of cntA) {
        const m = cntB.has(base) ? cntB.get(base) : 0;
        if (m !== n) mismatches.push({ base, first_theme_count: n, second_theme_count: m, note: "occurrence counts differ, indices " + Math.min(n, m) + ".." + Math.max(n, m) + " left unpaired instead of being shifted onto each other" });
      }
      for (const [base, m] of cntB) if (!cntA.has(base)) mismatches.push({ base, first_theme_count: 0, second_theme_count: m, note: "key exists only in the second theme run" });
      if (mismatches.length) guard.count_mismatch_keys.push({ arm: arm.name, width: width.w, mismatches });
    }
  }

  /* --- the two red lists, computed on the real arm only --- */
  const real = tables.real;
  const allReal = [];
  for (const w of Object.keys(real)) for (const x of real[w]) allReal.push(x);
  const rawA = listAOf(allReal), rawB = listBOf(allReal);
  const listA = dedupe(rawA);
  const listB = dedupe(rawB);
  /* How much of what this instrument reports would have been lost to the old text-inclusive key. */
  const oldKeyLoss = {
    listA_raw_pairs: rawA.length,
    listA_pairs_the_r2_text_key_would_have_dropped: rawA.filter((x) => !x.text_stable_across_themes).length,
    listB_raw_pairs: rawB.length,
    listB_pairs_the_r2_text_key_would_have_dropped: rawB.filter((x) => !x.text_stable_across_themes).length,
  };
  /* Diagnostic, deliberately NOT part of either red list: light-fill elements that only one theme run
     produced, so they are outside the paired set by construction. Shown so nothing is silently dropped. */
  const diagUnpaired = [];
  for (const w of Object.keys(real)) {
    const u = guard.unpaired_keys["real/" + w];
    diagUnpaired.push({ width: Number(w), second_only: u.second_run_only_count, first_only: u.first_run_only_count });
  }

  const control = DO_CONTROL ? tables.control_light_vs_light : null;
  const controlAll = [];
  if (control) for (const w of Object.keys(control)) for (const x of control[w]) controlAll.push(x);
  const controlSummary = control ? {
    paired_per_width: Object.keys(control).reduce((o, w) => (o[w] = control[w].length, o), {}),
    listA_count_deduped: dedupe(listAOf(controlAll)).length,
    listB_count_deduped: dedupe(listBOf(controlAll)).length,
    /* definition check: under a same-theme control every background is identical, so LIST B is
       expected to saturate; the discriminating number is how many backgrounds actually differed. */
    bg_identical_count: controlAll.filter((x) => x.bg_identical_across_themes).length,
    bg_differs_count: controlAll.filter((x) => !x.bg_identical_across_themes).length,
    listA: dedupe(listAOf(controlAll)),
  } : null;

  /* --- self-check on the known-good selectors ---
     A watched selector is clean only if the instrument actually PAIRED it at that width
     (coverage) and neither red list names it. Zero coverage is treated as an instrument fault
     (something filtered the element out), not as a pass-by-absence. */
  const selfCheck = [];
  let selfCheckPass = true;
  for (const watch of WATCH) {
    const perWidth = [];
    for (const w of Object.keys(real)) {
      const rows = real[w].filter((x) => x.selector === watch.selector && x.screen === watch.screen);
      const inA = listA.filter((x) => x.selector === watch.selector && x.screen === watch.screen);
      const inB = listB.filter((x) => x.selector === watch.selector && x.screen === watch.screen);
      const bad = rows.length === 0 || inA.length > 0 || inB.length > 0 || rows.some((x) => x.bg_lum == null || x.bg_lum > LUM_CUT);
      if (bad) selfCheckPass = false;
      perWidth.push({
        width: Number(w), paired_occurrences: rows.length, dark_bg: rows[0] ? rows[0].dark_bg : null,
        light_bg: rows[0] ? rows[0].light_bg : null, bg_lum: rows[0] ? rows[0].bg_lum : null,
        dark_color: rows[0] ? rows[0].dark_color : null, contrast: rows[0] ? rows[0].contrast_dark_bg_vs_dark_color : null,
        bg_identical_across_themes: rows.length ? rows.every((x) => x.bg_identical_across_themes) : null,
        in_listA: inA.length, in_listB: inB.length, clean: !bad,
      });
    }
    selfCheck.push({ selector: watch.selector, screen: watch.screen, widths: perWidth });
  }

  guard.headings_by_screen = headingByScreen;
  guard.problems = problems;
  guard.aborted = problems.length > 0;

  const doc = {
    instrument: "_agent_dp2_scan_r1.cjs",
    at: new Date().toISOString(),
    url: PAGE_URL,
    pairing_key: "screen || tagName || sorted full class list || data-testid || nth occurrence index within the screen",
    criteria: {
      listA_invisible_in_dark: "dark own background relative luminance > " + LUM_CUT + " AND contrast(dark own bg, dark computed color) < " + CONTRAST_CUT,
      listB_unpaired_background: "own computed background literally identical in both theme runs AND its luminance > " + LUM_CUT,
      dedupe: "selector + testid + screen; sorted by rendered area descending",
      transparent_own_background: "rows whose own background is rgba(...,0) are excluded from both lists (no luminance to compare)",
    },
    guard,
    self_check: { pass: selfCheckPass, watched: selfCheck },
    old_text_key_loss: oldKeyLoss,
    listA_invisible_in_dark: listA,
    listB_unpaired_background: listB,
    diagnostic_unpaired_occurrences: { per_width: diagUnpaired, note: "outside the paired set; listed so nothing drops silently, NOT merged into LIST A/B" },
    negative_control: controlSummary,
    paired_readings_real_arm: real,
  };
  fs.writeFileSync(OUT, JSON.stringify(doc, null, 1), "utf-8");

  /* --- compact console summary --- */
  console.log("instrument " + doc.instrument + " | page " + PAGE_URL + " | journey " + JOURNEY_ID + " | locale " + asc(LOCALE));
  console.log("paired per width (must be > " + MIN_PAIRED + "):");
  for (const k of Object.keys(guard.paired_per_width_per_arm)) console.log("   " + k + " = " + guard.paired_per_width_per_arm[k]);
  console.log("text drift between the two runs of each width (these are what an innerText join key would drop):");
  for (const k of Object.keys(guard.text_drift_per_width)) console.log("   " + k + " paired=" + guard.text_drift_per_width[k].paired + " text_changed=" + guard.text_drift_per_width[k].text_changed_between_the_two_runs);
  console.log("old-text-key loss on the red lists: " + JSON.stringify(oldKeyLoss));
  console.log("screen headings actually read (one value per screen; runs = how many arm/width/theme reads produced it):");
  for (const s of Object.keys(headingByScreen)) {
    const vals = Object.values(headingByScreen[s]);
    console.log("   " + s.padEnd(8) + " -> " + asc(vals[0]) + " | distinct=" + new Set(vals).size + " of " + vals.length + " reads");
  }
  console.log("distinct heading counts per run: " + JSON.stringify(guard.distinct_heading_count_by_run));
  console.log("unpaired occurrences per width: " + JSON.stringify(Object.keys(guard.unpaired_keys).reduce((o, k) => (o[k] = [guard.unpaired_keys[k].second_run_only_count, guard.unpaired_keys[k].first_run_only_count], o), {})));
  console.log("occurrence-count mismatch groups: " + guard.count_mismatch_keys.reduce((n, x) => n + x.mismatches.length, 0));
  for (const g of guard.count_mismatch_keys) for (const mm of g.mismatches) console.log("   MISMATCH real? arm=" + g.arm + " w=" + g.width + " " + asc(mm.base) + " " + mm.first_theme_count + " vs " + mm.second_theme_count);
  console.log("LIST A (invisible in dark) deduped=" + listA.length + " raw_pairs=" + rawA.length
    + " | LIST B (unpaired background) deduped=" + listB.length + " raw_pairs=" + rawB.length);
  console.log("--- LIST A top 12 (invisible in dark) ---");
  for (const x of listA.slice(0, 12)) {
    console.log("   " + x.screen.padEnd(8) + " w" + x.widths.join("/") + " | " + x.selector.slice(0, 46).padEnd(46) + " | " + (x.testid || "-").slice(0, 20).padEnd(20)
      + " | darkbg " + x.dark_bg + " lum " + x.bg_lum + " | ink " + x.dark_color + " lum " + x.color_lum + " | ratio " + x.contrast
      + " | lightbg " + x.light_bg + " | samebg " + x.bg_identical_across_themes + " | area " + x.max_area);
  }
  console.log("--- LIST B top 12 (unpaired background) ---");
  for (const x of listB.slice(0, 12)) {
    console.log("   " + x.screen.padEnd(8) + " w" + x.widths.join("/") + " | " + x.selector.slice(0, 46).padEnd(46) + " | " + (x.testid || "-").slice(0, 20).padEnd(20)
      + " | bg " + x.dark_bg + " lum " + x.bg_lum + " | ink " + x.dark_color + " | ratio " + x.contrast + " | area " + x.max_area);
  }
  console.log("--- self check ---");
  for (const s of selfCheck) console.log("   " + s.selector + " (" + s.screen + ") pass=" + s.widths.every((x) => x.clean) + " " + JSON.stringify(s.widths.map((x) => ({ w: x.width, darkbg: x.dark_bg, lum: x.bg_lum, ratio: x.contrast, inA: x.in_listA, inB: x.in_listB }))));
  if (controlSummary) console.log("--- negative control (light forced for BOTH sweeps) --- " + JSON.stringify({ paired: controlSummary.paired_per_width, listA: controlSummary.listA_count_deduped, listB_definitionally_saturated: controlSummary.listB_count_deduped, bg_identical_count: controlSummary.bg_identical_count, bg_differs_count: controlSummary.bg_differs_count }));

  if (!selfCheckPass) {
    console.log("SELF-CHECK FAILED: a known-good selector is in a red list - the instrument is wrong, not the product. See " + OUT);
    await browser.close();
    process.exit(3);
  }
  if (problems.length) {
    console.log("ABORT (vacuity guard):");
    for (const p of problems) console.log("   - " + asc(p));
    await browser.close();
    process.exit(2);
  }
  for (const k of Object.keys(guard.paired_per_width_per_arm)) {
    if (k.indexOf("real/") === 0 && guard.paired_per_width_per_arm[k] <= MIN_PAIRED) {
      console.log("ABORT: paired count at " + k + " is " + guard.paired_per_width_per_arm[k] + ", not > " + MIN_PAIRED);
      await browser.close();
      process.exit(2);
    }
  }
  console.log("OK wrote " + OUT);
  await browser.close();
})().catch((e) => { console.log("FATAL " + e); process.exit(1); });
