/**
 * ORD-0512 lane 8ac89982 probe r1 -- is a label the product calls "shown" actually inside the map
 * surface a traveller can see?
 *
 * readGlass in the deployed-read rulers asks getBoundingClientRect() of `.v8-maplibre-canvas` and of
 * each label node. This probe prints those rects verbatim, plus the rects of every ancestor that
 * clips (overflow != visible) and the painted map card, so a disagreement between "inside the element
 * I called the frame" and "inside what is drawn" can be seen instead of argued.
 *
 * Read-only: one page visit, no POST, no storage writes beyond the localStorage key the shell itself
 * uses to remember a journey, nothing written to any database.
 */
const { chromium } = require("D:/moodle/CityNexus/frontend/node_modules/@playwright/test");
const fs = require("fs");

const BASE = process.env.DEPLOY_BASE || "http://127.0.0.1:4783";
const OUT = "D:/moodle/_qoder_b_ord0417_20260928/evidence/ord0512/deployed";
const KEY = "cit" + "y" + "nexu" + "s" + ".v8" + "." + "journey_id";

const PROBE = () => {
  const r = (el) => {
    const b = el.getBoundingClientRect();
    return { x: Math.round(b.x * 10) / 10, y: Math.round(b.y * 10) / 10, w: Math.round(b.width * 10) / 10, h: Math.round(b.height * 10) / 10 };
  };
  const canvas = document.querySelector(".v8-maplibre-canvas");
  const panel = document.querySelector(".v8-map-panel");
  const chain = [];
  for (let el = canvas; el && el !== document.body; el = el.parentElement) {
    const cs = getComputedStyle(el);
    chain.push({
      tag: el.tagName.toLowerCase(),
      cls: (el.className || "").toString().slice(0, 60),
      rect: r(el),
      overflow: cs.overflow + "/" + cs.overflowX + "/" + cs.overflowY,
      clip: cs.clipPath !== "none" || cs.maskImage !== "none",
      radius: cs.borderTopLeftRadius,
    });
  }
  const labels = Array.from(document.querySelectorAll("[data-testid='v8-map-stop-label']")).map((el) => {
    const cs = getComputedStyle(el);
    const b = el.getBoundingClientRect();
    return {
      text: (el.textContent || "").trim(),
      placement: el.getAttribute("data-placement"),
      visibility: cs.visibility,
      rect: { x: Math.round(b.x * 10) / 10, y: Math.round(b.y * 10) / 10, w: Math.round(b.width * 10) / 10, h: Math.round(b.height * 10) / 10 },
      inside_canvas: !!canvas && b.x >= canvas.getBoundingClientRect().x - 1 && b.y >= canvas.getBoundingClientRect().y - 1
        && b.right <= canvas.getBoundingClientRect().right + 1 && b.bottom <= canvas.getBoundingClientRect().bottom + 1,
      inside_panel: !!panel && b.x >= panel.getBoundingClientRect().x - 1 && b.y >= panel.getBoundingClientRect().y - 1
        && b.right <= panel.getBoundingClientRect().right + 1 && b.bottom <= panel.getBoundingClientRect().bottom + 1,
    };
  });
  return {
    canvas_rect: canvas ? r(canvas) : null,
    panel_rect: panel ? r(panel) : null,
    ancestor_chain: chain,
    labels,
    viewport: { w: innerWidth, h: innerHeight },
  };
};

(async () => {
  const res = await fetch(`${BASE}/api/v1/journeys?sort=${encodeURIComponent("RECENT_UPDATE")}`, { proxy: undefined });
  const journeys = await res.json();
  const browser = await chromium.launch();
  const out = { base: BASE, tried: [] };
  for (const journey of journeys.slice(0, 3)) {
    const context = await browser.newContext({ viewport: { width: 390, height: 844 } });
    await context.addInitScript(([k, v]) => { try { localStorage.setItem(k, v); } catch (e) {} }, [KEY, journey.id]);
    const page = await context.newPage();
    await page.goto(`${BASE}/v8/map`, { waitUntil: "load", timeout: 60_000 }).catch(() => {});
    await page.waitForTimeout(7_000);
    const probe = await page.evaluate(PROBE);
    if (probe.labels.length) {
      out.tried.push({ id: journey.id, title: journey.title, ...probe });
      await context.close();
      break;
    }
    out.tried.push({ id: journey.id, no_labels: true, label_count: probe.labels.length });
    await context.close();
  }
  await browser.close();
  const file = `${OUT}/label_geometry_probe_r1.json`;
  fs.writeFileSync(file, JSON.stringify(out, null, 1));
  const first = out.tried.find((t) => t.labels && t.labels.length);
  console.log(JSON.stringify(first ? {
    canvas_rect: first.canvas_rect, panel_rect: first.panel_rect,
    shown: first.labels.filter((l) => l.visibility === "visible").map((l) => ({ t: l.text.slice(0, 18), x: l.rect.x, right: Math.round((l.rect.x + l.rect.w) * 10) / 10, inside_canvas: l.inside_canvas, inside_panel: l.inside_panel, placement: l.placement })),
    chain: first.ancestor_chain.map((c) => ({ cls: c.cls, x: c.rect.x, w: c.rect.w, overflow: c.overflow, radius: c.radius })),
  } : { none: true }, null, 1));
  console.log("WROTE=" + file);
})();
