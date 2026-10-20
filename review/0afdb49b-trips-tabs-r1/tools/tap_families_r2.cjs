/* Building walk, cell ten step two: the room around the two families, and whether a press answers.
 *
 * r1 named them: `button.cn-copilot-edge` paints 165x42 and declares min-height:42px; the trips tabs are
 * `button[role=tab][data-testid^=trips-tab-]` painting 356x40 with min-height:40px. Both are real controls
 * that answer to a centre hit-test, so the only question left before choosing a fix shape is what sits
 * around them: an outward hit box that lands on top of the bottom nav (or on the neighbouring tab) would
 * trade "2px too small" for "presses the wrong thing". r1's press-effect check never ran because it looked
 * for the opener on the hub, and the opener lives on the map screen -- fixed here.
 * argv: node tap_families_r2.cjs <base> <out.json>
 */
const { chromium } = require("D:/moodle/_qoder_phone_ord0485_20260930/recut_avatar/frontend/node_modules/playwright");
const fs = require("fs");
const BASE = process.argv[2] || "http://127.0.0.1:4895";
const OUT = process.argv[3] || "D:/moodle/_qoder_phone_ord0485_20260930/evidence/tap_families_r2.json";
const run = { schema: "CNX_TAP_FAMILIES_R2", base: BASE, started: new Date().toString(), screens: [], taps: [], errors: [] };

const ROOM = () => {
  const box = (el) => { const b = el.getBoundingClientRect();
    return { top: Math.round(b.top), bottom: Math.round(b.bottom), left: Math.round(b.left),
             right: Math.round(b.right), w: Math.round(b.width), h: Math.round(b.height) }; };
  const edge = document.querySelector("button.cn-copilot-edge");
  const nav = document.querySelector(".v8-mobile-nav");
  const tabs = Array.from(document.querySelectorAll("[data-testid^='trips-tab-']"));
  const out = { edge: null, nav: null, tabs: [], tab_gaps: [] };
  if (edge) {
    out.edge = box(edge);
    out.edge_min_h = getComputedStyle(edge).minHeight;
    const eb = edge.getBoundingClientRect();
    // what would an outward hit box of +/- 2 and +/- 5 px run into?
    out.edge_above = (document.elementFromPoint(eb.left + eb.width / 2, eb.top - 3) || {}).tagName || null;
    out.edge_below = (document.elementFromPoint(eb.left + eb.width / 2, eb.bottom + 3) || {}).tagName || null;
    const nb = nav ? nav.getBoundingClientRect() : null;
    out.gap_edge_to_nav = nb ? Math.round(nb.top - eb.bottom) : null;
  }
  if (nav) out.nav = box(nav);
  tabs.forEach((t, i) => {
    const b = box(t);
    out.tabs.push({ testid: t.getAttribute("data-testid"), words: (t.innerText || "").trim().slice(0, 10),
      min_h: getComputedStyle(t).minHeight, ...b, pe: getComputedStyle(t).pointerEvents });
    if (i > 0) out.tab_gaps.push(b.top - out.tabs[i - 1].bottom);
  });
  return out;
};

