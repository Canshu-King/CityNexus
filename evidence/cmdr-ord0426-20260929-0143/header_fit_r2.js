/* CMDR header-fit ruler r2 - same question as r1, with r1's two instrument faults removed.
 *
 * r1's faults, both found by reading its own output rather than trusting it:
 *   1. `header` fell back to `document.body` when the selector missed. On the en arm it missed, so r1
 *      reported header_h=0 and then counted 14-15 "wrapped" controls that were PAGE text, not header text.
 *      A silent change of denominator makes the zh and en arms incomparable - exactly the kind of number I
 *      must not hand to a lane. r2 has NO fallback: no header identified => the run is NOT_MEASURED.
 *   2. `wrapped` was round((height - padding) / line-height). For a short label in a padded chip that
 *      rounds up to 2 even on one line, so r1 flagged "EN" as wrapped. r2 counts the actual line boxes with
 *      a Range over the element's first text node - that is what "did this label break onto a second line"
 *      means geometrically.
 *
 * What stays from r1 unchanged: `documentElement.scrollWidth > clientWidth` is a direct browser answer
 * about horizontal overflow, no inference involved.
 *
 * Usage: node _header_fit_r2.js <base> <out-dir> [route]
 */
const { chromium } = require("D:/moodle/CityNexus/frontend/node_modules/playwright");
const fs = require("fs");
const BASE = process.argv[2] || "http://127.0.0.1:4806";
const OUT = process.argv[3] || "D:/moodle/_qoder_cmdr_ref_20260921/live_checks/_header_fit_r2/";
const ROUTE = process.argv[4] || "twin";
fs.mkdirSync(OUT, { recursive: true });

const SHAPES = [[390, 844], [360, 800], [414, 896], [320, 653]];
const LOCALES = ["zh", "en"];

const MEASURE = () => {
  let header = document.querySelector("[data-testid='v8-topbar'], header");
  if (!header) {
    const cands = Array.from(document.querySelectorAll("div,nav,section")).filter((e) => {
      const r = e.getBoundingClientRect();
      return r.top <= 4 && r.width > 300 && r.height > 24 && r.height < 140;
    }).sort((a, b) => a.getBoundingClientRect().height - b.getBoundingClientRect().height);
    header = cands[0] || null;
  }
  const de = document.documentElement;
  const out = { vw: innerWidth, vh: innerHeight, header_found: !!header,
                header_selector_used: header ? (header.tagName + "|" + String(header.getAttribute("data-testid") || header.className || "").slice(0, 30)) : null,
                header_box: null, doc_scroll_width: de.scrollWidth, client_width: de.clientWidth,
                horizontal_overflow: de.scrollWidth > de.clientWidth + 1,
                controls: [], wrapped_controls: [], clipped_controls: [] };
  if (!header) { out.status = "NOT_MEASURED_HEADER_NOT_IDENTIFIED"; return out; }
  const hb = header.getBoundingClientRect();
  out.header_box = [Math.round(hb.x), Math.round(hb.y), Math.round(hb.width), Math.round(hb.height)];
  const lineBoxes = (e) => {
    const t = Array.from(e.childNodes).find((n) => n.nodeType === 3 && (n.textContent || "").trim());
    if (!t) return null;
    const rg = document.createRange();
    rg.selectNodeContents(t);
    const rects = Array.from(rg.getClientRects()).filter((r) => r.width > 0 && r.height > 0);
    if (!rects.length) return null;
    const tops = [];
    rects.forEach((r) => { if (!tops.some((y) => Math.abs(y - r.top) <= 3)) tops.push(r.top); });
    return { text: (t.textContent || "").replace(/\s+/g, " ").trim().slice(0, 40), line_count: tops.length };
  };
  const vw = innerWidth;
  Array.from(header.querySelectorAll("button,a,[role=button],[data-testid]")).forEach((e) => {
    const r = e.getBoundingClientRect();
    if (r.width < 1 || r.height < 1) return;
    const lb = lineBoxes(e);
    const label = (e.innerText || e.textContent || "").replace(/\s+/g, " ").trim().slice(0, 40);
    const rec = { label, testid: e.getAttribute("data-testid"), tag: e.tagName,
                  box: [Math.round(r.x), Math.round(r.y), Math.round(r.width), Math.round(r.height)],
                  text_line_boxes: lb ? lb.line_count : null,
                  text_only: lb ? lb.text : null,
                  wrapped: lb ? lb.line_count >= 2 : false,
                  clipped_right: r.right > vw + 1, clipped_left: r.left < -1 };
    out.controls.push(rec);
    if (rec.wrapped) out.wrapped_controls.push(rec.text_only || rec.label || rec.testid);
    if (rec.clipped_right || rec.clipped_left) out.clipped_controls.push((rec.label || rec.testid) + (rec.clipped_right ? "|right" : "|left"));
  });
  out.status = "MEASURED";
  return out;
};

