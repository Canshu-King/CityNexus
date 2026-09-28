/* ORD-0417 lane geometry census r2 -- one evidence file PER ARM, and wrapping proven the only way
 * that proves it: `Range.getClientRects()`.
 *
 * r1 wrote a single receipt per build with both arms inside it and reported only bounding boxes.  Two
 * standing rules make that wrong here:
 *   - one evidence file per arm, so an arm cannot borrow another arm's witness;
 *   - a wrapped line is only observable as multiple client rects; `getBoundingClientRect()` on the
 *     element collapses to the union and cannot tell "one line" from "two lines of the same height".
 * So r2 takes `--arm zh|en`, writes `<label>_<arm>.census.json`, and for the cell this order adds
 * records both `box` and every client rect of a `Range` over its contents, plus the line count implied
 * by them.  The frozen 口径 for reachability is unchanged from r1 (lane N3's: the control set, the
 * 768 px line, `elementFromPoint` at the control's own centre, identity by testid else name+nth),
 * copied from `frontend/e2e/qoder-ord0407-empty-state-actions.spec.ts` rather than re-invented.
 *
 * usage: node ord0417_geometry_census_r2.js <base> <out-dir> <label> <zh|en>
 */
const { chromium } = require("D:/moodle/CityNexus/frontend/node_modules/playwright");
const fs = require("fs");

const BASE = (process.argv[2] || "http://127.0.0.1:4843/").replace(/\/$/, "");
const OUT = process.argv[3] || ".";
const LABEL = process.argv[4] || "unlabelled";
const ARM = (process.argv[5] || "zh").toLowerCase();
const LOCALE = ARM === "zh" ? "zh-CN" : "en";
const FLOOR = 768;
const SHAPES = [[390, 844], [360, 800], [320, 653], [414, 896]];

const READ = (floor) => {
  const rectOf = (el) => { const r = el.getBoundingClientRect();
    return [Math.round(r.x), Math.round(r.y), Math.round(r.width), Math.round(r.height)]; };
  const clientRects = (el) => {
    const range = document.createRange();
    range.selectNodeContents(el);
    return Array.from(range.getClientRects())
      .filter((r) => r.width > 0 && r.height > 0)
      .map((r) => [Math.round(r.x), Math.round(r.y), Math.round(r.width), Math.round(r.height)]);
  };
  const sel = "button, a[href], input, select, textarea, [role=button], [data-testid=pretrip-empty-action]";
  const seen = {};
  const controls = Array.from(document.querySelectorAll(sel)).map((el) => {
    const r = el.getBoundingClientRect();
    if (r.width === 0 || r.height === 0) return null;
    const cx = Math.round(r.left + r.width / 2), cy = Math.round(r.top + r.height / 2);
    const hit = document.elementFromPoint(cx, cy);
    const text = (el.textContent ?? "").replace(/\s+/g, " ").trim().slice(0, 60);
    const testid = el.getAttribute("data-testid");
    const name = text || el.getAttribute("aria-label") || el.getAttribute("placeholder") || "(no label)";
    const bare = testid ?? name;
    seen[bare] = (seen[bare] ?? 0) + 1;
    return { key: testid ?? `${name}#${seen[bare]}`, centre: [cx, cy],
             in_viewport: cy >= 0 && cy <= window.innerHeight, above_floor: cy <= floor,
             hit_test: !!hit && (hit === el || el.contains(hit) || hit.contains(el)) };
  }).filter((x) => x !== null);

  const band = document.querySelector(".v8-map-overlay-stack");
  const cell = document.querySelector(".v8-map-panel .v8-map-selected-stop");
  const cap = document.querySelector(".v8-map-caption");
  const bb = band && band.getBoundingClientRect();
  const pins = Array.from(document.querySelectorAll(".v8-map-panel .v9-map-marker"))
    .filter((el) => el.getAttribute("role") === "button")
    .map((el) => {
      const r = el.getBoundingClientRect();
      const cx = Math.round(r.x + r.width / 2), cy = Math.round(r.y + r.height / 2);
      const top = document.elementFromPoint(cx, cy);
      const ov = bb ? Math.max(0, Math.min(bb.right, r.right) - Math.max(bb.left, r.left))
                        * Math.max(0, Math.min(bb.bottom, r.bottom) - Math.max(bb.top, r.top)) : 0;
      return { painted: (el.textContent ?? "").trim(), aria: el.getAttribute("aria-label") ?? "",
               title_attr: el.getAttribute("title"), centre: [cx, cy],
               lands: !!top && (top === el || el.contains(top)), covered_px2: Math.round(ov) };
    });
  return {
    lang: document.documentElement.lang || null, scroll_y: Math.round(window.scrollY),
    inner: [window.innerWidth, window.innerHeight], controls, pins,
    band_box: bb ? [Math.round(bb.x), Math.round(bb.y), Math.round(bb.width), Math.round(bb.height)] : null,
    caption_box: cap ? rectOf(cap) : null,
    cell: cell ? { box: rectOf(cell), client_rects: clientRects(cell),
                   text: (cell.innerText ?? "").replace(/\s+/g, " ").trim(),
                   line_count: clientRects(cell).length } : null,
  };
};

const reachable = (r) => r.controls.filter((c) => c.hit_test && c.above_floor && c.in_viewport).map((c) => c.key);

