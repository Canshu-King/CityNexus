/* ORD-0459 r2 -- which elements did the radius ladder move, with a noise floor that can be believed.
 *
 * The first version of this instrument took its two same-arm shots straight after the demo click, so
 * the map tiles were still arriving: the before arm's own floor came back at 21,772 changed pixels,
 * which is larger than most real corner changes and useless as a threshold. This version waits for
 * the tile channel to go quiet (the resource-timing buffer is polled until its openstreetmap count
 * stops moving), then shoots:
 *   pass1.png / pass2.png      the 390x844 viewport, twice -- the floor and the comparison
 *   pass1_full.png / pass2_full.png  the whole document, so elements below the fold get a frame too
 * and per sampled element it records identity, computed radius, its box, and whether that box is
 * inside the viewport of the first frame.
 *
 * Usage: node cmdr_radii_diff_r2.js <base> <out-dir> <label>
 */
const { chromium } = require("D:/moodle/CityNexus/frontend/node_modules/playwright");
const fs = require("fs");

const BASE = (process.argv[2] || "").replace(/\/$/, "");
const OUT = process.argv[3];
const LABEL = process.argv[4] || "arm";
const VP = { width: +(process.argv[5] || 390), height: +(process.argv[6] || 844) };

async function settleTiles(page, maxMs) {
  const started = Date.now();
  let last = -1, stableFor = 0;
  while (Date.now() - started < maxMs) {
    const n = await page.evaluate(() => performance.getEntriesByType("resource")
      .filter((e) => /tile\.openstreetmap\.org/.test(e.name)).length);
    if (n === last) { stableFor += 1; } else { stableFor = 0; last = n; }
    if (stableFor >= 3) return { tile_resources: n, waited_ms: Date.now() - started, settled: true };
    await page.waitForTimeout(700);
  }
  return { tile_resources: last, waited_ms: Date.now() - started, settled: false };
}

function sample(page) {
  return page.evaluate(() => {
    const sel = "button, [class*=card], [class*=panel], input";
    const out = [];
    document.querySelectorAll(sel).forEach((el, i) => {
      const cs = getComputedStyle(el);
      if (cs.display === "none" || cs.visibility === "hidden") return;
      const r = el.getBoundingClientRect();
      if (r.width < 2 || r.height < 2) return;
      out.push({
        i,
        tag: el.tagName.toLowerCase(),
        cls: (el.className && el.className.baseVal !== undefined ? el.className.baseVal : String(el.className || "")).slice(0, 70),
        testid: el.getAttribute("data-testid") || null,
        radius: cs.borderRadius,
        rect: [Math.round(r.x), Math.round(r.y), Math.round(r.width), Math.round(r.height)],
        in_viewport: r.y >= 0 && r.y + r.height <= innerHeight && r.x >= 0 && r.x + r.width <= innerWidth,
      });
    });
    return out;
  });
}

(async () => {
  fs.mkdirSync(OUT, { recursive: true });
  const b = await chromium.launch({ chromiumSandbox: false });
  const ctx = await b.newContext({ viewport: VP, locale: "zh-CN" });
  const p = await ctx.newPage();
  const console_errors = [];
  p.on("console", (m) => { if (m.type() === "error") console_errors.push(m.text().slice(0, 200)); });
  p.on("pageerror", (e) => console_errors.push("pageerror " + String(e).slice(0, 200)));
  await p.goto(BASE + "/", { waitUntil: "networkidle", timeout: 60000 });
  const e = p.getByText("使用封存的演示行程", { exact: false }).first();
  if (await e.count()) await e.click({ timeout: 8000 }).catch(() => {});
  const settle = await settleTiles(p, 25000);
  await p.waitForTimeout(1200);
  const elements = await sample(p);
  await p.screenshot({ path: OUT + "/pass1.png" });
  await p.waitForTimeout(1500);
  await p.screenshot({ path: OUT + "/pass2.png" });
  await p.screenshot({ path: OUT + "/pass1_full.png", fullPage: true });
  await p.waitForTimeout(1200);
  await p.screenshot({ path: OUT + "/pass2_full.png", fullPage: true });
  const tally = {};
  for (const el of elements) tally[el.radius] = (tally[el.radius] || 0) + 1;
  fs.writeFileSync(OUT + "/elements.json", JSON.stringify({
    base: BASE, label: LABEL, viewport: `${VP.width}x${VP.height}`, settle, console_errors,
    sampled: elements.length, radius_tally: tally, elements }, null, 1) + "\n", "utf-8");
  console.log("%s: %d elements, tile settle %s, tally %s", LABEL, elements.length, JSON.stringify(settle), JSON.stringify(tally));
  await b.close();
})();
