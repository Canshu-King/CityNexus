/**
 * ORD-0401 -- price the three placements that could put the actionable empty state in the first
 * screen, so the ruling is a choice between numbers rather than between adjectives.
 *
 * The panel's own anchor is at y=885 and `today-strip` starts at y=771, while the *hittable* region
 * ends at y=768 (fixed `v8-mobile-nav`, measured in first_screen_rect_r1.json). Both roads the order
 * names therefore land the action under the tab bar. That leaves one question with a number in it:
 * what has to give, and by how much?
 *
 * Method: move the live panel node into each candidate slot, reload nothing, and read
 *   - the action's centre and whether `elementFromPoint` at that centre returns the button itself,
 *   - how much of the hero article / map panel ends up below 768 as a result.
 * The node is put back after each arm, and the file records the pre-move geometry so the shipped
 * state is not silently mutated by the instrument.
 */
import { chromium } from "playwright";
import { mkdirSync, writeFileSync } from "node:fs";

const BASE = process.env.ORD0401_BASE ?? "http://127.0.0.1:4301";
const OUT = process.env.ORD0401_OUT ?? "D:/moodle/_qoder_q_ord0401_evidence";
mkdirSync(OUT, { recursive: true });
const WIDTHS = (process.env.ORD0401_WIDTHS ?? "320,390").split(",").map(Number);

const ARM = ([slot, copy]) => {
  const navTop = (() => {
    const nav = document.querySelector('[data-testid="nav-hub"]')?.closest("nav");
    return nav ? Math.round(nav.getBoundingClientRect().top) : null;
  })();
  const panel = document.querySelector('[data-testid="pretrip-checklist"]');
  const hero = document.querySelector(".v8-hero-grid > article");
  const map = document.querySelector(".v8-map-panel");
  const intro = document.querySelector(".v8-page-intro");
  const strip = document.querySelector('[data-testid="today-strip"]');
  const band = document.querySelector('[data-testid="today-attention-band"]');
  const box = (el) => (el ? { y: Math.round(el.getBoundingClientRect().top + window.scrollY), h: Math.round(el.getBoundingClientRect().height), bottom: Math.round(el.getBoundingClientRect().bottom + window.scrollY) } : null);
  const pre = { panel: box(panel), hero: box(hero), map: box(map), intro: box(intro), strip: box(strip), band: box(band), nav_top: navTop };

  const originalNext = panel.nextSibling;
  const originalParent = panel.parentNode;
  const targets = {
    "P1_above_intro": () => [originalParent, intro],
    "P2_between_hero_and_map": () => [map.parentNode, map],
    "P3_before_today_strip": () => [strip.parentNode, strip],
    "P5_before_today_strip_map_empty_shortened": () => [strip.parentNode, strip],
    "P4_shipped_anchor": () => [originalParent, panel],
  };
  const [parent, ref] = targets[slot]();
  /* P5 is a *hypothetical priced in the browser*, not a shipped change: MapPanel's empty state is
     another lane's element, so it is shortened here only to answer "what would road ② need?". The
     override is applied to the live node and the arm records how tall the map block was before. */
  const mapEmptyBefore = map ? Math.round(map.getBoundingClientRect().height) : null;
  if (slot.startsWith("P5") && map) {
    map.style.padding = "8px 12px";
    map.querySelectorAll("p,small").forEach((el) => el.remove());
  }
  parent.insertBefore(panel, ref);

  const btn = document.querySelector('[data-testid="pretrip-empty-action"]');
  const r = btn?.getBoundingClientRect();
  const centre = r ? { cx: Math.round(r.x + r.width / 2), cy: Math.round(r.y + r.height / 2) } : null;
  const topEl = centre ? document.elementFromPoint(centre.cx, centre.cy) : null;
  const out = {
    slot,
    before_move: pre,
    nav_top: navTop,
    usable_first_screen_bottom: navTop,
    panel: box(panel),
    action: box(btn),
    action_centre: centre,
    hittable_at_scroll_0: !!topEl && topEl === btn,
    what_is_at_the_centre: topEl
      ? `${topEl.tagName.toLowerCase()}:${(topEl.getAttribute("data-testid") || (typeof topEl.className === "string" ? topEl.className.split(" ")[0] : "")).slice(0, 30)}`
      : "null(outside viewport)",
    map_empty_height_before: mapEmptyBefore,
    map_after: box(map),
    hero_after: box(hero),
    map_after: box(map),
    intro_after: box(intro),
    band_after: box(band),
    band_y_before: pre.band?.y,
    hero_behind_nav_px: hero ? Math.max(0, Math.round(hero.getBoundingClientRect().bottom) - navTop) : null,
    map_behind_nav_px: map ? Math.max(0, Math.round(map.getBoundingClientRect().bottom) - navTop) : null,
    panel_rendered_text: (panel.innerText || "").replace(/\s+/g, " ").trim().slice(0, copy),
  };
  /* Put it back exactly as the app mounted it. */
  originalParent.insertBefore(panel, originalNext);
  return out;
};

