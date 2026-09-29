// ORD-0430 (PARTIAL arm): the "after it has collapsed" state, measured against the text lines.
//
// What the commander could not accept (ledger :17653): after the pill takes its compact shape it
// still overlaps a line of body text.  So this instrument reports, per scroll rest, BOTH measures
// with the boxes themselves, not just a verdict:
//   `box`  = the readable element's border box,
//   `line` = Range.getClientRects(), one rect per painted line (a wrapped heading gives one rect
//            per line -- an element box cannot express that),
// and then sweeps the whole lower viewport on a 10 px grid to say how many candidate cells of the
// compact size are free of each kind of obstacle.  That grid is what decides whether "overlap 0
// while still visible" is reachable at all, instead of my asserting it.
const fs = require("fs");
const path = require("path");
const { chromium } = require("D:/moodle/CityNexus/frontend/node_modules/playwright");

const BASE = process.argv[2] || "http://127.0.0.1:4833";
const OUT = process.argv[3] || "D:/moodle/_qoder_ai_ord0387_20260928/ord0430_r4_census";
const ARM = process.argv[4] || "after_compact";
const SIZE = Number(process.argv[5] || 44);

const ENTRY = ["使用封存的演示行程", "Use the sealed demo journey", "sealed demo", "封存演示"];
const SCREENS = (process.env.SCREENS_CSV || "twin,discover,intelligence").split(",");
const READABLE = "h1,h2,h3,h4,h5,p,li,dt,dd,th,td,label,figcaption,summary";
const ACTIONABLE = 'button, a[href], input, select, textarea, [role="button"]';

const PROBE = async (cfg) => {
  const dock = document.querySelector('[data-testid="v18-copilot-dock"]');
  const nav = document.querySelector(".v8-mobile-nav");
  const vh = window.innerHeight;
  const vw = window.innerWidth;
  const R = cfg.READABLE;
  const A = cfg.ACTIONABLE;
  const size = cfg.SIZE;
  const out = {
    path: location.pathname,
    pill_present: !!dock,
    served_bundle: Array.from(document.querySelectorAll("script[src]")).map((s) => s.getAttribute("src")).filter(Boolean),
    viewport: { w: vw, h: vh },
    nav_top: nav ? Math.round(nav.getBoundingClientRect().top) : null,
    rests: [],
  };
  if (!dock) return out;
  const box = (r) => ({ left: Math.round(r.left), top: Math.round(r.top), right: Math.round(r.right), bottom: Math.round(r.bottom) });
  const px2 = (a, b) => {
    const w = Math.min(a.right, b.right) - Math.max(a.left, b.left);
    const h = Math.min(a.bottom, b.bottom) - Math.max(a.top, b.top);
    return w > 1 && h > 1 ? Math.round(w * h) : 0;
  };
  const scroller = document.scrollingElement || document.documentElement;
  const max = scroller.scrollHeight - scroller.clientHeight;
  for (const target of Array.from(new Set([0, Math.round(max / 2), max]))) {
    scroller.scrollTop = target;
    await new Promise((res) => window.setTimeout(res, 900));
    const p = box(dock.getBoundingClientRect());
    const readableBoxes = [];
    const readableLines = [];
    document.querySelectorAll(R).forEach((el) => {
      if (dock.contains(el) || el.contains(dock)) return;
      const r = el.getBoundingClientRect();
      if (r.width === 0 || r.height === 0 || r.bottom <= 0 || r.top >= vh) return;
      const text = (el.textContent || "").trim().slice(0, 40);
      if (!text) return;
      readableBoxes.push(Object.assign({ tag: el.tagName, text }, box(r)));
      const rg = document.createRange();
      rg.selectNodeContents(el);
      Array.from(rg.getClientRects()).forEach((q) => {
        if (q.width > 0 && q.height > 0) readableLines.push(Object.assign({ tag: el.tagName, text, line_top: Math.round(q.top) }, box(q)));
      });
    });
    const controls = [];
    document.querySelectorAll(A).forEach((el) => {
      if (dock.contains(el) || el.contains(dock)) return;
      const r = el.getBoundingClientRect();
      if (r.width === 0 || r.height === 0 || r.bottom <= 0 || r.top >= vh) return;
      controls.push(Object.assign({ tag: el.tagName, text: (el.textContent || "").trim().slice(0, 20) }, box(r)));
    });
    // full sweep on a 10 px grid, only inside the region above the fixed bar
    const lowerY = out.nav_top ? out.nav_top - 10 - size : vh - 10 - size;
    let tested = 0, freeBox = 0, freeLine = 0, freeBoth = 0, freeAll = 0;
    const firstFree = { freeLine: null, freeBoth: null, freeAll: null };
    for (let y = 10; y <= lowerY; y += 10) {
      for (let x = 10; x <= vw - 10 - size; x += 10) {
        const c = { left: x, top: y, right: x + size, bottom: y + size };
        tested += 1;
        const ob = readableBoxes.filter((b) => px2(b, c) > 0);
        const ol = readableLines.filter((b) => px2(b, c) > 0);
        const oc = controls.filter((b) => px2(b, c) > 0);
        if (!ob.length) freeBox += 1;
        if (!ol.length) freeLine += 1;
        if (!ol.length && !oc.length) freeBoth += 1;
        if (!ob.length && !ol.length && !oc.length) freeAll += 1;
        if (!ol.length && !firstFree.freeLine) firstFree.freeLine = [x, y];
        if (!ol.length && !oc.length && !firstFree.freeBoth) firstFree.freeBoth = [x, y];
        if (!ob.length && !ol.length && !oc.length && !firstFree.freeAll) firstFree.freeAll = [x, y];
      }
    }
    const cx = Math.round((p.left + p.right) / 2);
    const cy = Math.round((p.top + p.bottom) / 2);
    const at = document.elementFromPoint(cx, cy);
    out.rests.push({
      scrollTop: Math.round(scroller.scrollTop),
      pill_box: p,
      pill_attrs: { rest_overlap: dock.getAttribute("data-rest-overlap"), yield_slot: dock.getAttribute("data-yield-slot"), classes: String(dock.className) },
      centre: [cx, cy],
      centre_hit: at ? at.tagName + "." + String(at.className || "").slice(0, 18) : "none",
      centre_hit_is_pill: !!(at && dock.contains(at)),
      readable_box_count: readableBoxes.length,
      readable_line_count: readableLines.length,
      control_count: controls.length,
      box_overlap_px2_max: readableBoxes.reduce((m, b) => Math.max(m, px2(b, p)), 0),
      box_overlap_px2_sum: readableBoxes.reduce((a, b) => a + px2(b, p), 0),
      line_overlap_px2_max: readableLines.reduce((m, b) => Math.max(m, px2(b, p)), 0),
      line_overlap_px2_sum: readableLines.reduce((a, b) => a + px2(b, p), 0),
      boxes_over_pill: readableBoxes.filter((b) => px2(b, p) > 0).slice(0, 4),
      lines_over_pill: readableLines.filter((b) => px2(b, p) > 0).slice(0, 4),
      grid: { size, step: 10, cells_tested: tested, free_of_boxes: freeBox, free_of_lines: freeLine, free_of_lines_and_controls: freeBoth, free_of_everything: freeAll, first_free: firstFree },
      // the pill's own overlap with the nearest offending line, spelled out
      worst_line: readableLines.slice().sort((a, b) => px2(b, p) - px2(a, p))[0] || null,
    });
  }
  scroller.scrollTop = 0;
  return out;
};

