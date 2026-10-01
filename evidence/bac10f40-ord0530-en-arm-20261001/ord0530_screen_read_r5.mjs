/**
 * ORD-0530 -- the English arm of the footprint screen, read the way a traveller sees it.
 *
 * The r3 block names this as the one cell it did not verify: the zh/en sentences are one table
 * (`src/features/checkin/footprintCopy.ts`), but only the Chinese screen had been read off the
 * glass.  So this instrument reads the table from the source file and compares it to what is
 * painted -- no sentence is hard-coded here, which is the difference between "the copy exists" and
 * "the copy reaches the screen".  A missing English arm in that table does not crash anything; it
 * puts a machine word on the glass (`LocaleContext.tsx:2164` prints the key), so the judge is
 * counting machine tokens, not reading the file and concluding.
 *
 * The browser is still pinned to a zone that is NOT the trip's, in both arms: the day a stamp lands
 * on must not move when the device clock disagrees, and the two arms have to agree about which day
 * that is even though they spell it differently.
 *
 * Usage:  ORD0530_BASE=http://127.0.0.1:PORT node ord0530_screen_read_r5.mjs --out <dir> --tag <l>
 */
import { chromium } from "playwright";
import { mkdirSync, readFileSync, writeFileSync } from "node:fs";

const BASE = process.env.ORD0530_BASE ?? "http://127.0.0.1:4795";
const JOURNEY = "22222222-2222-4222-8222-222222222222";
const TABLE = "D:/moodle/_qoder_ai_ord0387_20260928/wt/frontend/src/features/checkin/footprintCopy.ts";
const args = process.argv.slice(2);
const outDir = args[args.indexOf("--out") + 1];
const tag = args[args.indexOf("--tag") + 1];
mkdirSync(outDir, { recursive: true });

/** Pull `en` and `zh` out of the product's own object literal, keyed by the copy key. */
function copyTable() {
  const src = readFileSync(TABLE, "utf8");
  const out = {};
  const re = /([A-Za-z]+):\s*\{((?:[^{}]|\{[^{}]*\})*)\}/gs;
  let m;
  while ((m = re.exec(src)) !== null) {
    const key = m[1];
    const body = m[2];
    const en = /en:\s*"((?:[^"\\]|\\.)*)"/s.exec(body);
    const zh = /zh:\s*"((?:[^"\\]|\\.)*)"/s.exec(body);
    if (en || zh) out[key] = { en: en ? en[1] : null, zh: zh ? zh[1] : null };
  }
  return out;
}

const COPY = copyTable();
const KEYS_USED = ["scope", "dayZone", "sourceWeb", "empty", "refused", "unreachable", "retry",
                   "count", "dayCount", "noteAbsent", "time", "target", "sourceLabel"];
for (const k of KEYS_USED) {
  if (!COPY[k] || !COPY[k].en || !COPY[k].zh) {
    throw new Error(`copy table parsed without a usable pair for ${k} -- the judge is broken`);
  }
}

const SHAPES = [
  { name: "phone_390x844", width: 390, height: 844 },
  { name: "desktop_1280x900", width: 1280, height: 900 },
];
const LOCALES = [
  { name: "en", value: "en-US" },
  { name: "zh", value: "zh-CN" },
];

const browser = await chromium.launch();
const report = { base: BASE, journey: JOURNEY, tag, browser_timezone: "America/Los_Angeles",
                 table_keys_parsed: Object.keys(COPY).length, arms: [] };