(async () => {
  const browser = await chromium.launch();
  const ctx = await browser.newContext({ viewport: { width: 390, height: 844 }, deviceScaleFactor: 2,
    isMobile: true, hasTouch: true, serviceWorkers: "block" });
  const page = await ctx.newPage();
  page.on("pageerror", (e) => run.errors.push(String(e).slice(0, 160)));
  await page.goto(BASE + "/", { waitUntil: "networkidle", timeout: 60000 });
  await page.waitForTimeout(1200);
  const a = page.locator("[data-testid='trial-tianjin-demo']").first();
  if (await a.count()) { await a.evaluate(e => e.scrollIntoViewIfNeeded()); await a.click(); }
  await page.waitForTimeout(1600);

  async function drawer(entry) {
    const m = page.locator("[data-testid='v8-mobile-menu']").first();
    await m.evaluate(e => e.scrollIntoViewIfNeeded()); await m.click(); await page.waitForTimeout(900);
    const e2 = page.locator("[data-testid='v8-drawer-entry-" + entry + "']").first();
    await e2.evaluate(e => e.scrollIntoViewIfNeeded()); await e2.click(); await page.waitForTimeout(2000);
  }

  // map screen: the Copilot edge button, its room, and what a press changes
  await drawer("map");
  const roomMap = await page.evaluate(ROOM);
  const chars0 = await page.evaluate(() => document.body.innerText.replace(/\s+/g, " ").length);
  const pressedEdge = await page.evaluate(() => {
    const el = document.querySelector("button.cn-copilot-edge");
    if (!el) return false;
    const b = el.getBoundingClientRect();
    const top = document.elementFromPoint(b.left + b.width / 2, b.top + b.height / 2);
    return !!top && (top === el || el.contains(top));
  });
  if (roomMap.edge) { await page.locator("button.cn-copilot-edge").first().click(); await page.waitForTimeout(2200); }
  const afterEdge = await page.evaluate(() => ({
    chars: document.body.innerText.replace(/\s+/g, " ").length,
    composer: !!document.querySelector("[data-testid*='composer' i],[data-testid*='agent' i],[class*='copilot' i]"),
    words: document.body.innerText.replace(/\s+/g, " ").slice(0, 160) }));
  run.screens.push({ screen: "map", room: roomMap, centre_pressable: pressedEdge,
    chars_before: chars0, chars_after: afterEdge.chars, dock_present_after: afterEdge.composer });

  // trips screen: the tab strip, its row gaps, and a press that must swap the list
  await page.goto(BASE + "/", { waitUntil: "networkidle", timeout: 60000 });
  await page.waitForTimeout(1200);
  if (await a.count()) { await a.evaluate(e => e.scrollIntoViewIfNeeded()); await a.click(); }
  await page.waitForTimeout(1500);
  const navTrips = page.locator("[data-testid='nav-trips']").first();
  if (await navTrips.count()) { await navTrips.evaluate(e => e.scrollIntoViewIfNeeded()); await navTrips.click(); }
  await page.waitForTimeout(2000);
  const roomTrips = await page.evaluate(ROOM);
  const tabSel = "[data-testid='trips-tab-spend']";
  const hasTab = await page.locator(tabSel).count();
  let tabTap = { attempted: false };
  if (hasTab) {
    const before = await page.evaluate(() => document.body.innerText.replace(/\s+/g, " ").length);
    await page.locator(tabSel).first().click();
    await page.waitForTimeout(1800);
    tabTap = { attempted: true, selected_before: null,
      selected_after: await page.evaluate((s) => { const el = document.querySelector(s);
        return el ? el.getAttribute("aria-selected") || el.getAttribute("aria-pressed") || el.className : null; }, tabSel),
      chars_before: before,
      chars_after: await page.evaluate(() => document.body.innerText.replace(/\s+/g, " ").length) };
  }
  run.screens.push({ screen: "trips", room: roomTrips, tab_tap: tabTap });

  fs.writeFileSync(OUT, JSON.stringify(run, null, 1));
  console.log(JSON.stringify({ map: { edge: run.screens[0].room.edge, gap_edge_to_nav: run.screens[0].room.gap_edge_to_nav,
      centre_pressable: run.screens[0].centre_pressable, chars_before: run.screens[0].chars_before,
      chars_after: run.screens[0].chars_after, dock_after: run.screens[0].dock_present_after,
      above: run.screens[0].room.edge_above, below: run.screens[0].room.edge_below },
    trips: { tabs: run.screens[1].room.tabs.map(t => ({ id: t.testid, h: t.h, min_h: t.min_h, top: t.top })),
      tab_gaps: run.screens[1].room.tab_gaps, tab_tap: run.screens[1].tab_tap,
      edge_on_trips: run.screens[1].room.edge },
    errors: run.errors.length }, null, 1));
  await browser.close();
})();
