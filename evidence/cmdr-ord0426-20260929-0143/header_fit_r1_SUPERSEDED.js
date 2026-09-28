/* CMDR header-fit ruler r1 - does the top bar still fit once its labels are Chinese?
 *
 * Why: I saw it in my own screenshot of /v8/twin at 390x844. The theme chip reads 跟随系统 and it is laid
 * out on TWO lines while the locale chip next to it reads EN on one line, so the two chips have different
 * heights inside one fixed row - and the round avatar at the right edge is clipped by the viewport.
 * Nobody has ordered this, and it is the predictable cost of the last two nights of work: ORD-0420 is
 * translating labels from English to Chinese, and a translated label is a DIFFERENT WIDTH. Every size ruler
 * so far measured overflow height, icon size and text collisions - none measured "a control's own label
 * wrapping inside a fixed row".
 *
 * Per shape x locale it reports, for every visible top-bar control:
 *   box, line_count (height / line-height, rounded), wrapped (line_count >= 2),
 *   and whether the control is fully inside the viewport (clipped_right / clipped_left / clipped_top).
 * Plus documentElement.scrollWidth vs the viewport width: horizontal overflow is the same defect seen from
 * the page side, and it is what a user feels as "the page shakes sideways".
 *
 * Usage: node _header_fit_r1.js <base> <out-dir> [route]
 */
const { chromium } = require("D:/moodle/CityNexus/frontend/node_modules/playwright");
const fs = require("fs");
const BASE = process.argv[2] || "http://127.0.0.1:4805";
const OUT = process.argv[3] || "D:/moodle/_qoder_cmdr_ref_20260921/live_checks/_header_fit_r1/";
const ROUTE = process.argv[4] || "twin";
fs.mkdirSync(OUT, { recursive: true });

const SHAPES = [[390, 844], [360, 800], [414, 896], [320, 653]];
const LOCALES = ["zh", "en"];

const MEASURE = () => {
  const header = document.querySelector("header, [class*='topbar'], [data-testid*='topbar']") ||
                 document.querySelector("body > div > div");
  const vw = innerWidth;
  const vis = (e) => { const r = e.getBoundingClientRect(); return r.width > 0 && r.height > 0; };
  const controls = Array.from((header || document.body).querySelectorAll("button,a,[role=button],[data-testid]"))
    .filter(vis)
    .slice(0, 24)
    .map((e) => {
      const r = e.getBoundingClientRect();
      const cs = getComputedStyle(e);
      const lh = parseFloat(cs.lineHeight) || parseFloat(cs.fontSize) * 1.2 || 16;
      const text = (e.innerText || e.textContent || "").replace(/\s+/g, " ").trim().slice(0, 40);
      const lines = Math.max(1, Math.round((r.height - parseFloat(cs.paddingTop) - parseFloat(cs.paddingBottom)) / lh));
      return { text, tag: e.tagName, testid: e.getAttribute("data-testid"),
               box: [Math.round(r.x), Math.round(r.y), Math.round(r.width), Math.round(r.height)],
               line_height_px: Math.round(lh * 10) / 10, rendered_lines: lines,
               wrapped: lines >= 2,
               clipped_right: r.right > vw + 1, clipped_left: r.left < -1,
               outside_viewport_bottom: r.top > innerHeight };
    });
  const de = document.documentElement;
  return { vw, vh: innerHeight, header_found: !!header,
           header_box: header ? (() => { const r = header.getBoundingClientRect();
             return [Math.round(r.x), Math.round(r.y), Math.round(r.width), Math.round(r.height)]; })() : null,
           doc_scroll_width: de.scrollWidth, client_width: de.clientWidth,
           horizontal_overflow: de.scrollWidth > de.clientWidth + 1,
           controls };
};

(async () => {
  const br = await chromium.launch({ channel: "chrome", headless: true });
  const report = { base: BASE, route: ROUTE, shapes: SHAPES, locales: LOCALES, runs: [] };
  for (const locale of LOCALES) {
    for (const [w, h] of SHAPES) {
      const ctx = await br.newContext({ viewport: { width: w, height: h } });
      const page = await ctx.newPage();
      await page.addInitScript((l) => { try { localStorage.setItem("citynexus.locale", l); } catch (e) {} }, locale);
      await page.goto(BASE.replace(/\/$/, "") + "/v8/" + ROUTE, { waitUntil: "networkidle", timeout: 60000 });
      const seal = page.getByText("使用封存的演示行程", { exact: false }).first();
      if (await seal.count()) { await seal.click(); await page.waitForTimeout(4000); }
      await page.waitForTimeout(1000);
      const m = await page.evaluate(MEASURE);
      m.locale = locale; m.shape = w + "x" + h;
      m.wrapped_controls = m.controls.filter((c) => c.wrapped).map((c) => c.text || c.testid);
      m.clipped_controls = m.controls.filter((c) => c.clipped_right || c.clipped_left).map((c) => (c.text || c.testid) + (c.clipped_right ? "|right" : "|left"));
      report.runs.push(m);
      fs.writeFileSync(OUT + "hdr_" + ROUTE + "_" + locale + "_" + w + x(h) + ".png", await page.screenshot({ type: "png" }));
      console.log((locale + " " + w + "x" + h).padEnd(14),
                  "header_h", String(m.header_box ? m.header_box[3] : 0).padStart(3),
                  "wrapped", String(m.wrapped_controls.length).padStart(2),
                  "clipped", String(m.clipped_controls.length).padStart(2),
                  "hscroll", m.horizontal_overflow ? "YES" : "no");
      m.wrapped_controls.slice(0, 4).forEach((t) => console.log("        WRAPPED:", JSON.stringify(t)));
      m.clipped_controls.slice(0, 4).forEach((t) => console.log("        CLIPPED:", JSON.stringify(t)));
      await ctx.close();
    }
  }
  await br.close();
  const wrapped = report.runs.reduce((a, r) => a + r.wrapped_controls.length, 0);
  const clipped = report.runs.reduce((a, r) => a + r.clipped_controls.length, 0);
  const hs = report.runs.filter((r) => r.horizontal_overflow).length;
  report.summary = { runs: report.runs.length, wrapped_controls: wrapped, clipped_controls: clipped,
                     runs_with_horizontal_overflow: hs,
                     verdict: (wrapped || clipped || hs) ? "HEADER_OVERFLOW_OR_WRAPS" : "HEADER_FITS" };
  fs.writeFileSync(OUT + "header_fit_" + ROUTE + ".json", JSON.stringify(report, null, 1));
  console.log("TOTALS runs", report.runs.length, "wrapped", wrapped, "clipped", clipped, "hscroll runs", hs,
              "| VERDICT", report.summary.verdict);
})().catch((e) => { console.log("FATAL", String(e).slice(0, 240)); process.exit(9); });

function x(h) { return "x" + h; }