(async () => {
  const br = await chromium.launch({ channel: "chrome", headless: true });
  const report = { base: BASE, route: ROUTE, shapes: SHAPES, locales: LOCALES, generated_by: "_header_fit_r2.js", runs: [] };
  for (const locale of LOCALES) {
    for (const [w, h] of SHAPES) {
      const ctx = await br.newContext({ viewport: { width: w, height: h } });
      const page = await ctx.newPage();
      await page.addInitScript((l) => { try { localStorage.setItem("citynexus.locale", l); } catch (e) {} }, locale);
      await page.goto(BASE.replace(/\/$/, "") + "/v8/" + ROUTE, { waitUntil: "networkidle", timeout: 60000 });
      const ENTRY = ["使用封存的演示行程", "sealed demo", "Use the sealed demo journey", "封存演示"];
      let entryUsed = null, entryForRun = null, pathForRun = null;
      for (const label of ENTRY) {
        const loc = page.getByText(label, { exact: false }).first();
        if (await loc.count()) { try { await loc.click({ timeout: 4000 }); entryUsed = label; await page.waitForTimeout(4000); break; } catch (e) {} }
      }
      entryForRun = entryUsed;
      pathForRun = await page.evaluate(() => location.pathname);
      await page.waitForTimeout(1000);
      const m = await page.evaluate(MEASURE);
      m.locale = locale; m.shape = w + "x" + h;
      m.entry_used = entryForRun; m.reached_route = pathForRun;
      report.runs.push(m);
      fs.writeFileSync(OUT + "hdr2_" + ROUTE + "_" + locale + "_" + w + "x" + h + ".png", await page.screenshot({ type: "png" }));
      console.log((locale + " " + w + "x" + h).padEnd(14), m.status,
                  "header_h", String(m.header_box ? m.header_box[3] : 0).padStart(3),
                  "controls", String(m.controls.length).padStart(2),
                  "wrapped", String(m.wrapped_controls.length).padStart(2),
                  "clipped", String(m.clipped_controls.length).padStart(2),
                  "hscroll", m.horizontal_overflow ? "YES" : "no",
                  "sel=" + (m.header_selector_used || "-"));
      m.wrapped_controls.slice(0, 5).forEach((t) => console.log("        WRAPPED:", JSON.stringify(t)));
      m.clipped_controls.slice(0, 5).forEach((t) => console.log("        CLIPPED:", JSON.stringify(t)));
      await ctx.close();
    }
  }
  await br.close();
  const measured = report.runs.filter((r) => r.status === "MEASURED");
  const wrapped = measured.reduce((a, r) => a + r.wrapped_controls.length, 0);
  const clipped = measured.reduce((a, r) => a + r.clipped_controls.length, 0);
  const hs = report.runs.filter((r) => r.horizontal_overflow).length;
  report.summary = { runs: report.runs.length, runs_measured: measured.length,
                     runs_not_measured: report.runs.length - measured.length,
                     wrapped_controls: wrapped, clipped_controls: clipped,
                     runs_with_horizontal_overflow: hs,
                     verdict: (measured.length !== report.runs.length) ? "PARTIAL_NOT_MEASURED"
                              : (wrapped || clipped || hs) ? "HEADER_OVERFLOW_OR_WRAPS" : "HEADER_FITS" };
  fs.writeFileSync(OUT + "header_fit2_" + ROUTE + ".json", JSON.stringify(report, null, 1));
  console.log("TOTALS runs", report.runs.length, "measured", measured.length, "wrapped", wrapped,
              "clipped", clipped, "hscroll runs", hs, "| VERDICT", report.summary.verdict);
})().catch((e) => { console.log("FATAL", String(e).slice(0, 240)); process.exit(9); });
