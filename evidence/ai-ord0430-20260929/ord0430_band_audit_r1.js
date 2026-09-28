// ORD-0430 (round 2) band audit: where in the viewport may a fixed accessory sit without
// newly hiding text the traveller is reading?
//
// Two measures are recorded for every readable node, because they answer different questions:
//   box  = the element's own border box. Block-level text spans the whole content column, so a
//          right-edge control "overlaps" it even when it covers no glyph.
//   ink  = Range.getClientRects() of the node's text, i.e. where glyphs are actually painted,
//          line by line (a wrapped heading yields one rect per line).
// The nav band is measured on the untouched before-arm bundle so the claim "the fixed bar already
// sits on that text" is a reading, not an assumption.
const fs = require("fs");
const { chromium } = require("D:/moodle/CityNexus/frontend/node_modules/playwright");

const BASE = process.env.BASE || "http://127.0.0.1:4811";
const OUT = process.env.OUT || "D:/moodle/_qoder_ai_ord0387_20260928/ord0430_band_audit";
const SCREENS = (process.env.SCREENS || "twin,discover").split(",");
const ENTRY = ["使用封存的演示行程", "Use the sealed demo journey", "sealed demo", "封存演示"];
const READABLE = "h1,h2,h3,h4,h5,p,li,dt,dd,th,td,label,figcaption,summary";

const PROBE = (READABLE_SEL) => {
  const dock = document.querySelector('[data-testid="v18-copilot-dock"]');
  const nav = document.querySelector(".v8-mobile-nav");
  const vh = window.innerHeight, vw = window.innerWidth;
  const rectOf = (el) => {
    const r = el.getBoundingClientRect();
    return { top: Math.round(r.top), bottom: Math.round(r.bottom), left: Math.round(r.left), right: Math.round(r.right) };
  };
  const inkOf = (el) => {
    const out = [];
    (el.textContent || "").trim() && (() => {
      const rg = document.createRange();
      rg.selectNodeContents(el);
      for (const r of Array.from(rg.getClientRects())) {
        if (r.width > 0 && r.height > 0) out.push({ top: Math.round(r.top), bottom: Math.round(r.bottom), left: Math.round(r.left), right: Math.round(r.right) });
      }
    })();
    return out;
  };
  const inter = (a, b) => {
    const w = Math.min(a.right, b.right) - Math.max(a.left, b.left);
    const h = Math.min(a.bottom, b.bottom) - Math.max(a.top, b.top);
    return w > 1 && h > 1 ? Math.round(w * h) : 0;
  };
  const scroller = document.scrollingElement || document.documentElement;
  const out = { viewport: { w: vw, h: vh }, nav: nav ? Object.assign(rectOf(nav), { position: getComputedStyle(nav).position }) : null, dock: dock ? rectOf(dock) : null, rests: [] };
  const max = scroller.scrollHeight - scroller.clientHeight;
  const stops = Array.from(new Set([0, Math.round(max / 2), max]));
  for (const target of stops) {
    scroller.scrollTop = target;
    const nodes = [];
    document.querySelectorAll(READABLE_SEL).forEach((el) => {
      if (dock && (dock.contains(el) || el.contains(dock))) return;
      if (nav && nav.contains(el)) return;
      const b = rectOf(el);
      if (b.bottom <= 0 || b.top >= vh) return;
      const text = (el.textContent || "").trim().slice(0, 40);
      if (!text) return;
      const ink = inkOf(el);
      const n = out.nav || { top: vh, bottom: vh, left: 0, right: vw };
      const d = out.dock || { top: -1, bottom: -1, left: -1, right: -1 };
      nodes.push({
        tag: el.tagName, text,
        box_in_nav_px: inter(b, n), ink_in_nav_px: ink.reduce((a, r) => a + inter(r, n), 0),
        box_in_dock_px: inter(b, d), ink_in_dock_px: ink.reduce((a, r) => a + inter(r, d), 0),
        box: b, ink,
      });
    });
    out.rests.push({
      scrollTop: Math.round(scroller.scrollTop),
      readable_nodes: nodes.length,
      boxes_over_nav: nodes.filter((x) => x.box_in_nav_px > 0).length,
      inks_over_nav: nodes.filter((x) => x.ink_in_nav_px > 0).length,
      boxes_over_dock: nodes.filter((x) => x.box_in_dock_px > 0).length,
      inks_over_dock: nodes.filter((x) => x.ink_in_dock_px > 0).length,
      max_box_over_dock_px: nodes.reduce((a, x) => Math.max(a, x.box_in_dock_px), 0),
      max_ink_over_dock_px: nodes.reduce((a, x) => Math.max(a, x.ink_in_dock_px), 0),
      free_band_px: (() => {
        // vertical gaps inside the viewport that no readable ink occupies, at least 42 px tall
        const spans = nodes.filter((x) => x.top !== undefined).map((x) => [0, vh]).map((s) => {
          const own = x.ink.length ? x.ink : [x.box];
          return own.reduce((a, r) => [Math.min(a[0], r.top), Math.max(a[1], r.bottom)], [vh, 0]);
        });
        const marks = [0, vh];
        spans.forEach((s) => { marks.push(s[0], s[1]); });
        marks.sort((a, b) => a - b);
        let best = 0, bestTop = 0;
        for (let i = 1; i < marks.length; i++) {
          const g = marks[i] - marks[i - 1];
          if (g > best && marks[i] <= vh) { best = g; bestTop = marks[i - 1]; }
        }
        return { tallest_px_no_ink: best, from_y: bestTop };
      })(),
      nodes: nodes.slice(0, 10),
    });
  }
  scroller.scrollTop = 0;
  return out;
};

(async () => {
  fs.mkdirSync(OUT, { recursive: true });
  const browser = await chromium.launch();
  const rep = { base: BASE, screens: [] };
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
      r.locales[locale] = await page.evaluate(PROBE, READABLE);
    }
    rep.screens.push(r);
    await ctx.close();
  }
  await browser.close();
  const file = OUT + "/band_audit_before_arm.json";
  fs.writeFileSync(file, JSON.stringify(rep, null, 1), "utf8");
  for (const s of rep.screens) {
    for (const k of Object.keys(s.locales)) {
      const p = s.locales[k];
      console.log(`${s.screen}/${k} nav=${JSON.stringify(p.nav)} dock=${JSON.stringify(p.dock)}`);
      p.rests.forEach((x, i) => console.log(`   rest${i} scrollTop=${x.scrollTop} nodes=${x.readable_nodes}` +
        ` boxesOverNav=${x.boxes_over_nav} inksOverNav=${x.inks_over_nav}` +
        ` boxesOverDock=${x.boxes_over_dock} inksOverDock=${x.inks_over_dock}` +
        ` maxBox=${x.max_box_over_dock_px} maxInk=${x.max_ink_over_dock_px} gap=${JSON.stringify(x.free_band_px)}`));
    }
  }
  console.log("WROTE", file, fs.statSync(file).size, "B");
})();
