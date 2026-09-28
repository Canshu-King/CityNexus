// ORD-0430 geometry probe (r1): how tall a band does the idle pill actually take off the
// bottom of the phone viewport, and which inset rule is in force at 390x844.
// Why this exists: the ledger block first quoted "bottom 22px => 76px of band", which is the
// DESKTOP inset from styles.css:354. At 390px width the media query at styles.css:740 and the
// idle-compact rule in design-tokens.css:980 are what apply, so the inset has to be read off
// the rendered page, not off whichever rule a human happened to grep first.
// Read-only: no clicks that change product state, no writes to the app.
const fs = require("fs");
const { chromium } = require("D:/moodle/CityNexus/frontend/node_modules/playwright");

const BASE = process.env.BASE || "http://127.0.0.1:4811";
const OUT = process.env.OUT || "D:/moodle/_qoder_ai_ord0387_20260928/wt/evidence/ai-ord0430-20260929";
const ARM = process.env.ARM || "before";
const SCREENS = ["twin"];
const ENTRY = ["使用封存的演示行程", "Use the sealed demo journey", "sealed demo", "封存演示"];

const PROBE = () => {
  const dock = document.querySelector('[data-testid="v18-copilot-dock"]');
  if (!dock) return null;
  const cs = getComputedStyle(dock);
  const r = dock.getBoundingClientRect();
  const scripts = Array.from(document.querySelectorAll("script[src]")).map((s) => s.getAttribute("src"));
  // the readable node the collision ruler reported as covered on this screen
  const heads = Array.from(document.querySelectorAll("h1,h2,h3,h4,h5,p,li"));
  const inBand = heads
    .map((el) => {
      const b = el.getBoundingClientRect();
      return { tag: el.tagName, text: (el.textContent || "").trim().slice(0, 60), top: Math.round(b.top), bottom: Math.round(b.bottom) };
    })
    .filter((x) => x.bottom > r.top && x.top < r.bottom && x.top >= 0);
  return {
    viewport: { w: window.innerWidth, h: window.innerHeight },
    served_bundle: scripts.filter((s) => s && s.indexOf("/assets/index-") === 0),
    dock_rect: { top: Math.round(r.top), bottom: Math.round(r.bottom), left: Math.round(r.left), right: Math.round(r.right), w: Math.round(r.width), h: Math.round(r.height) },
    dock_inset: { right_specified: cs.right, bottom_specified: cs.bottom, position: cs.position, width_specified: cs.width },
    band_from_dock_top_to_viewport_bottom_px: Math.round(window.innerHeight - r.top),
    pill_painted_h_px: Math.round(r.height),
    readable_in_pill_band: inBand,
    classes: String(dock.className),
  };
};

(async () => {
  fs.mkdirSync(OUT, { recursive: true });
  const browser = await chromium.launch();
  const rep = { base: BASE, arm: ARM, note: "insets read off the rendered page at 390x844", screens: [] };
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
  const file = OUT + "/pill_geometry_" + ARM + "_arm_r1.json";
  fs.writeFileSync(file, JSON.stringify(rep, null, 1), "utf8");
  for (const s of rep.screens) {
    for (const k of Object.keys(s.locales)) {
      const p = s.locales[k];
      if (!p) { console.log(s.screen + "/" + k + ": NO DOCK"); continue; }
      console.log(`${s.screen}/${k}: rect=${JSON.stringify(p.dock_rect)} inset_right=${p.dock_inset.right_specified} inset_bottom=${p.dock_inset.bottom_specified} band=${p.band_from_dock_top_to_viewport_bottom_px} bundle=${p.served_bundle}`);
    }
  }
  console.log("WROTE", file, fs.statSync(file).size, "B");
})();