const browser = await chromium.launch();
const report = { base: BASE, widths: WIDTHS, arms: [] };
for (const width of WIDTHS) {
  for (const locale of ["zh-CN", "en"]) {
    const ctx = await browser.newContext({ viewport: { width, height: 844 } });
    const page = await ctx.newPage();
    await page.addInitScript((v) => localStorage.setItem("citynexus.locale", v), locale);
    await page.route((url) => url.pathname.startsWith("/api/"), (r) =>
      r.request().method() === "GET" ? r.continue() : r.fulfill({ status: 405, body: "{}" }),
    );
    await page.goto(`${BASE}/v8`, { waitUntil: "load" });
    await page.waitForTimeout(1200);
    const demo = page.getByTestId("trial-tianjin-demo");
    if (await demo.count()) {
      await demo.click();
      await page.waitForFunction(() => !!localStorage.getItem("citynexus.v8.journey_id"), null, { timeout: 30_000 }).catch(() => {});
    }
    await page.goto(`${BASE}/v8/hub`, { waitUntil: "load" });
    await page.waitForTimeout(2200);
    /* One fresh document per slot: a node move changes the margin collapse between the band and the
       panel by 10 px, which is measurement bias, not a property of the placement. Each arm therefore
       reloads the screen before moving anything, and the arm records the pre-move geometry it found. */
    const results = [];
    for (const slot of ["P4_shipped_anchor", "P1_above_intro", "P2_between_hero_and_map", "P3_before_today_strip", "P5_before_today_strip_map_empty_shortened"]) {
      await page.goto(`${BASE}/v8/hub`, { waitUntil: "load" });
      await page.waitForTimeout(1800);
      results.push(await page.evaluate(ARM, [slot, 90]));
    }
    report.arms.push({ width, locale, results });
    console.log(`\n=== ${locale} @ ${width}x844 (nav top ${results[0].nav_top}) ===`);
    for (const r of results) {
      console.log(
        `  ${r.slot.padEnd(24)} panel_y=${String(r.panel.y).padStart(4)} h=${String(r.panel.h).padStart(3)} action_ctr=${String(r.action_centre?.cy).padStart(4)} hittable=${String(r.hit?.[1] ?? r.hittable_at_scroll_0).padEnd(5)} at_centre=${r.what_is_at_the_centre.padEnd(26)} hero_behind=${String(r.hero_behind_nav_px).padStart(4)} map_behind=${String(r.map_behind_nav_px).padStart(4)} band_y=${r.band_after?.y}`,
      );
    }
    await ctx.close();
  }
}
await browser.close();
writeFileSync(`${OUT}/placement_options_r1.json`, JSON.stringify(report, null, 2));
console.log("\nrows:", report.arms.reduce((n, a) => n + a.results.length, 0));
