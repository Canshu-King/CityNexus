/* Why is `Unknown accessibility evidence is not accessible.` NOT_ON_SCREEN on /v8/twin?
 * Two candidate causes and this probe separates them: (a) the aside is rendered but sits below the fold
 * and my r2 scroll union never reached it, or (b) the aside / that <small> is not in the DOM at all.
 * It prints the DOM facts, not a guess. */
const { chromium } = require("D:/moodle/CityNexus/frontend/node_modules/playwright");
const BASE = process.argv[2] || "http://127.0.0.1:4805";
(async () => {
  const br = await chromium.launch({ channel: "chrome", headless: true });
  const ctx = await br.newContext({ viewport: { width: 390, height: 844 } });
  const p = await ctx.newPage();
  await p.addInitScript(() => { try { localStorage.setItem("citynexus.locale", "zh"); } catch (e) {} });
  await p.goto(BASE + "/v8/twin", { waitUntil: "networkidle", timeout: 60000 });
  const seal = p.getByText("\u4f7f\u7528\u5c01\u5b58\u7684\u6f14\u793a\u884c\u7a0b", { exact: false }).first();
  if (await seal.count()) { await seal.click(); await p.waitForTimeout(4000); }
  await p.waitForTimeout(1200);
  const f = await p.evaluate(() => {
    const q = (s) => document.querySelector(s);
    const box = (e) => { if (!e) return null; const r = e.getBoundingClientRect();
      return { x: Math.round(r.x), y: Math.round(r.y), w: Math.round(r.width), h: Math.round(r.height) }; };
    const aside = q(".v8-boundary-card");
    const grid = q(".v8-twin-grid");
    const se = q("html"), b = document.body;
    const scrollers = [];
    document.querySelectorAll("*").forEach((e) => {
      if (e.scrollHeight > e.clientHeight + 8) scrollers.push({ tag: e.tagName, cls: (e.className||"").toString().slice(0,40),
        sh: e.scrollHeight, ch: e.clientHeight, st: e.scrollTop,
        ov: getComputedStyle(e).overflowY });
    });
    return {
      innerHeight, bodyScrollHeight: b.scrollHeight, docScrollHeight: se.scrollHeight,
      docClientHeight: se.clientHeight,
      grid_present: !!grid, grid_box: box(grid), grid_child_count: grid ? grid.children.length : 0,
      aside_present: !!aside, aside_box: box(aside),
      aside_text: aside ? (aside.innerText || "").replace(/\s+/g, " ").trim().slice(0, 200) : null,
      aside_html_len: aside ? aside.innerHTML.length : 0,
      disclosure_present: !!q(".v8-capability-disclosure"),
      disclosure_text: q(".v8-capability-disclosure") ? q(".v8-capability-disclosure").textContent : null,
      disclosure_box: box(q(".v8-capability-disclosure")),
      scrollers: scrollers.slice(0, 8),
    };
  });
  console.log(JSON.stringify(f, null, 1));
  await br.close();
})().catch((e) => { console.log("FATAL", String(e).slice(0, 200)); process.exit(9); });
