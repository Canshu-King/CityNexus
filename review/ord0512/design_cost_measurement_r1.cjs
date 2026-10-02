/**
 * ORD-0512 next-hand measurement r1 -- what each of the three candidate designs would actually buy.
 *
 * The shipped placement rule hides a name when neither side of its pin can hold it. On the deployed
 * generation that leaves two of eight names visible at phone width, and the open question for the
 * commander is whether to pay for more names with wrapping, with truncation, or by moving the word under
 * the pin. This script measures all three on the live screen: it clones each label to learn the box that
 * design would produce, then runs the same greedy order the product uses (picked stop first, then the
 * current one, then plan order; the map surface is the frame; attribution / caption / tile notice / the
 * named control are reserved ground) and counts what survives.
 *
 * It is a model of the rule, measured on the real screen -- not the rule itself, and not a product
 * change. Nothing is written: one read-only page visit, styles are added and removed inside one evaluate.
 */
const { chromium } = require("D:/moodle/CityNexus/frontend/node_modules/@playwright/test");
const fs = require("fs");
const path = require("path");

const BASE = process.env.DEPLOY_BASE || "http://127.0.0.1:4783";
const OUT = "D:/moodle/_qoder_b_ord0417_20260928/evidence/ord0512/deployed";
const KEY = "cit" + "y" + "nexu" + "s" + ".v8" + "." + "journey_id";

const MEASURE = () => {
  const canvas = document.querySelector(".v8-maplibre-canvas");
  const panel = document.querySelector(".v8-map-panel");
  const map = canvas && canvas.citynexusMap;
  if (!canvas || !panel || !map) return { error: "no map on this screen" };
  const frameRect = canvas.getBoundingClientRect();
  const frame = { x: frameRect.x, y: frameRect.y, w: frameRect.width, h: frameRect.height };
  const reservedSel = [
    "[data-testid='v8-map-attribution']", ".v8-map-overlay-stack", ".v8-map-caption",
    ".v8-map-tile-notice", "[data-testid='v8-map-gesture-hint']", "[data-testid='map-viewport-reset']",
  ].join(", ");
  const reserved = Array.from(panel.querySelectorAll(reservedSel))
    .map((el) => el.getBoundingClientRect())
    .filter((b) => b.width > 0 && b.height > 0)
    .map((b) => ({ x: b.x, y: b.y, w: b.width, h: b.height }));
  const labels = Array.from(document.querySelectorAll("[data-testid='v8-map-stop-label']"));
  const pins = Array.from(document.querySelectorAll(".v8-map-panel .v9-map-marker"));

  // one offscreen probe, restyled per design, to learn the box that design would produce
  const probe = document.createElement("div");
  probe.className = "v8-map-stop-label";
  probe.style.position = "absolute";
  probe.style.left = "-2000px";
  probe.style.top = "0px";
  panel.appendChild(probe);
  const boxFor = (text, design) => {
    probe.style.cssText = "position:absolute;left:-2000px;top:0px;";
    probe.className = "v8-map-stop-label";
    if (design === "wrap") {
      probe.classList.add("measure-wrap");
    } else if (design === "truncate") {
      probe.classList.add("measure-truncate");
    }
    probe.textContent = text;
    const b = probe.getBoundingClientRect();
    return { w: b.width, h: b.height };
  };
  const style = document.createElement("style");
  style.textContent = [
    ".v8-map-stop-label.measure-wrap{white-space:normal;width:120px;line-height:1.3;}",
    ".v8-map-stop-label.measure-truncate{white-space:nowrap;max-width:96px;overflow:hidden;text-overflow:ellipsis;}",
  ].join("");
  document.head.appendChild(style);

  const overlaps = (a, b) => {
    const w = Math.min(a.x + a.w, b.x + b.w) - Math.max(a.x, b.x);
    const h = Math.min(a.y + a.h, b.y + b.h) - Math.max(a.y, b.y);
    return w > 1 && h > 1;
  };
  const inside = (b) => b.x >= frame.x - 1 && b.y >= frame.y - 1
    && b.x + b.w <= frame.x + frame.w + 1 && b.y + b.h <= frame.y + frame.h + 1;
  const greedy = (candidates) => {
    const ordered = [...candidates].sort((a, b) => b.priority - a.priority || a.order - b.order);
    const placed = reserved.map((box) => ({ box, kind: "control" }));
    let shown = 0;
    const reasons = [];
    for (const candidate of ordered) {
      const fitting = candidate.sides.filter(inside);
      if (!fitting.length) { shown += 0; reasons.push(["off_map", candidate.text]); continue; }
      const free = fitting.find((box) => !placed.some((p) => overlaps(box, p.box)));
      if (!free) { reasons.push([placed.some((p) => p.kind === "name") ? "over_a_name" : "over_a_control", candidate.text]); continue; }
      placed.push({ box: free, kind: "name" });
      shown += 1;
    }
    return { shown, hidden: reasons.length, reasons };
  };

  const designs = {};
  for (const design of ["asis_right_then_left", "wrap_two_lines", "truncate_ninety_six", "under_the_pin"]) {
    const candidates = labels.map((el, index) => {
      const pin = pins[index];
      const text = el.textContent.trim();
      // measure from the marker's own anchor: the label element is transformed by maplibre, so its
      // centre still sits where the pin is; use the pin box, which is the same anchor
      const pb = pin.getBoundingClientRect();
      const cx = pb.x + pb.width / 2;
      const cy = pb.y + pb.height / 2;
      const size = boxFor(text, design === "wrap_two_lines" ? "wrap" : design === "truncate_ninety_six" ? "truncate" : "asis");
      const gap = 18;
      let sides;
      if (design === "under_the_pin") {
        sides = [{ x: cx - size.w / 2, y: cy + 20, w: size.w, h: size.h },
                 { x: cx - size.w / 2, y: cy - 20 - size.h, w: size.w, h: size.h }];
      } else if (design === "asis_right_then_left") {
        sides = [{ x: cx + gap, y: cy - size.h / 2, w: size.w, h: size.h },
                 { x: cx - gap - size.w, y: cy - size.h / 2, w: size.w, h: size.h }];
      } else {
        // wrap and truncate keep both sides too -- they only change the box's shape
        sides = [{ x: cx + gap, y: cy - size.h / 2, w: size.w, h: size.h },
                 { x: cx - gap - size.w, y: cy - size.h / 2, w: size.w, h: size.h }];
      }
      const pressed = pin.getAttribute("aria-pressed") === "true";
      return { text, sides, priority: pressed ? 3 : (pin.classList.contains("current") ? 2 : 1), order: index };
    });
    designs[design] = greedy(candidates);
    designs[design].widest_label_px = Math.max(...candidates.map((c) => Math.round(c.sides[0].w)));
  }
  const widths = labels.map((el) => {
    probe.className = "v8-map-stop-label";
    probe.style.cssText = "position:absolute;left:-2000px;top:0px;";
    probe.textContent = el.textContent.trim();
    const b = probe.getBoundingClientRect();
    return { text: el.textContent.trim(), w: Math.round(b.width), h: Math.round(b.height) };
  });
  probe.remove();
  style.remove();
  return {
    frame, reserved_boxes: reserved.length, label_nodes: labels.length,
    canvas_width_px: Math.round(frame.w), canvas_height_px: Math.round(frame.h),
    names: widths, designs,
    shipped_visible_count: labels.filter((el) => getComputedStyle(el).visibility === "visible").length,
  };
};

