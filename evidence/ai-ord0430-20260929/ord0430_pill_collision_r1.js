/* ORD-0430 pill-vs-readable-text collision ruler.
 *
 * Reuses the published scan instrument's navigation (both-locale demo entry, and the walk over every
 * scrollable so readings are taken at REST, not mid-scroll) and adds the one thing it does not read:
 * whether the floating Copilot pill covers text a person is trying to READ.
 *
 * Two overlaps are recorded and they are not the same claim:
 *   band_overlap_px    -- the pill's resting layout box (offsetLeft/Top, what the dock's own measure
 *                         uses at frontend/src/features/agent/CopilotDock.tsx:695). What the detector sees.
 *   painted_overlap_px -- the actually painted rect. What the traveller's eyes see. When the pill
 *                         steps aside, band overlap stays > 0 while painted overlap must fall to 0.
 * Both are recomputed AT EVERY SCROLL POSITION: reading the geometry once before the walk would
 * report stale rectangles, which is the mistake this file's first draft made and was rebuilt for.
 *
 * Reachability is asserted independently of coverage: hit-test at the pill's own painted bottom-centre
 * must land inside it, and a real click must open the panel. Nothing trusts a data attribute for
 * geometry; the attributes are recorded only as corroboration.
 */
const { chromium } = require("D:/moodle/CityNexus/frontend/node_modules/playwright");
const fs = require("fs");

const BASE = process.argv[2] || "http://127.0.0.1:4811";
const OUT = process.argv[3] || "D:/moodle/_qoder_ai_ord0387_20260928/ord0430_readings";
const ARM = process.argv[4] || "before";

const ENTRY = ["使用封存的演示行程", "Use the sealed demo journey", "sealed demo", "封存演示"];
const SCREENS = ["twin", "discover", "intelligence"];

const PROBE = () => {
  const READABLE = "h1,h2,h3,h4,h5,p,li,dt,dd,th,td,label,figcaption,summary";
  const ACTIONABLE = 'button, a[href], input, select, textarea, [role="button"]';
  const pill = document.querySelector('[data-testid="v18-copilot-dock"]');
  const out = { path: location.pathname, pill_present: !!pill, rests: [] };
  out.horizontal_overflow = {
    scrollWidth: document.documentElement.scrollWidth,
    clientWidth: document.documentElement.clientWidth,
    overflow_gt: document.documentElement.scrollWidth > document.documentElement.clientWidth,
  };
  if (!pill) return out;

  out.pill_attrs = {
    yield_to_surface: pill.getAttribute("data-yield-to-surface"),
    rest_overlap: pill.getAttribute("data-rest-overlap"),
    idle_compact: pill.getAttribute("data-idle-compact"),
  };

  const boxes = () => {
    const pr = pill.getBoundingClientRect();
    return {
      band: {
        left: pill.offsetLeft, top: pill.offsetTop,
        right: pill.offsetLeft + pill.offsetWidth, bottom: pill.offsetTop + pill.offsetHeight,
      },
      painted: { left: pr.left, top: pr.top, right: pr.right, bottom: pr.bottom },
    };
  };

  const collect = (sel, cls, band, painted) => {
    const hits = [];
    document.querySelectorAll(sel).forEach((el) => {
      if (pill.contains(el) || el.contains(pill)) return;
      const t = (el.textContent || "").replace(/\s+/g, " ").trim();
      if (!t) return;
      const r = el.getBoundingClientRect();
      if (!(r.width > 0 && r.height > 0)) return;
      const ow = Math.min(r.right, band.right) - Math.max(r.left, band.left);
      const oh = Math.min(r.bottom, band.bottom) - Math.max(r.top, band.top);
      if (!(ow > 1 && oh > 1)) return;
      const pw = Math.min(r.right, painted.right) - Math.max(r.left, painted.left);
      const ph = Math.min(r.bottom, painted.bottom) - Math.max(r.top, painted.top);
      hits.push({
        kind: cls,
        tag: el.tagName,
        text: t.slice(0, 90),
        band_overlap_px: Math.round(ow * oh),
        painted_overlap_px: pw > 1 && ph > 1 ? Math.round(pw * ph) : 0,
        el_y: Math.round(r.top),
      });
    });
    return hits;
  };

  const first = boxes();
  out.pill_band_px = { w: Math.round(first.band.right - first.band.left), h: Math.round(first.band.bottom - first.band.top) };
  out.pill_painted_px = { w: Math.round(first.painted.right - first.painted.left), h: Math.round(first.painted.bottom - first.painted.top) };

  const scrollables = [document.scrollingElement || document.documentElement];
  document.querySelectorAll("*").forEach((e) => {
    if (e.scrollHeight > e.clientHeight + 8 && e.clientHeight > 120) scrollables.push(e);
  });
  scrollables.forEach((el) => {
    const max = Math.max(0, el.scrollHeight - el.clientHeight);
    const stepBy = Math.max(120, Math.floor(el.clientHeight * 0.5));
    for (let y = 0; ; y += stepBy) {
      el.scrollTop = Math.min(y, max);
      const b = boxes();
      const cw = b.painted.right - b.painted.left;
      const cx = Math.round(b.painted.left + cw / 2);
      const cy = Math.round(b.painted.bottom - 8);
      const at = document.elementFromPoint(cx, cy);
      const readable = collect(READABLE, "readable", b.band, b.painted);
      const actionable = collect(ACTIONABLE, "actionable", b.band, b.painted);
      const covered = readable.filter((h) => h.painted_overlap_px > 0);
      out.rests.push({
        scroller: el.tagName + "." + String(el.className || "").slice(0, 20),
        scrollTop: Math.round(el.scrollTop),
        pill_hit_test: at ? at.tagName + "." + String(at.className || "").slice(0, 18) : "none",
        pill_hit_inside: !!(at && pill.contains(at)),
        readable_covered: covered.length,
        actionable_overlap: actionable.length,
        max_painted_overlap_px: covered.reduce((a, h) => Math.max(a, h.painted_overlap_px), 0),
        max_band_overlap_px: readable.reduce((a, h) => Math.max(a, h.band_overlap_px), 0),
        first_covered_text: covered.length ? covered[0].text : null,
        first_covered_tag: covered.length ? covered[0].tag : null,
        items: readable.concat(actionable).slice(0, 12),
      });
      if (y >= max) break;
    }
    el.scrollTop = 0;
  });
  return out;
};