for (const loc of LOCALES) {
  for (const shape of SHAPES) {
    const context = await browser.newContext({
      viewport: { width: shape.width, height: shape.height },
      locale: loc.value,
      timezoneId: "America/Los_Angeles",
    });
    const page = await context.newPage();
    await page.addInitScript((o) => {
      localStorage.setItem("citynexus.v8.journey_id", o.journey);
      localStorage.setItem("citynexus.locale", o.locale);
    }, { journey: JOURNEY, locale: loc.value });
    await page.goto(`${BASE}/v8/footprints`, { waitUntil: "load", timeout: 60000 });
    await page.waitForSelector("[data-testid='footprint-panel']", { timeout: 30000 });
    await page.waitForTimeout(2500);

    const read = await page.evaluate(() => {
      const text = (el) => (el instanceof HTMLElement ? el.innerText.replace(/\s+/g, " ").trim() : "");
      const panel = document.querySelector("[data-testid='footprint-panel']");
      const days = Array.from(document.querySelectorAll("[data-testid='footprint-day']"));
      const rows = Array.from(document.querySelectorAll("[data-testid='footprint-row']"));
      const probe = (el) => {
        el.scrollIntoView({ block: "center" });
        const r = el.getBoundingClientRect();
        const cx = Math.round(r.x + r.width / 2);
        const cy = Math.round(r.y + r.height / 2);
        const hitEl = document.elementFromPoint(cx, cy);
        return { box: { x: Math.round(r.x), y: Math.round(r.y), w: Math.round(r.width), h: Math.round(r.height) },
                 centre: { x: cx, y: cy }, hit: hitEl ? `${hitEl.tagName.toLowerCase()}.${hitEl.className}` : "none",
                 hit_is_self: !!hitEl && (hitEl === el || el.contains(hitEl)) };
      };
      return {
        panel_text: text(panel),
        tally: text(panel.querySelector("[data-testid='footprint-tally']") || panel),
        day_rows: days.map((el) => ({ text: text(el), probe: probe(el) })),
        stamp_rows: rows.map((el) => ({ text: text(el), cells: Array.from(el.children).map((c) => text(c)),
                                       probe: probe(el) })),
        button_words: Array.from(panel.querySelectorAll("button")).map(text),
      };
    });

    /* The sentence-level judges, all against the table the product shipped for this locale. */
    const want = (k) => COPY[k][loc.name];
    const checks = {
      scope_on_glass: read.panel_text.includes(want("scope")),
      zone_sentence: read.panel_text.includes(want("dayZone").replace("{zone}", "Asia/Shanghai")),
      source_word_on_glass: read.stamp_rows.every((r) => r.cells.includes(want("sourceWeb"))),
      retry_button_word: read.button_words.includes(want("retry")),
      tally_matches_template: read.panel_text.includes(
        want("count").replace("{count}", String(read.stamp_rows.length))) &&
        read.panel_text.includes(want("dayCount").replace("{count}", String(read.day_rows.length))),
      row_cells: read.stamp_rows.map((r) => r.cells.length),
    };
    /* Machine words that should never reach the glass in either arm. */
    const machine = read.panel_text.match(/FOREGROUND_WEB|footprint[A-Z]\w*|[a-z]+_[a-z]+_[a-z]+|[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}/g);
    const arm = { locale: loc.value, arm: loc.name, shape, read, checks,
                  machine_tokens: machine ? machine.slice(0, 8) : [],
                  screaming_snake: (read.panel_text.match(/\b[A-Z][A-Z_]{3,}\b/g) || []).length,
                  bare_uuid: (read.panel_text.match(/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}/g) || []).length };
    report.arms.push(arm);
    await page.screenshot({ path: `${outDir}/footprints_${tag}_${loc.name}_${shape.name}.png`, fullPage: false });
    await context.close();
  }
}
await browser.close();

/* The two arms spell the day differently but must agree about which days there are and how many
   rows sit under each one -- that is the grouping claim, read off both screens in one run. */
const en = report.arms.find((a) => a.arm === "en" && a.shape.name === "phone_390x844");
const zh = report.arms.find((a) => a.arm === "zh" && a.shape.name === "phone_390x844");
report.cross_arm = {
  en_day_count: en.read.day_rows.length,
  zh_day_count: zh.read.day_rows.length,
  en_row_count: en.read.stamp_rows.length,
  zh_row_count: zh.read.stamp_rows.length,
  same_grouping_size: en.read.day_rows.length === zh.read.day_rows.length &&
                      en.read.stamp_rows.length === zh.read.stamp_rows.length,
  en_days: en.read.day_rows.map((d) => d.text),
  zh_days: zh.read.day_rows.map((d) => d.text),
};
report.all_checks_pass = report.arms.every((a) => Object.values(a.checks).every((v) => v === true ||
  Array.isArray(v)));
report.machine_tokens_anywhere = report.arms.reduce((n, a) => n + a.machine_tokens.length, 0);

writeFileSync(`${outDir}/footprints_${tag}.json`, JSON.stringify(report, null, 1), "utf8");
console.log(`arms ${report.arms.length} all_checks_pass ${report.all_checks_pass} machine_tokens ${report.machine_tokens_anywhere}`);
for (const a of report.arms) {
  console.log(`  ${a.arm} ${a.shape.name} days ${a.read.day_rows.length} rows ${a.read.stamp_rows.length}`,
    JSON.stringify(a.checks), "snake", a.screaming_snake, "uuid", a.bare_uuid,
    "machine", JSON.stringify(a.machine_tokens));
}
console.log("cross_arm", JSON.stringify(report.cross_arm));
console.log("out", `${outDir}/footprints_${tag}.json`);