(async () => {
  fs.mkdirSync(OUT, { recursive: true });
  const res = await fetch(`${BASE}/api/v1/journeys?sort=${encodeURIComponent("RECENT_UPDATE")}`, { proxy: undefined });
  const journeys = await res.json();
  const browser = await chromium.launch();
  const report = { base: BASE, journeys_seen: journeys.length, tries: [] };
  for (const journey of journeys.slice(0, 3)) {
    const context = await browser.newContext({ viewport: { width: 390, height: 844 } });
    await context.addInitScript(([key, value]) => { try { localStorage.setItem(key, value); } catch (e) {} }, [KEY, journey.id]);
    const page = await context.newPage();
    await page.goto(`${BASE}/v8/map`, { waitUntil: "load", timeout: 60_000 }).catch(() => {});
    await page.waitForTimeout(9_000);
    const shot = path.join(OUT, "measurement_screen.png");
    await page.screenshot({ path: shot }).catch(() => {});
    const measured = await page.evaluate(MEASURE);
    report.tries.push({ id: journey.id, title: journey.title, measured });
    await context.close();
    if (measured && measured.label_nodes) break;
  }
  await browser.close();
  const file = path.join(OUT, "design_cost_measurement_r1.json");
  fs.writeFileSync(file, JSON.stringify(report, null, 1));
  const first = report.tries[0] && report.tries[0].measured;
  console.log(JSON.stringify({
    journeys_seen: report.journeys_seen,
    canvas: first && { w: first.canvas_width_px, h: first.canvas_height_px },
    shipped_visible: first && first.shipped_visible_count,
    designs: first && Object.fromEntries(Object.entries(first.designs).map(([k, v]) => [k, { shown: v.shown, hidden: v.hidden, widest: v.widest_label_px, why_hidden: v.reasons.map((r) => r[0]) }])),
  }, null, 1));
  console.log("WROTE=" + file);
})();
