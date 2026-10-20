/* Building walk, cell nine: the map's tappable things -- are they reachable, and do they answer?

The 17-screen census keeps reporting three families under the touch floor on the map: the stop labels
(v8-map-stop-label, 22 tall), the numbered pins ("1".."6", 34), and 回到行程视野 (map-viewport-reset, 36).
Before touching CSS, the fact needed is what those controls are made of and what a tap does:

  * painted box and pressable box (grid-sampled elementFromPoint, same rule as the avatar hand),
  * the tag/class actually under a centre tap -- a map label may be a div the app never listens to, in which
    case "make it 44 tall" would fix a number and leave the traveller with the same dead tap,
  * whether a tap changes anything observable: the re-centre button moves the map, and a stop selection
    should change the selected stop somewhere on screen.

The map canvas is WebGL and answers with 0x0 until a frame has been painted, so this tool waits for the
canvas to have a box first -- reading "not reachable" off a canvas that has not drawn yet is how a walk
invents defects.

argv: node walk_map_targets_r1.cjs <base> <out.json> <shot.png>
 */
const { chromium } = require("D:/moodle/_qoder_phone_ord0485_20260930/recut_avatar/frontend/node_modules/playwright");
const fs = require("fs");
const path = require("path");

const BASE = process.argv[2] || "http://127.0.0.1:4895";
const OUT = process.argv[3] || "D:/moodle/_qoder_phone_ord0485_20260930/evidence/map_targets.json";
const SHOT = process.argv[4] || "D:/moodle/_qoder_phone_ord0485_20260930/evidence/map_targets.png";

const run = { schema: "CNX_BUILDING_MAP_TARGETS_R1", base: BASE, viewport: { width: 390, height: 844 },
  started: new Date().toString(), steps: [], targets: [], effects: [], page_errors: [], console_errors: [] };

async function pressTestId(page, testid, tag) {
  const loc = page.locator("[data-testid='" + testid + "']").first();
  if (await loc.count() === 0) return { tag, pressed: false, why: "NO_SUCH_TESTID" };
  const hit = await loc.evaluate((el) => {
    el.scrollIntoViewIfNeeded();
    const b = el.getBoundingClientRect();
    const top = document.elementFromPoint(b.left + b.width / 2, b.top + b.height / 2);
    return { w: Math.round(b.width), h: Math.round(b.height),
             landed: !!top && (top === el || el.contains(top) || (top.contains && top.contains(el))),
             disabled: !!el.disabled };
  });
  if (!hit.landed) return { tag, pressed: false, why: "HIT_TEST_MISSED", hit };
  await loc.click();
  await page.waitForTimeout(1500);
  return { tag, pressed: true, hit };
}

const MEASURE = () => {
  const strip = (x) => String(x || "").replace(/\s+/g, " ").trim();
  const probe = (el) => {
    const b = el.getBoundingClientRect();
    const cx = b.left + b.width / 2, cy = b.top + b.height / 2;
    let minx = cx, maxx = cx, miny = cy, maxy = cy, n = 0;
    for (let dx = -30; dx <= 30; dx += 4) for (let dy = -30; dy <= 30; dy += 4) {
      const t = document.elementFromPoint(cx + dx, cy + dy);
      if (t && (t === el || el.contains(t))) { n++;
        minx = Math.min(minx, cx + dx); maxx = Math.max(maxx, cx + dx);
        miny = Math.min(miny, cy + dy); maxy = Math.max(maxy, cy + dy); }
    }
    const s = getComputedStyle(el);
    return { words: strip(el.innerText || el.getAttribute("aria-label")).slice(0, 40),
             tag: el.tagName, cls: el.className ? String(el.className).slice(0, 60) : null,
             painted: [Math.round(b.width), Math.round(b.height)],
             pressable: [Math.round(maxx - minx + 4), Math.round(maxy - miny + 4)],
             samples: n, cursor: s.cursor, pointer_events: s.pointerEvents,
             position: s.position, min_h: s.minHeight };
  };
  const out = [];
  document.querySelectorAll("[data-testid]").forEach((el) => {
    const id = el.getAttribute("data-testid");
    if (!/^(v8-map-stop-label|map-viewport-reset|v8-maplibre-canvas|map-stop-marker-.*|v8-map-stop-pin.*)$/.test(id)) return;
    const b = el.getBoundingClientRect();
    if (b.width <= 0 || b.height <= 0) return;
    out.push({ testid: id, ...probe(el) });
  });
  // the numbered pins carry no testid, so find them by structure inside the strip
  document.querySelectorAll(".v12-strip button, .v8-strip-item button, [class*='strip'] button").forEach((el) => {
    const b = el.getBoundingClientRect();
    if (b.width <= 0 || b.height <= 0) return;
    out.push({ testid: el.getAttribute("data-testid") || "strip-pin:" + strip(el.innerText).slice(0, 3),
               ...probe(el) });
  });
  return out;
};

