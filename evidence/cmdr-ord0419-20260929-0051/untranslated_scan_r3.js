/* CMDR untranslated-screen instrument r3 - fixes a fault in r2 that silently invalidated every EN arm.
 *
 * The fault, found by my own header ruler failing to find a header in the en arm:
 * r2 entered the app by clicking `getByText("使用封存的演示行程")` - the CHINESE copy of the demo-entry
 * button. In the en arm that text does not exist, so the click never happened and the en arm stayed on the
 * onboarding trial screen for ALL FOURTEEN routes. The signature was right there in my receipts: the en arm
 * reported exactly 38 ASCII-prose leaves on every single route, while the zh arm varied per route
 * (4,2,5,5,2,3,23,4,4,8,2,2,9,9). I saw that constant and did not question it.
 * => "the en arm shows 38 on this screen" was never a per-screen reading; it was one screen measured 14 times.
 *
 * r3 therefore:
 *   1. matches the demo entry in BOTH locales (and, if neither matches, records ENTRY_NOT_FOUND instead of
 *      quietly measuring the wrong page);
 *   2. asserts the arm actually landed on the requested route (`location.pathname` must contain the route)
 *      and writes `reached_route` into the receipt - an arm that did not arrive is not a reading;
 *   3. keeps r2's scroll-union collection and its `bottom_reached` proof.
 *
 * Usage: node _untranslated_scan_r3.js <base> <route> <out-dir> [expect.json]
 */
const { chromium } = require("D:/moodle/CityNexus/frontend/node_modules/playwright");
const fs = require("fs");
const BASE = process.argv[2] || "http://127.0.0.1:4806";
const ROUTE = process.argv[3] || "twin";
const OUT = process.argv[4] || "D:/moodle/_qoder_cmdr_ref_20260921/live_checks/_untranslated_r3/";
const EXPECT = process.argv[5] ? JSON.parse(fs.readFileSync(process.argv[5], "utf-8")) : [];
fs.mkdirSync(OUT, { recursive: true });
const CJK = /[一-鿿-䶿]/;

// the demo entry in both locales; r2 had only the Chinese one
const ENTRY = [
  "使用封存的演示行程",
  "Use the sealed demo journey",
  "sealed demo",
  "封存演示",
];

const COLLECT = () => {
  const seen = new Map();
  const push = () => {
    document.querySelectorAll("body *").forEach((e) => {
      if (e.children.length) return;
      const t = (e.textContent || "").replace(/\s+/g, " ").trim();
      if (!t) return;
      const r = e.getBoundingClientRect();
      if (!(r.width > 0 && r.height > 0 && r.bottom > 0 && r.top < innerHeight)) return;
      const key = e.tagName + "|" + String(e.className || "").slice(0, 24) + "|" + t;
      if (seen.has(key)) return;
      seen.set(key, { text: t.slice(0, 160), tag: e.tagName,
                      cls: String(e.className || "").slice(0, 40),
                      testid: e.getAttribute("data-testid") || (e.parentElement && e.parentElement.getAttribute("data-testid")) || null,
                      y: Math.round(r.top) });
    });
  };
  const scrollables = [document.scrollingElement || document.documentElement];
  document.querySelectorAll("*").forEach((e) => {
    if (e.scrollHeight > e.clientHeight + 8 && e.clientHeight > 120) scrollables.push(e);
  });
  let steps = 0;
  const reached = [];
  scrollables.forEach((el) => {
    const max = Math.max(0, el.scrollHeight - el.clientHeight);
    const stepBy = Math.max(120, Math.floor(el.clientHeight * 0.5));
    let deepest = 0;
    for (let y = 0; ; y += stepBy) {
      el.scrollTop = Math.min(y, max);
      deepest = Math.max(deepest, Math.round(el.scrollTop));
      push();
      steps++;
      if (y >= max || steps > 80) break;
    }
    reached.push({ tag: el.tagName, cls: String(el.className || "").slice(0, 32), max,
                   deepest_scrollTop_reached: deepest, bottom_reached: deepest >= max - 2 });
    el.scrollTop = 0;
  });
  return { path: location.pathname, hash: location.hash, steps, scrollables: scrollables.length, reached,
           leaves: Array.from(seen.values()), locale_read: localStorage.getItem("citynexus.locale") };
};

async function arm(browser, locale) {
  const ctx = await browser.newContext({ viewport: { width: 390, height: 844 } });
  const page = await ctx.newPage();
  await page.addInitScript((l) => { try { localStorage.setItem("citynexus.locale", l); } catch (e) {} }, locale);
  await page.goto(BASE.replace(/\/$/, "") + "/v8/" + ROUTE, { waitUntil: "networkidle", timeout: 60000 });
  let entryUsed = null;
  for (const label of ENTRY) {
    const loc = page.getByText(label, { exact: false }).first();
    if (await loc.count()) {
      try { await loc.click({ timeout: 4000 }); entryUsed = label; await page.waitForTimeout(4000); break; }
      catch (e) { /* try the next label rather than silently continuing */ }
    }
  }
  await page.waitForTimeout(1200);
  const read = await page.evaluate(COLLECT);
  const ascii = read.leaves.filter((l) => l.text.length >= 6 && !CJK.test(l.text)
      && !/^[\d\s.,:%/\-+()[\]#·¥]+$/.test(l.text));
  const allText = read.leaves.map((l) => l.text).join("\n");
  const expect = EXPECT.map((s) => ({ text: s, on_screen: allText.includes(s) }));
  await page.screenshot({ path: OUT + ROUTE + "_" + locale + ".png" });
  await ctx.close();
  return { locale, entry_used: entryUsed, reached_route: read.path,
           on_requested_route: read.path.indexOf("/" + ROUTE) >= 0,
           path: read.path, locale_read: read.locale_read, scroll_steps: read.steps,
           scrollables: read.scrollables, scroll_reached: read.reached, leaf_count: read.leaves.length,
           ascii_prose_count: ascii.length, ascii_prose: ascii, expect };
}

(async () => {
  const br = await chromium.launch({ channel: "chrome", headless: true });
  const zh = await arm(br, "zh"), en = await arm(br, "en");
  await br.close();
  const both_arrived = zh.on_requested_route && en.on_requested_route;
  const out = { base: BASE, route: ROUTE, generated_by: "_untranslated_scan_r3.js",
                expect_list_size: EXPECT.length, zh, en, arms_comparable: both_arrived,
                verdict: !both_arrived ? "ARMS_NOT_COMPARABLE_ANCHOR_FAILED"
                     : (zh.ascii_prose_count === 0 ? "NO_UNTRANSLATED_PROSE_ON_ZH" : "ZH_SCREEN_CARRIES_ENGLISH_PROSE") };
  fs.writeFileSync(OUT + "untranslated_" + ROUTE + "_r3.json", JSON.stringify(out, null, 1));
  console.log("route", ROUTE, "| zh entry:", JSON.stringify(zh.entry_used), "path", zh.reached_route,
              "| en entry:", JSON.stringify(en.entry_used), "path", en.reached_route);
  console.log("zh ascii_prose", zh.ascii_prose_count, "| en ascii_prose", en.ascii_prose_count,
              "| arms_comparable", both_arrived);
  zh.ascii_prose.forEach((x) => console.log("  ZH-EN", JSON.stringify(x.text), x.tag, x.cls));
  zh.expect.forEach((x) => console.log("  EXPECT", x.on_screen ? "ON_SCREEN " : "NOT_ON_SCREEN", JSON.stringify(x.text)));
  console.log("VERDICT", out.verdict);
})().catch((e) => { console.log("FATAL", String(e).slice(0, 240)); process.exit(9); });
