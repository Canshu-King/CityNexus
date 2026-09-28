/* ORD-0431 baseline instrument. The ruler the order names is Range.getClientRects(): a label whose
 * rect list has more than one entry is wrapped onto a second line, whatever the CSS says. Measured on
 * every leaf inside the top bar, at 320 / 360 / 390 / 414, both arms, and paired with the two things a
 * wrap damages: whether the bar itself overflows, and whether the control on the right edge is cut off
 * or covered. One evidence file per arm, as the order requires.
 */
import fs from "node:fs";
import { chromium } from "file:///D:/moodle/CityNexus/frontend/node_modules/playwright/index.mjs";

const UI = process.argv[2] || "http://127.0.0.1:4314";
const DEMO = "22222222-2222-4222-8222-222222222222";
const OUT = process.argv[3] || "D:/moodle/_qoder_q_ord0431";
const WIDTHS = [320, 360, 390, 414];

const PROBE = () => {
  const bar = document.querySelector(".v8-topbar");
  if (!bar) return { topbar_absent: true, path: location.pathname };
  const rectsOf = (el) => {
    const r = document.createRange();
    r.selectNodeContents(el);
    const list = Array.from(r.getClientRects()).filter((x) => x.height > 0 && x.width > 0);
    return { n: list.length, heights: list.map((x) => Math.round(x.height)),
             width: Math.round(list.reduce((a, x) => Math.max(a, x.width), 0)) };
  };
  const leaves = [];
  bar.querySelectorAll("*").forEach((el) => {
    if (el.children.length) return;
    const t = (el.textContent || "").replace(/\s+/g, " ").trim();
    const box = el.getBoundingClientRect();
    if (!(t || box.width > 8)) return;
    if (!(box.width > 0 && box.height > 0)) return;
    const g = el.getBoundingClientRect();
    const centre = { x: Math.round(g.left + g.width / 2), y: Math.round(g.top + g.height / 2) };
    const hit = document.elementFromPoint(centre.x, centre.y);
    leaves.push({ text: t.slice(0, 40), tag: el.tagName, cls: String(el.className || "").slice(0, 34),
                  rects: rectsOf(el), box: { left: Math.round(g.left), right: Math.round(g.right),
                                            top: Math.round(g.top), h: Math.round(g.height) },
                  beyond_right_edge: Math.round(g.right) > window.innerWidth,
                  occluded: !!hit && hit !== el && !el.contains(hit) });
  });
  const kids = [...bar.children];
  const right = kids.length ? kids[kids.length - 1].getBoundingClientRect() : null;
  return {
    path: location.pathname, viewport: window.innerWidth,
    bar_box: (() => { const g = bar.getBoundingClientRect();
      return { top: Math.round(g.top), height: Math.round(g.height), left: Math.round(g.left),
               right: Math.round(g.right) }; })(),
    bar_overflow_x: bar.scrollWidth - bar.clientWidth,
    bar_scrollWidth: bar.scrollWidth, bar_clientWidth: bar.clientWidth,
    rightmost_child: right ? { tag: kids[kids.length - 1].tagName,
      cls: String(kids[kids.length - 1].className || "").slice(0, 34),
      left: Math.round(right.left), right: Math.round(right.right),
      clipped_by_viewport: Math.round(right.right) > window.innerWidth,
      visible_width: Math.round(Math.min(right.right, window.innerWidth) - right.left) } : null,
    wrapped_leaves: leaves.filter((l) => l.rects.n > 1).map((l) => l.text),
    leaves,
  };
};

const browser = await chromium.launch({ channel: "chrome", headless: true });
const report = { ui: UI, widths: WIDTHS, arms: { "zh-CN": [], en: [] } };
for (const locale of ["zh-CN", "en"]) {
  for (const width of WIDTHS) {
    const ctx = await browser.newContext({ viewport: { width, height: 844 } });
    const page = await ctx.newPage();
    await page.addInitScript(([l, id]) => {
      try {
        localStorage.setItem("citynexus.locale", l);
        localStorage.setItem("citynexus.v8.journey_id", id);
      } catch (e) {}
    }, [locale, DEMO]);
    await page.goto(`${UI}/v8/twin`, { waitUntil: "networkidle", timeout: 60000 });
    await page.waitForTimeout(2400);
    const r = await page.evaluate(PROBE);
    r.width = width;
    report.arms[locale].push(r);
    await page.screenshot({ path: `${OUT}/topbar_${locale}_${width}.png` });
    await ctx.close();
  }
}
await browser.close();
for (const locale of ["zh-CN", "en"]) {
  fs.writeFileSync(`${OUT}/topbar_${locale}.json`, JSON.stringify(report.arms[locale], null, 1));
}
fs.writeFileSync(`${OUT}/topbar_both_arms.json`, JSON.stringify(report, null, 1));
for (const locale of ["zh-CN", "en"]) {
  console.log("== arm", locale);
  for (const r of report.arms[locale]) {
    if (r.topbar_absent) { console.log("  width", r.width, "TOPBAR ABSENT"); continue; }
    console.log("  width %d | bar h=%d overflowX=%d | wrapped: %s | right: %s",
      r.width, r.bar_box.height, r.bar_overflow_x, JSON.stringify(r.wrapped_leaves),
      JSON.stringify(r.rightmost_child));
    r.leaves.filter((l) => l.rects.n > 1 || l.beyond_right_edge || l.occluded)
      .forEach((l) => console.log("     ", JSON.stringify(l)));
  }
}