(async () => {
  fs.mkdirSync(OUT, { recursive: true });
  const browser = await chromium.launch();
  const rep = { base: BASE, arm: ARM, screens: [] };
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
        if (await loc.count()) {
          await loc.click({ timeout: 8000 }).catch(() => {});
          await page.waitForTimeout(2000);
          break;
        }
      }
      await page.goto(BASE + "/v8/" + screen, { waitUntil: "domcontentloaded", timeout: 60000 }).catch(() => {});
      await page.waitForTimeout(2600);
      const probe = await page.evaluate(PROBE);
      const pill = page.locator('[data-testid="v18-copilot-dock"]');
      const bb = await pill.boundingBox().catch(() => null);
      if (bb) {
        await page.mouse.click(bb.x + bb.width / 2, bb.y + bb.height - 10);
        await page.waitForTimeout(1200);
      }
      probe.reachability = {
        had_box: !!bb,
        panel_opened: (await page.locator(".cn-copilot-panel").count()) > 0,
      };
      r.locales[locale] = probe;
    }
    rep.screens.push(r);
    await ctx.close();
  }
  const file = OUT + "/pill_readme_collision_" + ARM + ".json";
  fs.writeFileSync(file, JSON.stringify(rep, null, 1), "utf8");
  for (const s of rep.screens) {
    for (const loc of Object.keys(s.locales)) {
      const p = s.locales[loc];
      const rests = p.rests || [];
      const covered = rests.filter((x) => x.readable_covered > 0);
      console.log(`${s.screen}/${loc}: present=${p.pill_present} band=${JSON.stringify(p.pill_band_px)}` +
        ` h_overflow=${p.horizontal_overflow && p.horizontal_overflow.overflow_gt}` +
        ` rests=${rests.length} rests_covering_text=${covered.length}` +
        ` max_painted=${rests.reduce((a, x) => Math.max(a, x.max_painted_overlap_px), 0)}` +
        ` max_band=${rests.reduce((a, x) => Math.max(a, x.max_band_overlap_px), 0)}` +
        ` opened=${p.reachability && p.reachability.panel_opened}`);
      if (covered.length) {
        console.log(`    covered text sample: [${covered[0].first_covered_tag}] "${covered[0].first_covered_text}` +
          `" at scrollTop=${covered[0].scrollTop} painted_overlap_px=${covered[0].max_painted_overlap_px}`);
      }
    }
  }
  console.log("WROTE " + file);
  await browser.close();
})();