(async () => {
  fs.mkdirSync(OUT, { recursive: true });
  const browser = await chromium.launch();
  const rep = { base: BASE, arm: ARM, compact_size: SIZE, screens: [] };
  for (const screen of SCREENS) {
    const ctx = await browser.newContext({ viewport: { width: 390, height: 844 } });
    const page = await ctx.newPage();
    const r = { screen, locales: {} };
    for (const locale of ["zh-CN", "en"]) {
      await page.goto(BASE + "/", { waitUntil: "domcontentloaded", timeout: 60000 }).catch(() => {});
      await page.evaluate((l) => localStorage.setItem("citynexus.locale", l), locale);
      await page.goto(BASE + "/v8/" + screen, { waitUntil: "domcontentloaded", timeout: 60000 }).catch(() => {});
      for (const label of ENTRY) {
        const loc = page.getByText(label, { exact: false }).first();
        if (await loc.count()) { await loc.click({ timeout: 8000 }).catch(() => {}); await page.waitForTimeout(2000); break; }
      }
      await page.goto(BASE + "/v8/" + screen, { waitUntil: "domcontentloaded", timeout: 60000 }).catch(() => {});
      await page.waitForTimeout(2600);
      r.locales[locale] = await page.evaluate(PROBE, { READABLE, ACTIONABLE, SIZE: SIZE });
    }
    rep.screens.push(r);
    await ctx.close();
  }
  await browser.close();
  const file = path.join(OUT, "collapse_census_" + ARM + ".json");
  fs.writeFileSync(file, JSON.stringify(rep, null, 1), "utf8");
  for (const s of rep.screens) {
    for (const k of Object.keys(s.locales)) {
      const p = s.locales[k];
      console.log(`${s.screen}/${k} bundle=${(p.served_bundle || [])[0]} nav_top=${p.nav_top}`);
      (p.rests || []).forEach((x) => console.log(
        `   scrollTop=${x.scrollTop} pill=${JSON.stringify(x.pill_box)} slot=${x.pill_attrs.yield_slot}` +
        ` boxMax=${x.box_overlap_px2_max} boxSum=${x.box_overlap_px2_sum}` +
        ` lineMax=${x.line_overlap_px2_max} centreHit=${x.centre_hit_is_pill ? "PILL" : x.centre_hit}` +
        ` grid cells=${x.grid.cells_tested} freeLines=${x.grid.free_of_lines} freeLinesCtl=${x.grid.free_of_lines_and_controls} freeAll=${x.grid.free_of_everything} firstFreeAll=${JSON.stringify(x.grid.first_free.freeAll)}`));
    }
  }
  console.log("WROTE", file, fs.statSync(file).size, "B");
})();
