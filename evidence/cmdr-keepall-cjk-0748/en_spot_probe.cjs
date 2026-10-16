/* 英文臂的定点复查：keep-all 这手在中文上是把"词内断行"关掉，英文要是因此溢出就白修了。
 * 每档宽度读四枚元素的：文本、行盒、自身是否溢出（scrollWidth>clientWidth）、右缘是否越过视口。
 */
const { chromium } = require("D:/moodle/CityNexus/frontend/node_modules/playwright/index.js");

const SPECS = [
  ["A", "summary.v9-evidence-summary > span"],
  ["B", "details.v9-evidence-drawer > .v8-aside-heading span"],
  ["C", ".v8-booking-card .v8-selected-label"],
  ["D", "strong[data-testid='v13-2-memory-name']"],
];
const MEAS = (sel) => {
  const el = document.querySelector(sel);
  if (!el) return { present: false };
  const r = el.getBoundingClientRect();
  const rg = new Range();
  rg.selectNodeContents(el);
  const rects = Array.from(rg.getClientRects()).map(x => Math.round(x.width));
  return {
    present: true, text: (el.textContent || "").trim().slice(0, 24), lines: new Set(rects.map(x => x)).size, rects,
    self_overflow: el.scrollWidth > el.clientWidth + 1, scroll_w: el.scrollWidth, client_w: el.clientWidth,
    right: Math.round(r.right), vw: window.innerWidth, over_viewport: Math.round(r.right) > window.innerWidth + 1,
    wb: getComputedStyle(el).wordBreak,
  };
};

(async () => {
  const b = await chromium.launch({ channel: "chrome", headless: true });
  for (const w of [320, 360, 390, 430]) {
    const p = await b.newPage({ viewport: { width: w, height: 800 } });
    await p.addInitScript(() => {
      localStorage.setItem("citynexus.v8.journey_id", "22222222-2222-4222-8222-222222222222");
      localStorage.setItem("citynexus.theme", "light");
      localStorage.setItem("citynexus.locale", "en");
    });
    await p.goto("http://127.0.0.1:8121/", { waitUntil: "networkidle" });
    await p.waitForTimeout(2200);
    await p.evaluate(() => { const e = document.querySelector('[data-testid="today-hero-cta"]'); if (e) e.click(); });
    await p.waitForTimeout(1000);
    await p.evaluate(() => { const s = document.querySelector("summary.v9-evidence-summary"); if (s) s.click(); });
    await p.waitForTimeout(700);
    const live = {};
    for (const [k, sel] of SPECS.slice(0, 2)) live[k] = await p.evaluate(MEAS, sel);
    await p.evaluate(() => { const e = document.querySelector('[data-testid="nav-trips"]'); if (e) e.click(); });
    await p.waitForTimeout(800);
    await p.evaluate(() => { const e = document.querySelector('[data-testid="trips-tab-bookings"]'); if (e) e.click(); });
    await p.waitForTimeout(1000);
    const trip = {};
    for (const [k, sel] of SPECS.slice(2)) trip[k] = await p.evaluate(MEAS, sel);
    const doc = await p.evaluate(() => ({ s: document.documentElement.scrollWidth, v: window.innerWidth }));
    console.log("宽度", w, "| 文档横向溢出", doc.s > doc.v + 1, "(scrollW", doc.s, "视口", doc.v, ")");
    for (const [name, m] of Object.entries({ ...live, ...trip })) {
      if (!m.present) { console.log("   ", name, "不在屏上（不当成零问题）"); continue; }
      console.log("   ", name, JSON.stringify(m));
    }
    await p.close();
  }
  await b.close();
})().catch(e => { console.log("FATAL " + e); process.exit(1); });
