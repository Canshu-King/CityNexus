/* ORD-0417 lane probe r1 - what does a tap on a v8 map marker change, ANYWHERE on the screen?
   The commander's instrument reads only .v8-map-caption and .v8-map-overlay-stack.  This probe reads
   those two plus every other place a stop name could legitimately appear (the ORD-0390 h2 outside
   the panel, the stop rows, the marker's own classes) and the geometry of markers vs the overlay
   stack, so "the name is not shown" and "the name is shown but not inside the map panel" are
   different answers rather than one number.  Nothing here writes. */
const { chromium } = require("D:/moodle/CityNexus/frontend/node_modules/playwright");
const fs = require("fs");
const BASE = process.argv[2] || "http://127.0.0.1:4832/";
const OUT = process.argv[3];
const LOCALE = process.argv[4] || "";
const VPW = parseInt(process.argv[5] || "390", 10);
const VPH = parseInt(process.argv[6] || "844", 10);
const NTH = parseInt(process.argv[7] || "1", 10);

const snap = () => {
  const box = (e) => { const b = e.getBoundingClientRect();
    return [Math.round(b.x), Math.round(b.y), Math.round(b.width), Math.round(b.height)]; };
  const txt = (e) => (e ? (e.textContent || "").replace(/\s+/g, " ").trim() : null);
  const q = (s) => document.querySelector(s);
  const stack = q(".v8-map-overlay-stack");
  const stackBox = stack ? box(stack) : null;
  const markers = Array.from(document.querySelectorAll(".v9-map-marker")).map((e) => ({
    text: (e.textContent || "").trim(), aria: e.getAttribute("aria-label"),
    role: e.getAttribute("role"), title: e.getAttribute("title"),
    pressed: e.getAttribute("aria-pressed"), cls: e.className, box: box(e),
    /* visual occlusion: does the bottom overlay band cover this marker's box? */
    covered_by_overlay_px2: stackBox ? Math.max(0,
      Math.min(stackBox[0] + stackBox[2], e.getBoundingClientRect().right) -
      Math.max(stackBox[0], e.getBoundingClientRect().left)) * Math.max(0,
      Math.min(stackBox[1] + stackBox[3], e.getBoundingClientRect().bottom) -
      Math.max(stackBox[1], e.getBoundingClientRect().top)) : 0,
    /* hit-test at the marker's own centre: does a finger land on the marker? */
    hit_at_centre: (() => { const b = e.getBoundingClientRect();
      const cx = b.x + b.width / 2, cy = b.y + b.height / 2;
      const top = document.elementFromPoint(cx, cy);
      return top ? { tag: top.tagName, cls: top.className || null, is_marker: top === e || e.contains(top) } : null; })(),
  }));
  return {
    viewport: [window.innerWidth, window.innerHeight],
    lang: document.documentElement.lang,
    caption: txt(q(".v8-map-caption")),
    overlay: txt(stack),
    overlay_box: stackBox,
    attribution: (() => { const a = q('[data-testid="v8-map-attribution"]');
      return a ? { text: txt(a), box: box(a) } : null; })(),
    /* the places OUTSIDE the map panel that ORD-0390 already wires */
    h2_map_selected_stop: txt(q('[data-testid="map-selected-stop"]')),
    h2_box: (() => { const e = q('[data-testid="map-selected-stop"]'); return e ? box(e) : null; })(),
    h2_in_viewport: (() => { const e = q('[data-testid="map-selected-stop"]'); if (!e) return null;
      const b = e.getBoundingClientRect();
      return b.top >= 0 && b.bottom <= window.innerHeight; })(),
    selected_type: txt(q('[data-testid="map-selected-type"]')),
    stop_rows_selected: Array.from(document.querySelectorAll(".v8-map-stop.selected")).map((e) => txt(e)),
    stop_rows_total: document.querySelectorAll(".v8-map-stop").length,
    markers,
    scroll_y: Math.round(window.scrollY),
    document_height: document.documentElement.scrollHeight,
  };
};

