/* ORD-0431 readout-only instrument, on the evening tip's build.
 * Answers exactly the three numbers the commander asked for, at 390x844 (plus the neighbouring
 * widths for context), both arms:
 *   - the real height of the top-bar row and of each control in it, in px;
 *   - whether the label wraps, decided by Range.getClientRects() count (not by dividing heights);
 *   - the overlap area in px^2 between the theme chip and every other control sharing the row,
 *     plus the horizontal gap, so "同排" and "交叠" are two separate measured facts.
 * Page errors are counted from the console so the reading is comparable with the commander's own
 * "页面错误为零" observation.
 */
import fs from "node:fs";
import { chromium } from "file:///D:/moodle/CityNexus/frontend/node_modules/playwright/index.mjs";

const UI = process.argv[2] || "http://127.0.0.1:4314";
const OUT = process.argv[3] || "D:/moodle/_qoder_q_ord0431/evening";
const WIDTHS = (process.argv[4] || "320,360,390,414").split(",").map(Number);
const ROUTE = process.argv[5] || "twin";
const DEMO = "22222222-2222-4222-8222-222222222222";
fs.mkdirSync(OUT, { recursive: true });

const PROBE = () => {
  const bar = document.querySelector(".v8-topbar");
  if (!bar) return { topbar_absent: true };
  const controls = [...bar.querySelectorAll("button, a, span, strong")].filter((el) => {
    if (el.children.length) return false;
    const t = (el.textContent || "").trim();
    const g = el.getBoundingClientRect();
    return t.length > 0 && g.width > 0 && g.height > 0;
  });
  const info = controls.map((el) => {
    const g = el.getBoundingClientRect();
    const r = document.createRange();
    r.selectNodeContents(el);
    const rects = Array.from(r.getClientRects()).filter((x) => x.width > 0 && x.height > 0);
    return { text: el.textContent.trim().slice(0, 30), tag: el.tagName,
             cls: String(el.className || "").slice(0, 30),
             box: { left: Math.round(g.left), right: Math.round(g.right), top: Math.round(g.top),
                    bottom: Math.round(g.bottom), w: Math.round(g.width), h: Math.round(g.height) },
             rect_count: rects.length,
             line_boxes: rects.map((x) => ({ w: Math.round(x.width), h: Math.round(x.height),
                                             top: Math.round(x.top) })),
             font_size: getComputedStyle(el).fontSize };
  });
  const inter = (a, b) => {
    const w = Math.min(a.box.right, b.box.right) - Math.max(a.box.left, b.box.left);
    const h = Math.min(a.box.bottom, b.box.bottom) - Math.max(a.box.top, b.box.top);
    return (w > 0 && h > 0) ? Math.round(w * h) : 0;
  };
  const gap = (a, b) => Math.round(Math.max(a.box.left - b.box.right, b.box.left - a.box.right));
  const chip = info.find((i) => i.cls.includes("v9-language"));
  const pairs = chip ? info.filter((i) => i !== chip).map((i) => ({
    with: i.text, overlap_px2: inter(chip, i), gap_px: gap(chip, i),
    same_row: i.box.top < chip.box.bottom && i.box.bottom > chip.box.top,
  })) : [];
  const bg = bar.getBoundingClientRect();
  return {
    path: location.pathname, viewport: { w: innerWidth, h: innerHeight },
    bar_box: { top: Math.round(bg.top), h: Math.round(bg.height), left: Math.round(bg.left),
               right: Math.round(bg.right) },
    bar_overflow_x: bar.scrollWidth - bar.clientWidth,
    controls: info,
    chip_present: !!chip, chip_text: chip ? chip.text : null,
    chip_rect_count: chip ? chip.rect_count : null,
    chip_box_h_px: chip ? chip.box.h : null,
    chip_font_size: chip ? chip.font_size : null,
    chip_line_boxes: chip ? chip.line_boxes : null,
    chip_vs_neighbours: pairs,
    wrapped_texts: info.filter((i) => i.rect_count > 1).map((i) => i.text),
  };
};

const browser = await chromium.launch({ channel: "chrome", headless: true });
const report = { ui: UI, route: ROUTE, widths: WIDTHS, arms: { "zh-CN": [], en: [] } };
for (const locale of ["zh-CN", "en"]) {
  for (const width of WIDTHS) {
    const ctx = await browser.newContext({ viewport: { width, height: 844 } });
    const page = await ctx.newPage();
    const errors = [];
    page.on("pageerror", (e) => errors.push(String(e).slice(0, 120)));
    page.on("console", (m) => { if (m.type() === "error") errors.push("console:" + m.text().slice(0, 120)); });
    await page.addInitScript(([l, id]) => {
      try {
        localStorage.setItem("citynexus.locale", l);
        localStorage.setItem("citynexus.v8.journey_id", id);
      } catch (e) {}
    }, [locale, DEMO]);
    await page.goto(`${UI}/v8/${ROUTE}`, { waitUntil: "networkidle", timeout: 60000 });
    await page.waitForTimeout(2400);
    const r = await page.evaluate(PROBE);
    r.width = width;
    r.page_errors = errors.length;
    r.page_error_samples = errors.slice(0, 3);
    report.arms[locale].push(r);
    await page.screenshot({ path: `${OUT}/${ROUTE}_${locale}_${width}.png` });
    await ctx.close();
  }
}
await browser.close();
for (const locale of ["zh-CN", "en"])
  fs.writeFileSync(`${OUT}/${ROUTE}_${locale}.json`, JSON.stringify(report.arms[locale], null, 1));
fs.writeFileSync(`${OUT}/${ROUTE}_both_arms.json`, JSON.stringify(report, null, 1));
for (const locale of ["zh-CN", "en"]) {
  console.log("== arm", locale);
  for (const r of report.arms[locale]) {
    if (r.topbar_absent) { console.log("  width", r.width, "TOPBAR ABSENT"); continue; }
    console.log("  width %s | bar h %s px | chip %r rect_count %s h %s px font %s | wrapped %s | errors %s",
      r.width, r.bar_box.h, r.chip_text, r.chip_rect_count, r.chip_box_h_px, r.chip_font_size,
      JSON.stringify(r.wrapped_texts), r.page_errors);
    console.log("     line boxes:", JSON.stringify(r.chip_line_boxes),
      "| neighbours:", JSON.stringify(r.chip_vs_neighbours));
  }
}
