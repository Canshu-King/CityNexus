/* CMDR ORD-0406 acceptance r1 - is the safety hint actually reachable above the fixed bottom bar?
 *
 * The defect: `.v8-mobile-nav` is `position: fixed` and eats the bottom 76 px of the first screen, and
 * the attention message ("this journey has no trustworthy coordinates yet") sat inside that band, so a
 * traveller on a phone could not read or tap it.  The fix is supposed to give the scroll container its
 * own bottom clearance.
 *
 * Per shape and per arm this reports, from the RENDERED page:
 *   - the message's own text (so the verdict is about a sentence a human can read, not a flag)
 *   - its box, the nav's box, and whether the two overlap
 *   - a hit-test at the message's centre: does the element under that point belong to the message?
 *   - the same hit-test after scrolling the message to the middle of the viewport (reachability in the
 *     ORD-0338 甲 sense: reachable after scrolling counts, only never-reachable is red)
 * Usage: node cmdr_ord0406_band_hit_r1.js <base> <out-file>
 */
const { chromium } = require("D:/moodle/CityNexus/frontend/node_modules/playwright");
const fs = require("fs");

const BASE = process.argv[2];
const OUT = process.argv[3];
if (!BASE || !OUT) { console.error("usage: node cmdr_ord0406_band_hit_r1.js <base> <out-file>"); process.exit(2); }
const SHAPES = [[390, 844], [360, 800], [414, 896], [320, 653]];
const ARMS = ["zh", "en"];

async function run(browser, base, w, h, locale) {
  const ctx = await browser.newContext({ viewport: { width: w, height: h }, hasTouch: true, locale });
  const page = await ctx.newPage();
  const errs = [];
  page.on("pageerror", (e) => errs.push(String(e).slice(0, 160)));
  const out = { shape: `${w}x${h}`, locale, entry: null, found: false };
  try {
    await page.goto(base, { waitUntil: "networkidle", timeout: 90000 });
    out.entry = await page.evaluate(() =>
      Array.from(document.querySelectorAll('script[src*="assets/index-"]')).map((s) => s.getAttribute("src")));
    for (const cand of [page.getByText("使用封存的演示行程", { exact: false }).first(),
                        page.getByText(/sealed demo trip/i).first()]) {
      if (await cand.count()) { await cand.click(); await page.waitForTimeout(4500); break; }
    }
    const m = await page.evaluate(() => {
      const el = document.querySelector(".v8-message");
      const nav = document.querySelector(".v8-mobile-nav");
      if (!el) return { found: false, navPresent: !!nav };
      const r = el.getBoundingClientRect();
      const nr = nav ? nav.getBoundingClientRect() : null;
      const cx = Math.round(r.left + r.width / 2), cy = Math.round(r.top + r.height / 2);
      const top = document.elementFromPoint(cx, cy);
      return {
        found: true,
        text: (el.innerText || "").trim().replace(/\s+/g, " ").slice(0, 120),
        box: { top: Math.round(r.top), bottom: Math.round(r.bottom), height: Math.round(r.height) },
        centre: [cx, cy],
        navTop: nr ? Math.round(nr.top) : null,
        overlapsNav: nr ? (r.bottom > nr.top && r.top < nr.bottom) : null,
        hitTestLandsOnMessage: !!(top && (top === el || el.contains(top))),
        fullyInView: r.top >= 0 && r.bottom <= window.innerHeight,
      };
    });
    Object.assign(out, m);
    if (m.found && !(m.box.top >= 0 && m.box.bottom <= h)) {
      await page.evaluate(() => {
        const el = document.querySelector(".v8-message");
        el.scrollIntoView({ block: "center" });
      });
      await page.waitForTimeout(700);
      out.afterScroll = await page.evaluate(() => {
        const el = document.querySelector(".v8-message");
        const nav = document.querySelector(".v8-mobile-nav");
        const r = el.getBoundingClientRect();
        const nr = nav ? nav.getBoundingClientRect() : null;
        const cx = Math.round(r.left + r.width / 2), cy = Math.round(r.top + r.height / 2);
        const top = document.elementFromPoint(cx, cy);
        return { box: { top: Math.round(r.top), bottom: Math.round(r.bottom) },
                 centre: [cx, cy],
                 navTop: nr ? Math.round(nr.top) : null,
                 overlapsNav: nr ? (r.bottom > nr.top && r.top < nr.bottom) : null,
                 hitTestLandsOnMessage: !!(top && (top === el || el.contains(top))),
                 fullyInView: r.top >= 0 && r.bottom <= window.innerHeight };
      });
    }
    out.pageErrors = errs.length;
  } finally {
    await ctx.close();
  }
  return out;
}

async function main() {
  const browser = await chromium.launch({ channel: "chrome", headless: true });
  const cells = [];
  for (const arm of ARMS) for (const [w, h] of SHAPES) cells.push(await run(browser, BASE, w, h, arm));
  await browser.close();
  const missing = cells.filter((c) => !c.found).map((c) => `${c.shape}/${c.locale}`);
  const reachable = cells.filter((c) => c.found && ((c.hitTestLandsOnMessage && c.overlapsNav === false) ||
    (c.afterScroll && c.afterScroll.hitTestLandsOnMessage && c.afterScroll.overlapsNav === false)));
  const report = {
    instrument: "cmdr_ord0406_band_hit_r1", base: BASE, shapes: SHAPES.map(([w, h]) => `${w}x${h}`), arms: ARMS,
    cells,
    summary: {
      cellsExpected: SHAPES.length * ARMS.length,
      cellsWithMessageFound: cells.filter((c) => c.found).length,
      cellsWithoutMessage: missing,
      cellsReachableAboveNav: reachable.length,
      verdict: (missing.length === 0 && reachable.length === cells.length)
        ? "SAFETY_HINT_REACHABLE_IN_EVERY_SHAPE_AND_ARM"
        : (missing.length ? "MESSAGE_NOT_RENDERED_IN_" + missing.length + "_CELLS" : "SOME_CELLS_STILL_COVERED"),
    },
  };
  fs.writeFileSync(OUT, JSON.stringify(report, null, 2));
  console.log(JSON.stringify({ out: OUT, summary: report.summary,
    perCell: cells.map((c) => ({ s: c.shape, l: c.locale, found: c.found, overlapsNav: c.overlapsNav ?? null,
      hit: c.hitTestLandsOnMessage ?? null, afterScrollHit: c.afterScroll ? c.afterScroll.hitTestLandsOnMessage : "n/a",
      text: (c.text || "").slice(0, 40) })) }, null, 2));
}
main().catch((e) => { console.error("FATAL", e); process.exit(1); });
