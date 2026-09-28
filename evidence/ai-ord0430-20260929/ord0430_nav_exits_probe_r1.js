// ORD-0430: does the reserved bottom band have anything a relocated pill could occupy without
// sitting on another exit?  The previous run reported no nav because it skipped the locale write
// and the second navigation that the working audit uses -- the onboarding shell intentionally
// renders no `.v8-mobile-nav` (design-tokens.css:1055), so the sequence below is the same one the
// band audit uses. Output is a per-exit enumeration with rects, plus an in-band collision grid.
const fs = require("fs");
const { chromium } = require("D:/moodle/CityNexus/frontend/node_modules/playwright");

const BASE = process.argv[2] || "http://127.0.0.1:4811";
const OUT = process.argv[3] || "D:/moodle/_qoder_ai_ord0387_20260928/ord0430_band_audit/nav_exits_before_arm.json";
const SCREENS = ["twin", "discover", "intelligence"];
const ENTRY = ["使用封存的演示行程", "Use the sealed demo journey", "sealed demo", "封存演示"];

const PROBE = () => {
  const nav = document.querySelector(".v8-mobile-nav");
  const vh = window.innerHeight;
  const out = { path: location.pathname, nav_present: !!nav, viewport_h: vh, rests: [] };
  if (!nav) return out;
  const nr = nav.getBoundingClientRect();
  out.nav = { top: Math.round(nr.top), bottom: Math.round(nr.bottom), left: Math.round(nr.left), right: Math.round(nr.right), position: getComputedStyle(nav).position };
  const exits = Array.from(nav.querySelectorAll("button, a[href]")).map((el, i) => {
    const r = el.getBoundingClientRect();
    return { i, tag: el.tagName, text: (el.textContent || "").trim().slice(0, 24), aria: el.getAttribute("aria-label"), rect: { left: Math.round(r.left), top: Math.round(r.top), right: Math.round(r.right), bottom: Math.round(r.bottom) } };
  });
  out.nav_exit_count = exits.length;
  out.nav_exits = exits;
  const scroller = document.scrollingElement || document.documentElement;
  const max = scroller.scrollHeight - scroller.clientHeight;
  for (const target of Array.from(new Set([0, Math.round(max / 2), max]))) {
    scroller.scrollTop = target;
    const ink = [];
    document.querySelectorAll("h1,h2,h3,h4,h5,p,li,dt,dd,th,td,label,figcaption,summary").forEach((el) => {
      if (nav.contains(el)) return;
      const rg = document.createRange();
      rg.selectNodeContents(el);
      Array.from(rg.getClientRects()).forEach((r) => {
        if (r.width > 0 && r.height > 0 && r.bottom > 0 && r.top < vh) ink.push({ left: Math.round(r.left), top: Math.round(r.top), right: Math.round(r.right), bottom: Math.round(r.bottom) });
      });
    });
    const ctl = exits.map((e) => e.rect);
    const inter = (a, b) => (Math.min(a.right, b.right) - Math.max(a.left, b.left) > 1) && (Math.min(a.bottom, b.bottom) - Math.max(a.top, b.top) > 1);
    // every 44px cell whose vertical span falls inside the band
    const cells = [];
    for (let top = out.nav.top; top + 44 <= out.nav.bottom + 1; top += 44) {
      for (const left of [10, 173, 336]) {
        const c = { left, top: Math.round(top), right: left + 44, bottom: Math.round(top) + 44 };
        cells.push({
          cell: [c.left, c.top],
          exits_overlapped: ctl.filter((r) => inter(r, c)).length,
          ink_overlapped: ink.filter((r) => inter(r, c)).length,
        });
      }
    }
    out.rests.push({
      scrollTop: Math.round(scroller.scrollTop),
      ink_rects_in_viewport: ink.length,
      cells_tested: cells.length,
      cells_free_of_exits: cells.filter((x) => x.exits_overlapped === 0).length,
      cells_free_of_exits_and_ink: cells.filter((x) => x.exits_overlapped === 0 && x.ink_overlapped === 0).length,
      cells,
    });
  }
  scroller.scrollTop = 0;
  return out;
};

(async () => {
  fs.mkdirSync(require("path").dirname(OUT), { recursive: true });
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
      r.locales[locale] = await page.evaluate(PROBE);
    }
    rep.screens.push(r);
    await ctx.close();
  }
  await browser.close();
  fs.writeFileSync(OUT, JSON.stringify(rep, null, 1), "utf8");
  for (const s of rep.screens) {
    for (const k of Object.keys(s.locales)) {
      const p = s.locales[k];
      console.log(`${s.screen}/${k} nav_present=${p.nav_present}` + (p.nav ? ` band=${p.nav.top}..${p.nav.bottom} exits=${p.nav_exit_count} ` +
        p.nav_exits.map((e) => `${e.aria || e.text}@${e.rect.top}-${e.rect.bottom}`).join(" | ") : ""));
      (p.rests || []).forEach((x) => console.log(`   scrollTop=${x.scrollTop} cells_tested=${x.cells_tested} free_of_exits=${x.cells_free_of_exits} free_of_exits_and_ink=${x.cells_free_of_exits_and_ink}`));
    }
  }
  console.log("WROTE", OUT, fs.statSync(OUT).size, "B");
})();