async function mapState(page) {
  return page.evaluate(() => {
    const strip = (x) => String(x || "").replace(/\s+/g, " ").trim();
    const canvas = document.querySelector("[data-testid='v8-maplibre-canvas'] canvas")
      || document.querySelector("canvas");
    const b = canvas ? canvas.getBoundingClientRect() : null;
    const selected = Array.from(document.querySelectorAll("[class*='selected'],[aria-current],[aria-pressed='true']"))
      .filter((e) => e.getBoundingClientRect().height > 0)
      .map((e) => (e.getAttribute("data-testid") || e.tagName) + ":" + strip(e.innerText).slice(0, 26)).slice(0, 8);
    return { canvas_box: b ? [Math.round(b.width), Math.round(b.height)] : null,
             canvas_transform: canvas ? getComputedStyle(canvas.parentElement || canvas).transform.slice(0, 80) : null,
             selected, path: location.pathname,
             body_head: strip(document.body.innerText).slice(0, 260) };
  });
}

(async () => {
  const browser = await chromium.launch();
  const ctx = await browser.newContext({ viewport: { width: 390, height: 844 }, deviceScaleFactor: 2,
    isMobile: true, hasTouch: true, serviceWorkers: "block" });
  const page = await ctx.newPage();
  page.on("pageerror", (e) => run.page_errors.push(String(e).slice(0, 200)));
  page.on("console", (m) => { if (m.type() === "error") run.console_errors.push(m.text().slice(0, 200)); });

  await page.goto(BASE + "/", { waitUntil: "networkidle", timeout: 60000 });
  await page.waitForTimeout(1200);
  run.steps.push(await pressTestId(page, "trial-tianjin-demo", "anchor_demo"));
  await page.waitForTimeout(1500);
  run.steps.push(await pressTestId(page, "v8-mobile-menu", "open_drawer"));
  run.steps.push(await pressTestId(page, "v8-drawer-entry-map", "enter_map"));
  // wait for the canvas to have a box before judging anything as unreachable
  let waited = 0;
  while (waited < 20) {
    const st = await mapState(page);
    if (st.canvas_box && st.canvas_box[0] > 10 && st.canvas_box[1] > 10) break;
    await page.waitForTimeout(1000);
    waited++;
  }
  run.canvas_wait_seconds = waited;
  const before = await mapState(page);
  run.map_before = before;
  run.targets = await page.evaluate(MEASURE);

  fs.mkdirSync(path.dirname(SHOT), { recursive: true });
  await page.screenshot({ path: SHOT, fullPage: true });
  run.shot = SHOT;

  for (const cand of ["map-viewport-reset", "v8-map-stop-label"]) {
    const loc = page.locator("[data-testid='" + cand + "']").first();
    if (await loc.count() === 0) { run.effects.push({ testid: cand, pressed: false, why: "ABSENT" }); continue; }
    const st0 = await mapState(page);
    const p = await pressTestId(page, cand, "tap_" + cand);
    const st1 = await mapState(page);
    run.effects.push({ testid: cand, press: p,
      transform_changed: st0.canvas_transform !== st1.canvas_transform,
      selected_changed: JSON.stringify(st0.selected) !== JSON.stringify(st1.selected),
      before_selected: st0.selected, after_selected: st1.selected });
  }

  const under = run.targets.filter((t) => t.pressable[0] < 44 || t.pressable[1] < 44);
  run.summary = {
    targets_found: run.targets.length,
    under_floor_by_pressable: under.length,
    non_button_targets: run.targets.filter((t) => t.tag !== "BUTTON" && t.tag !== "A").map((t) => t.testid + "/" + t.tag),
    cursor_pointer_absent: run.targets.filter((t) => t.cursor !== "pointer").map((t) => t.testid + ":" + t.cursor),
    canvas_box: before.canvas_box,
    taps_that_changed_something: run.effects.filter((e) => e.transform_changed || e.selected_changed).length };
  run.finished = new Date().toString();
  fs.writeFileSync(OUT, JSON.stringify(run, null, 1));
  console.log(JSON.stringify({ canvas_wait_seconds: waited, canvas_box: before.canvas_box,
    summary: run.summary,
    targets: run.targets.map((t) => ({ id: t.testid, tag: t.tag, painted: t.painted, pressable: t.pressable,
      cursor: t.cursor, pe: t.pointer_events, words: t.words })),
    effects: run.effects.map((e) => ({ id: e.testid, pressed: e.press && e.press.pressed,
      transform_changed: e.transform_changed, selected_changed: e.selected_changed, why: e.why || null })),
    page_errors: run.page_errors.length, console_errors: run.console_errors.length }, null, 1));
  await browser.close();
})();
