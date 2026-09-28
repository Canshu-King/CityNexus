/* CMDR ORD-0419 instrument r2 - same question as r1 ("on a zh screen, which rendered strings are still
 * English?") with r1's blind spot closed.
 *
 * r1 filtered leaves with `r.top < innerHeight` and never scrolled, so everything below the fold was
 * invisible to it.  That is why `Unknown accessibility evidence is not accessible.` - a hardcoded literal
 * at TwinPanel.tsx:24 - never showed up in the twin receipt.  r1's counts are therefore a FLOOR, not a
 * total, and this instrument exists to say so with a number.
 *
 * r2 collects a UNION over scroll steps: the document plus every scrollable container found in the DOM is
 * stepped in viewport-sized increments, leaves are gathered at each step, and de-duplicated by
 * (tag,cls,text).  It also takes an explicit checklist of source-proven literals and reports, for each,
 * whether it was actually seen on screen - so "in the source" and "on the screen" stay separate claims.
 *
 * Usage: node _untranslated_scan_r2.js <base> <route> <out-dir> [expect.json]
 *   expect.json = ["string one", "string two", ...]   (optional)
 */
const { chromium } = require("D:/moodle/CityNexus/frontend/node_modules/playwright");
const fs = require("fs");
const BASE = process.argv[2], ROUTE = process.argv[3] || "twin";
const OUT = process.argv[4] || "D:/moodle/_qoder_cmdr_ref_20260921/live_checks/_untranslated_r2/";
const EXPECT = process.argv[5] ? JSON.parse(fs.readFileSync(process.argv[5], "utf-8")) : [];
fs.mkdirSync(OUT, { recursive: true });
const CJK = /[\u3400-\u9fff\uf900-\ufaff]/;

const COLLECT = () => {
  const seen = new Map();
  const push = () => {
    document.querySelectorAll("body *").forEach((e) => {
      if (e.children.length) return;
      const t = (e.textContent || "").replace(/\s+/g, " ").trim();
      if (!t) return;
      const r = e.getBoundingClientRect();
      const vis = r.width > 0 && r.height > 0 && r.bottom > 0 && r.top < innerHeight;
      if (!vis) return;
      const key = e.tagName + "|" + (e.className || "").toString().slice(0, 24) + "|" + t;
      if (seen.has(key)) return;
      seen.set(key, { text: t.slice(0, 160), tag: e.tagName,
        cls: (e.className || "").toString().slice(0, 40),
        testid: e.getAttribute("data-testid") || (e.parentElement && e.parentElement.getAttribute("data-testid")) || null,
        y: Math.round(r.top), scroll_step: seen.size });
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
    // r2's first cut stepped by 0.8*clientHeight and stopped at `y <= max`, so on a page whose whole
    // scroll range (392 px) is smaller than one step (675 px) the loop ran ONCE at y=0 and the document
    // was never scrolled at all - it then reported a below-the-fold literal as NOT_ON_SCREEN.  The step is
    // now smaller and the loop always performs a final step AT max, so the bottom of the page is reached
    // whatever the geometry.
    const stepBy = Math.max(120, Math.floor(el.clientHeight * 0.5));
    let deepest = 0;
    for (let y = 0; ; y += stepBy) {
      el.scrollTop = Math.min(y, max);
      deepest = Math.max(deepest, Math.round(el.scrollTop));
      push();
      steps++;
      if (y >= max || steps > 80) break;
    }
    // an arm has to show it landed: without this the receipt cannot tell "scrolled to the bottom" from
    // "the page refused to move", and a refused scroll looks exactly like "no copy down there".
    reached.push({ tag: el.tagName, cls: (el.className || "").toString().slice(0, 32),
                   max, deepest_scrollTop_reached: deepest,
                   bottom_reached: deepest >= max - 2 });
    el.scrollTop = 0;
  });
  return { path: location.pathname, steps, scrollables: scrollables.length, reached,
           leaves: Array.from(seen.values()),
           locale_read: localStorage.getItem("citynexus.locale") };
};

async function arm(browser, locale) {
  const ctx = await browser.newContext({ viewport: { width: 390, height: 844 } });
  const page = await ctx.newPage();
  await page.addInitScript((l) => { try { localStorage.setItem("citynexus.locale", l); } catch (e) {} }, locale);
  await page.goto(BASE.replace(/\/$/, "") + "/v8/" + ROUTE, { waitUntil: "networkidle", timeout: 60000 });
  const seal = page.getByText("\u4f7f\u7528\u5c01\u5b58\u7684\u6f14\u793a\u884c\u7a0b", { exact: false }).first();
  if (await seal.count()) { await seal.click(); await page.waitForTimeout(4000); }
  await page.waitForTimeout(1200);
  const read = await page.evaluate(COLLECT);
  const ascii = read.leaves.filter((l) => l.text.length >= 6 && !CJK.test(l.text)
      && !/^[\d\s.,:%/\-+()[\]#\u00b7\u00a5]+$/.test(l.text));
  // the checklist: does each source-proven literal actually reach the screen in THIS locale?
  const allText = read.leaves.map((l) => l.text).join("\n");
  const expect = EXPECT.map((s) => ({ text: s, on_screen: allText.includes(s) }));
  await page.screenshot({ path: OUT + ROUTE + "_" + locale + ".png", fullPage: false });
  await ctx.close();
  return { locale, path: read.path, locale_read: read.locale_read, scroll_steps: read.steps,
           scrollables: read.scrollables, scroll_reached: read.reached, leaf_count: read.leaves.length,
           ascii_prose_count: ascii.length, ascii_prose: ascii, expect };
}

(async () => {
  const br = await chromium.launch({ channel: "chrome", headless: true });
  const zh = await arm(br, "zh"), en = await arm(br, "en");
  await br.close();
  const r1zh = fs.existsSync(OUT + "../_untranslated_twin/untranslated_twin_r1.json") && ROUTE === "twin"
    ? JSON.parse(fs.readFileSync(OUT + "../_untranslated_twin/untranslated_twin_r1.json", "utf-8")).zh.ascii_prose_count
    : null;
  const out = { base: BASE, route: ROUTE, generated_by: "_untranslated_scan_r2.js",
    expect_list_size: EXPECT.length, zh, en,
    r1_floor_for_twin: r1zh,
    verdict: zh.ascii_prose_count === 0 ? "NO_UNTRANSLATED_PROSE_ON_ZH" : "ZH_SCREEN_CARRIES_ENGLISH_PROSE" };
  fs.writeFileSync(OUT + "untranslated_" + ROUTE + "_r2.json", JSON.stringify(out, null, 1));
  console.log("route", ROUTE, "| scroll_steps", zh.scroll_steps, "scrollables", zh.scrollables);
  console.log("zh leaves", zh.leaf_count, "ascii_prose", zh.ascii_prose_count,
              "| en ascii_prose", en.ascii_prose_count, r1zh === null ? "" : "| r1 said " + r1zh);
  zh.ascii_prose.forEach((x) => console.log("  ZH-EN", JSON.stringify(x.text), x.tag, x.cls));
  zh.expect.forEach((x) => console.log("  EXPECT", x.on_screen ? "ON_SCREEN " : "NOT_ON_SCREEN", JSON.stringify(x.text)));
  console.log("VERDICT", out.verdict);
})().catch((e) => { console.log("FATAL", String(e).slice(0, 240)); process.exit(9); });
