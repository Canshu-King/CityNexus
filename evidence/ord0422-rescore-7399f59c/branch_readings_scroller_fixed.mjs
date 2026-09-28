/* ORD-0422 branch readings: whole-leaf, two-arm readings of the eleven rows the sealed demo alone
 * cannot walk. Each run is paired with the fixture step that produced the state, and the artifact
 * names whether that state came through a product door or through a stored row in this lane's own
 * private database copy -- a panel reading is not a production reachability claim.
 *
 * Matching is whole-leaf equality, not substring: "CHANGED" is a badge of its own and must not be
 * counted as read because the kicker "V14 · REALITY CHANGED" happens to contain it.
 */
import fs from "node:fs";
import { chromium } from "file:///D:/moodle/CityNexus/frontend/node_modules/playwright/index.mjs";

const UI = "http://127.0.0.1:4314";
const OUT = process.argv[3] || "D:/moodle/_qoder_q_ord0422/branch_readings";
const ROUTE = process.argv[2] || "authoritative";
const CASE = process.argv[4] || "case";
fs.mkdirSync(OUT, { recursive: true });
const DEMO = "22222222-2222-4222-8222-222222222222";
const ROWS = JSON.parse(fs.readFileSync("D:/moodle/_qoder_q_ord0422/branch_rows.json", "utf-8"));

const src = fs.readFileSync("D:/moodle/_qoder_q_ord0422/rescore_LocaleContext.tsx", "utf-8");
const KEY = /^ {2}"([a-z][A-Za-z0-9_]*(?:\.[A-Za-z0-9_]+)+)": "((?:[^"\\]|\\.)*)",$/gm;
const grab = (name) => {
  const i = src.indexOf(`const ${name}: Dict = {`);
  const out = new Map();
  for (const m of src.slice(i, src.indexOf("\n};", i)).matchAll(KEY)) out.set(m[1], m[2].replace(/\\"/g, '"'));
  return out;
};
const enDict = grab("en"), zhDict = grab("zhCN");

/* Every key that writes this exact English value, because the same sentence can legitimately live
 * under two keys (v14.deterministicGate and discovery.detGate both say "Deterministic gate").
 * A row counts as Chinese-paid when ANY of those keys' zh values is on the screen; the ambiguity
 * itself is reported instead of being resolved by whichever key came first. */
function locate(row) {
  const hits = [];
  for (const [k, v] of enDict) {
    if (v === row) hits.push({ key: k, en: v, zh: zhDict.get(k) ?? null, param: false });
    else if (/\{[a-z_]+\}/.test(v) && v.includes(row))
      hits.push({ key: k, en: v, zh: zhDict.get(k) ?? null, param: true });
  }
  return { hits, key: hits.length ? hits.map((h) => h.key).join(",") : null };
}
const widen = (v) => new RegExp(`^${v.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")
  .replace(/\\\{[a-z_]+\\\}/g, "[\\d.,]+")}$`);

const COLLECT = () => {
  const seen = new Map();
  const push = () => {
    document.querySelectorAll("body *").forEach((e) => {
      if (e.children.length) return;
      const t = (e.textContent || "").replace(/\s+/g, " ").trim();
      if (!t) return;
      const r = e.getBoundingClientRect();
      if (!(r.width > 0 && r.height > 0 && r.bottom > 0 && r.top < innerHeight)) return;
      if (!seen.has(t)) seen.set(t, true);
    });
  };
  /* A container counts only when it can actually scroll: overflowY visible with 10 px of overflow is
     painted outside the box, not hidden behind it, and setting scrollTop on it does nothing -- that is
     what made the Chinese twin arm report "did not reach bottom" while the page itself hit its max. */
  const scrollable = (e) => ["auto", "scroll"].includes(getComputedStyle(e).overflowY);
  const scrollers = [document.scrollingElement || document.documentElement];
  document.querySelectorAll("*").forEach((e) => {
    if (e.scrollHeight > e.clientHeight + 8 && e.clientHeight > 120 && scrollable(e)) scrollers.push(e);
  });
  const reached = [];
  scrollers.forEach((el) => {
    const max = Math.max(0, el.scrollHeight - el.clientHeight);
    let deepest = 0;
    for (let y = 0; ; y += Math.max(120, Math.floor(el.clientHeight * 0.5))) {
      el.scrollTop = Math.min(y, max);
      deepest = Math.max(deepest, Math.round(el.scrollTop));
      push();
      if (y >= max) break;
    }
    reached.push({ max, deepest, bottom_reached: deepest >= max - 2 });
    el.scrollTop = 0;
  });
  return { path: location.pathname, texts: Array.from(seen.keys()), reached,
           locale_read: localStorage.getItem("citynexus.locale") };
};

const browser = await chromium.launch({ channel: "chrome", headless: true });
const ctx = await browser.newContext({ viewport: { width: 390, height: 844 } });
const page = await ctx.newPage();
const report = { case: CASE, route: ROUTE, journey: DEMO, ui: UI, arms: [] };

for (const locale of ["zh-CN", "en"]) {
  await page.addInitScript(([l, id]) => {
    try {
      localStorage.setItem("citynexus.locale", l);
      localStorage.setItem("citynexus.v8.journey_id", id);
    } catch (e) {}
  }, [locale, DEMO]);
  await page.goto(`${UI}/v8/${ROUTE}`, { waitUntil: "networkidle", timeout: 60000 });
  await page.waitForTimeout(2600);
  const r = await page.evaluate(COLLECT);
  const leaves = r.texts;
  const rows = ROWS.map((row) => {
    const { hits, key } = locate(row);
    const hit = (value, param) => value == null ? false
      : (param ? leaves.some((l) => widen(value).test(l)) : leaves.includes(value));
    const enLeaf = hits.some((h) => hit(h.en, h.param));
    const zhLeaf = hits.some((h) => hit(h.zh, h.param));
    return {
      row, key, keys: hits.map((h) => h.key), interpolated: hits.some((h) => h.param),
      en_leaf: locale === "en" ? enLeaf : null,
      zh_leaf: locale === "zh-CN" ? zhLeaf : null,
      en_texts: hits.map((h) => h.en), zh_texts: hits.map((h) => h.zh),
    };
  });
  report.arms.push({ locale, path: r.path, locale_read: r.locale_read,
                     bottom_reached: r.reached.every((x) => x.bottom_reached),
                     leaf_count: leaves.length, rows, leaves,
                     cjk_leaves: leaves.filter((t) => /[㖀-鿿]/.test(t)) });
  await page.screenshot({ path: `${OUT}/${CASE}_${ROUTE}_${locale.replace("-", "_")}.png` });
}
await ctx.close();
await browser.close();
const file = `${OUT}/${CASE}_${ROUTE}.json`;
fs.writeFileSync(file, JSON.stringify(report, null, 1));
const zh = report.arms[0], en = report.arms[1];
console.log(`${CASE} /${ROUTE} | zh path=${zh.path} leaves=${zh.leaf_count} bottom=${zh.bottom_reached}`
  + ` | en path=${en.path} leaves=${en.leaf_count} bottom=${en.bottom_reached}`);
for (const r of en.rows) {
  const zhRow = zh.rows.find((x) => x.row === r.row);
  console.log("  en_leaf=%s zh_leaf=%s | %s | zh=%s | keys=%s%s",
    String(r.en_leaf), String(zhRow ? zhRow.zh_leaf : null), JSON.stringify(r.row).slice(0, 76),
    JSON.stringify(r.zh_texts), r.keys, r.interpolated ? " (interpolated)" : "");
}
console.log("->", file);