(async () => {
  const br = await chromium.launch({ channel: "chrome", headless: true });
  const ctx = await br.newContext({ viewport: { width: VPW, height: VPH },
    locale: LOCALE || undefined });
  const p = await ctx.newPage();
  if (LOCALE) { await p.addInitScript((l) => { try { localStorage.setItem("citynexus.locale", l); } catch (e) {} }, LOCALE); }
  const errors = [];
  p.on("pageerror", (e) => errors.push("pageerror: " + String(e).slice(0, 160)));
  await p.goto(BASE.replace(/\/$/, "") + "/v8/map", { waitUntil: "networkidle", timeout: 60000 });
  const seal = p.getByText("使用封存的演示行程", { exact: false }).first();
  if (await seal.count()) { await seal.click(); await p.waitForTimeout(5000); }
  const before = await p.evaluate(snap);
  const m = before.markers[NTH];
  if (!m) { console.log("FATAL no marker index", NTH); await br.close(); process.exit(9); }
  const centre = [Math.round(m.box[0] + m.box[2] / 2), Math.round(m.box[1] + m.box[3] / 2)];
  await p.mouse.click(centre[0], centre[1]);
  await p.waitForTimeout(2500);
  const after = await p.evaluate(snap);
  const name = m.aria;
  const contains = (s) => !!(s && name && s.includes(name));
  const out = {
    base: BASE, locale: LOCALE || "(browser default)", viewport_requested: [VPW, VPH],
    tapped_marker_index_0: NTH, tap_centre: centre, target_place_name: name,
    before, after, errors,
    changed: {
      caption: before.caption !== after.caption,
      overlay: before.overlay !== after.overlay,
      h2_map_selected_stop: before.h2_map_selected_stop !== after.h2_map_selected_stop,
      stop_rows_selected: JSON.stringify(before.stop_rows_selected) !== JSON.stringify(after.stop_rows_selected),
      marker_pressed_flags: JSON.stringify(before.markers.map((x) => x.pressed)) !==
                            JSON.stringify(after.markers.map((x) => x.pressed)),
      marker_classes: JSON.stringify(before.markers.map((x) => x.cls)) !==
                      JSON.stringify(after.markers.map((x) => x.cls)),
      overlay_box: JSON.stringify(before.overlay_box) !== JSON.stringify(after.overlay_box),
    },
    name_shown: {
      in_caption: contains(after.caption),
      in_overlay_stack: contains(after.overlay),
      in_h2_outside_panel: contains(after.h2_map_selected_stop),
      in_a_selected_stop_row: after.stop_rows_selected.some((s) => contains(s)),
      anywhere_read_by_this_probe: contains(after.caption) || contains(after.overlay) ||
        contains(after.h2_map_selected_stop) || after.stop_rows_selected.some((s) => contains(s)),
    },
    geometry: {
      overlay_box_before: before.overlay_box, overlay_box_after: after.overlay_box,
      overlay_growth_px: (before.overlay_box && after.overlay_box)
        ? after.overlay_box[3] - before.overlay_box[3] : null,
      markers_covered_by_overlay_px2_after: after.markers.map((x) => x.covered_by_overlay_px2),
      markers_not_hittable_after: after.markers
        .filter((x) => !(x.hit_at_centre && x.hit_at_centre.is_marker))
        .map((x) => ({ text: x.text, hit: x.hit_at_centre })),
      markers_centre_y_after: after.markers.map((x) => Math.round(x.box[1] + x.box[3] / 2)),
      h2_in_viewport_after: after.h2_in_viewport,
    },
  };
  fs.mkdirSync(OUT, { recursive: true });
  fs.writeFileSync(OUT + "/probe.json", JSON.stringify(out, null, 1));
  const c = out.changed, n = out.name_shown;
  console.log(JSON.stringify({ locale: out.locale, vp: out.viewport_requested, tapped: name,
    changed: c, name_shown: n, overlay_growth_px: out.geometry.overlay_growth_px,
    markers_covered_px2: out.geometry.markers_covered_by_overlay_px2_after,
    not_hittable: out.geometry.markers_not_hittable_after.length,
    h2_in_viewport: out.geometry.h2_in_viewport_after, errors: errors.length }));
  await br.close();
})().catch((e) => { console.log("FATAL", String(e).slice(0, 300)); process.exit(9); });