async function shape(browser, w, h) {
  const page = await browser.newPage({ viewport: { width: w, height: h } });
  const errors = [];
  page.on("pageerror", (e) => errors.push(String(e).slice(0, 180)));
  const rec = { label: LABEL, arm: ARM, locale_stored: LOCALE, shape: `${w}x${h}`,
                shape_wh_px: [w, h], hit_floor_px: FLOOR, base: BASE, errors };
  try {
    await page.goto(BASE + "/v8/map", { waitUntil: "networkidle", timeout: 60000 });
    const seal = page.getByText("使用封存的演示行程", { exact: false }).first();
    if (await seal.count()) { await seal.click(); await page.waitForTimeout(6000); }
    await page.evaluate((l) => localStorage.setItem("citynexus.locale", l), LOCALE);
    await page.reload({ waitUntil: "networkidle" });
    const seal2 = page.getByText("使用封存的演示行程", { exact: false }).first();
    if (await seal2.count()) { await seal2.click(); await page.waitForTimeout(6000); }
    await page.waitForTimeout(1200);

    const idle = await page.evaluate(READ, FLOOR);
    rec.idle = idle;
    rec.entry = { reached_path: (await page.evaluate(() => location.pathname)),
                  lang_read: idle.lang, pins: idle.pins.length };
    const hittable = idle.pins.filter((p) => p.lands && p.aria);
    rec.pins_individually_hittable = hittable.length;
    if (!hittable.length) { rec.fatal = "ENTRY_OR_PIN_FAILURE: no pin answers a hit at its own centre"; await page.close(); return rec; }
    const t = hittable[Math.min(1, hittable.length - 1)];
    rec.tapped = { painted: t.painted, aria: t.aria, centre: t.centre };
    await page.mouse.click(t.centre[0], t.centre[1]);
    await page.waitForTimeout(2200);
    await page.evaluate(() => window.scrollTo(0, 0));
    await page.waitForTimeout(900);
    const live = await page.evaluate(READ, FLOOR);
    rec.live = live;

    const before = reachable(idle), after = new Set(reachable(live));
    const idleLands = new Set(idle.pins.filter((p) => p.lands).map((p) => p.painted));
    const idleCovered = new Map(idle.pins.map((p) => [p.painted, p.covered_px2]));
    rec.reachable_idle = before.length;
    rec.reachable_with_selection = after.size;
    rec.lost_reachable = before.filter((k) => !after.has(k));
    rec.controls_idle = idle.controls.length;
    rec.controls_with_selection = live.controls.length;
    rec.band_height_idle_px = idle.band_box ? idle.band_box[3] : null;
    rec.band_height_with_selection_px = live.band_box ? live.band_box[3] : null;
    rec.band_growth_px = (idle.band_box && live.band_box) ? live.band_box[3] - idle.band_box[3] : null;
    rec.cell_box_px = live.cell ? live.cell.box : null;
    rec.cell_client_rects = live.cell ? live.cell.client_rects : null;
    rec.cell_line_count = live.cell ? live.cell.line_count : null;
    rec.caption_height_idle_px = idle.caption_box ? idle.caption_box[3] : null;
    rec.caption_height_with_selection_px = live.caption_box ? live.caption_box[3] : null;
    rec.cell_text = live.cell ? live.cell.text : null;
    rec.name_painted_on_glass = !!(live.cell && t.aria && live.cell.text.includes(t.aria));
    rec.newly_covered_pins = live.pins
      .filter((p) => (idleCovered.get(p.painted) ?? 0) === 0 && p.covered_px2 > 0)
      .map((p) => ({ painted: p.painted, aria: p.aria, px2: p.covered_px2 }));
    rec.newly_unhittable_pins = live.pins
      .filter((p) => idleLands.has(p.painted) && !p.lands).map((p) => ({ painted: p.painted }));
    rec.pins_below_floor = live.pins.filter((p) => p.centre[1] > FLOOR).map((p) => ({ painted: p.painted }));
    await page.screenshot({ path: `${OUT}/${LABEL}_${ARM}_${w}x${h}.png` });
  } catch (e) {
    rec.fatal = String(e).slice(0, 220);
  }
  await page.close();
  return rec;
}

(async () => {
  fs.mkdirSync(OUT, { recursive: true });
  const browser = await chromium.launch({ channel: "chrome", headless: true });
  const results = [];
  for (const [w, h] of SHAPES) results.push(await shape(browser, w, h));
  await browser.close();
  const path = `${OUT}/${LABEL}_${ARM}.census.json`;
  fs.writeFileSync(path, JSON.stringify({ base: BASE, label: LABEL, arm: ARM, locale_stored: LOCALE,
    hit_floor_px: FLOOR, shapes_wh_px: SHAPES, results }, null, 1), "utf-8");
  for (const r of results) {
    console.log(`${LABEL}/${ARM} ${r.shape_wh_px[0]}x${r.shape_wh_px[1]} px entry=${JSON.stringify(r.entry)} grew=${r.band_growth_px}px band ${r.band_height_idle_px}->${r.band_height_with_selection_px}px caption ${r.caption_height_idle_px}->${r.caption_height_with_selection_px}px cell_lines=${r.cell_line_count} cell=${JSON.stringify(r.cell_box_px)} ctl ${r.controls_idle}->${r.controls_with_selection} reach ${r.reachable_idle}->${r.reachable_with_selection} lost=${JSON.stringify(r.lost_reachable)} covered=${JSON.stringify(r.newly_covered_pins)} unhitt=${JSON.stringify(r.newly_unhittable_pins)} below=${JSON.stringify(r.pins_below_floor)} name=${r.name_painted_on_glass} err=${(r.errors||[]).length}${r.fatal ? " FATAL=" + r.fatal : ""}`);
  }
  console.log("wrote", path);
})().catch((e) => { console.log("FATAL", String(e).slice(0, 300)); process.exit(9); });
