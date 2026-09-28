/* ORD-0441 r1 -- does the aligned ladder actually reach the painted screen?
 *
 * Two readings per cell, both from getComputedStyle on the shipped bundle:
 *   tokens       -- the value :root resolves for each ladder token (proves it is in the artefact);
 *   distribution -- how many painted elements land on each font-size / radius / border-width / gap
 *                   value (proves the value reaches geometry rather than sitting unused, and shows
 *                   where a tier has NO consumer, which is a paper rule and must be named).
 * Nothing is asserted against a class name or a data attribute.
 *
 * Usage: node cmdr_ladder_reach_r1.js <base> <out.json> <label>
 */
const { chromium } = require("D:/moodle/CityNexus/frontend/node_modules/playwright");
const fs = require("fs");

const BASE = (process.argv[2] || "http://127.0.0.1:4805/").replace(/\/$/, "");
const OUT = process.argv[3] || "D:/moodle/_qoder_q_ord0441_20260929/_ladder.json";
const LABEL = process.argv[4] || "arm";

const TOKENS = ["--cn-fs-card", "--cn-fs-body", "--cn-fs-meta", "--cn-fs-caption", "--cn-r-control",
                "--cn-r-button", "--cn-r-card", "--cn-divider-w", "--cn-s-2", "--cn-s-4", "--cn-s-6",
                "--cn-s-10", "--cn-s-16", "--cn-gutter", "--cn-nav-icon-size", "--cn-touch-min"];
const PATHS = ["/v8/hub", "/v8/live", "/v8/stay", "/v8/discover"];

async function read(page) {
  return page.evaluate(({ TOKENS }) => {
    const root = getComputedStyle(document.documentElement);
    const tokens = {};
    for (const t of TOKENS) tokens[t] = root.getPropertyValue(t).trim() || null;
    const acc = { fontSize: {}, borderTopLeftRadius: {}, borderTopWidth: {}, columnGap: {}, rowGap: {} };
    let painted = 0;
    for (const el of document.querySelectorAll("body *")) {
      const cs = getComputedStyle(el);
      if (cs.display === "none" || cs.visibility === "hidden" || cs.opacity === "0") continue;
      if (el.offsetHeight <= 0 && el.offsetWidth <= 0) continue;
      painted += 1;
      for (const key of Object.keys(acc)) {
        const v = cs[key];
        if (!v || v === "normal" || v === "auto" || v === "0px" && key !== "borderTopWidth") continue;
        acc[key][v] = (acc[key][v] || 0) + 1;
      }
    }
    const top = (o, n) => Object.entries(o).sort((a, b) => b[1] - a[1] || String(a[0]).localeCompare(String(b[0]))).slice(0, n);
    return { tokens, painted, fontSize: top(acc.fontSize, 14), radius: top(acc.borderTopLeftRadius, 12),
             borderTop: top(acc.borderTopWidth, 8), columnGap: top(acc.columnGap, 10), rowGap: top(acc.rowGap, 10) };
  }, { TOKENS });
}

(async () => {
  const browser = await chromium.launch({ channel: "chrome", headless: true });
  const cells = [];
  for (const vp of [{ width: 390, height: 844 }, { width: 414, height: 896 }]) {
    for (const locale of ["zh-CN", "en"]) {
      for (const path of PATHS) {
        const ctx = await browser.newContext({ viewport: vp, hasTouch: true, locale });
        const page = await ctx.newPage();
        const errors = [];
        page.on("pageerror", (e) => errors.push(String(e).slice(0, 180)));
        const rec = { label: LABEL, base: BASE, viewport: `${vp.width}x${vp.height}`, arm: locale, path, errors };
        try {
          await page.goto(BASE + path, { waitUntil: "networkidle", timeout: 90000 });
          await page.waitForTimeout(1200);
          const one = await read(page);
          rec.tokens = one.tokens;
          rec.distribution = one;
        } catch (e) {
          rec.fatal = String(e).slice(0, 180);
        }
        cells.push(rec);
        await ctx.close();
      }
    }
  }
  await browser.close();
  fs.writeFileSync(OUT, JSON.stringify({ at: new Date().toISOString(), base: BASE, label: LABEL,
                                          screens: PATHS, cells }, null, 1) + "\n", "utf-8");
  const c = cells.find((x) => x.tokens);
  console.log("%s tokens: %s", LABEL, JSON.stringify(c ? c.tokens : {}));
  console.log("%s hub fontSize: %s", LABEL, JSON.stringify(c ? c.distribution.fontSize.slice(0, 8) : []));
  console.log("cells: %d -> %s", cells.length, OUT);
})();
