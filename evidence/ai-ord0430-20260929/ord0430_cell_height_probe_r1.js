// Why is the yielded cell 44 wide but 56 tall?  Read computed values rather than guessing which
// CSS rule wins.
const { chromium } = require("D:/moodle/CityNexus/frontend/node_modules/playwright");
const BASE = process.argv[2] || "http://127.0.0.1:4827";

const PROBE = async () => {
  await new Promise((r) => window.setTimeout(r, 900));
  const dock = document.querySelector('[data-testid="v18-copilot-dock"]');
  const btn = dock && dock.querySelector(".cn-copilot-edge");
  const cs = (el) => {
    const c = getComputedStyle(el);
    return { height: c.height, minHeight: c.minHeight, maxHeight: c.maxHeight, boxSizing: c.boxSizing, padding: c.padding, display: c.display, position: c.position, lineHeight: c.lineHeight };
  };
  const rect = (el) => {
    const r = el.getBoundingClientRect();
    return { w: Math.round(r.width), h: Math.round(r.height), top: Math.round(r.top), bottom: Math.round(r.bottom) };
  };
  return {
    dockClasses: String(dock && dock.className),
    dockRect: dock && rect(dock),
    dockComputed: dock && cs(dock),
    btnRect: btn && rect(btn),
    btnComputed: btn && cs(btn),
    btnChildren: btn ? Array.from(btn.children).map((k) => k.tagName + "." + String(k.className) + " " + JSON.stringify(rect(k))) : [],
    scrollTop: Math.round((document.scrollingElement || document.documentElement).scrollTop),
  };
};

(async () => {
  const browser = await chromium.launch();
  const ctx = await browser.newContext({ viewport: { width: 390, height: 844 } });
  const page = await ctx.newPage();
  await page.goto(BASE + "/", { waitUntil: "domcontentloaded", timeout: 60000 }).catch(() => {});
  await page.evaluate(() => localStorage.setItem("citynexus.locale", "en"));
  await page.goto(BASE + "/v8/twin", { waitUntil: "domcontentloaded", timeout: 60000 }).catch(() => {});
  for (const label of ["Use the sealed demo journey", "sealed demo", "使用封存的演示行程"]) {
    const loc = page.getByText(label, { exact: false }).first();
    if (await loc.count()) { await loc.click({ timeout: 8000 }).catch(() => {}); await page.waitForTimeout(2000); break; }
  }
  await page.goto(BASE + "/v8/twin", { waitUntil: "domcontentloaded", timeout: 60000 }).catch(() => {});
  await page.waitForTimeout(2600);
  await page.evaluate(() => {
    const scroller = document.scrollingElement || document.documentElement;
    scroller.scrollTop = Math.round((scroller.scrollHeight - scroller.clientHeight) / 2);
  });
  await page.waitForTimeout(1400);
  const res = await page.evaluate(PROBE);
  console.log(JSON.stringify(res, null, 1));
  await browser.close();
})();
