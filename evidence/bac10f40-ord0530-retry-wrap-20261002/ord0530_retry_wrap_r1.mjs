/**
 * ORD-0530 reach, second instrument -- how many lines does that button's text actually paint?
 *
 * The reach gauge found the phone-shaped `重读一次` button rendered 48 px wide and 105 px tall, which
 * is not what a one-line button looks like.  A bounding box cannot prove wrapping (the memory of this
 * project is that wrapping is only provable with `Range.getClientRects()` -- `boundingBox()` on a
 * wrapped element just returns the enclosing rectangle), so this measures the text range itself:
 * one client rect per painted line, plus the line height that turns those rects into a height claim.
 */
import { chromium } from "playwright";
import { mkdirSync, writeFileSync } from "node:fs";

const BASE = process.env.ORD0530_BASE;
const JOURNEY = process.env.ORD0530_JOURNEY || "22222222-2222-4222-8222-222222222222";
const args = process.argv.slice(2);
const outDir = args[args.indexOf("--out") + 1];
const tag = args[args.indexOf("--tag") + 1];
mkdirSync(outDir, { recursive: true });

const SHAPES = [{ name: "phone_390x844", width: 390, height: 844 },
                { name: "desktop_1280x900", width: 1280, height: 900 }];
const browser = await chromium.launch();
const report = { base: BASE, journey: JOURNEY, tag, shapes: [] };

for (const shape of SHAPES) {
  const context = await browser.newContext({ viewport: { width: shape.width, height: shape.height },
                                            locale: "zh-CN", timezoneId: "America/Los_Angeles" });
  const page = await context.newPage();
  await page.addInitScript((o) => {
    localStorage.setItem("citynexus.v8.journey_id", o.journey);
    localStorage.setItem("citynexus.locale", "zh-CN");
  }, { journey: JOURNEY });
  await page.goto(`${BASE}/v8/footprints`, { waitUntil: "load", timeout: 60000 });
  await page.waitForSelector("[data-testid='footprint-retry']", { timeout: 30000 });
  await page.waitForTimeout(2200);

  const read = await page.evaluate(() => {
    const el = document.querySelector("[data-testid='footprint-retry']");
    const r = el.getBoundingClientRect();
    const cs = getComputedStyle(el);
    const rects = [];
    const walk = (node) => {
      if (node.nodeType === 3 && node.textContent.trim()) {
        const rg = document.createRange();
        rg.selectNodeContents(node);
        for (const rr of Array.from(rg.getClientRects())) {
          if (rr.width > 0 && rr.height > 0) rects.push({ x: Math.round(rr.x), y: Math.round(rr.y),
                                                          w: Math.round(rr.width), h: Math.round(rr.height) });
        }
      }
      for (const c of node.childNodes) walk(c);
    };
    walk(el);
    const distinctRows = [...new Set(rects.map((x) => x.y))].sort((a, b) => a - b);
    const parent = el.parentElement;
    const pcs = parent ? getComputedStyle(parent) : null;
    return { text: el.innerText.replace(/\s+/g, " ").trim(),
             char_count: el.innerText.replace(/\s+/g, "").length,
             box: { x: Math.round(r.x), y: Math.round(r.y), w: Math.round(r.width), h: Math.round(r.height) },
             computed: { font_size: cs.fontSize, line_height: cs.lineHeight, padding: cs.padding,
                         white_space: cs.whiteSpace, width: cs.width, min_height: cs.minHeight },
             text_rects: rects, painted_lines: distinctRows.length,
             parent_tag: parent ? parent.tagName.toLowerCase() + "." + String(parent.className) : null,
             parent_display: pcs ? pcs.display : null,
             parent_width: parent ? Math.round(parent.getBoundingClientRect().width) : null };
  });
  await page.screenshot({ path: `${outDir}/retry_${tag}_${shape.name}.png` });
  report.shapes.push({ shape, read });
  await context.close();
}
await browser.close();
report.phone_wraps = report.shapes[0].read.painted_lines;
report.desktop_wraps = report.shapes[1].read.painted_lines;
writeFileSync(`${outDir}/retry_${tag}.json`, JSON.stringify(report, null, 1), "utf8");
for (const s of report.shapes) {
  console.log(s.shape.name, "text", JSON.stringify(s.read.text), "box", JSON.stringify(s.read.box),
              "painted_lines", s.read.painted_lines, "white-space", s.read.computed.white_space,
              "parent_display", s.read.parent_display, "parent_width", s.read.parent_width);
}
console.log("out", `${outDir}/retry_${tag}.json`);
