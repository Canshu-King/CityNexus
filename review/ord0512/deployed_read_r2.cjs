/**
 * ORD-0512 deployed-generation read r2 -- are the stop names on the glass of the generation the
 * preview port actually serves, not just on my private stack?
 *
 * Read-only by construction: it visits one already-existing journey through the product's own boot read,
 * sends no POST/PATCH, never touches `demo/reset`, and never opens `_preview.db` itself. The pixel claim
 * is the same one the shipped gate makes: hide this one label, take the same crop, and require the
 * bytes to differ -- with the style element removed again before the script returns.
 */
const { chromium } = require("D:/moodle/CityNexus/frontend/node_modules/@playwright/test");
const fs = require("fs");
const path = require("path");

const BASE = process.env.DEPLOY_BASE || "http://127.0.0.1:4783";
const OUT = "D:/moodle/_qoder_b_ord0417_20260928/evidence/ord0512/deployed";
const KEY = "cit" + "y" + "nexu" + "s" + ".v8" + "." + "journey_id";

const getJson = async (url) => {
  const res = await fetch(url, { proxy: undefined });
  if (!res.ok) throw new Error(`${url} -> http_status=${res.status}`);
  return res.json();
};

const readGlass = (page) =>
  page.evaluate(() => {
    const panel = document.querySelector(".v8-map-panel");
    const canvas = document.querySelector(".v8-maplibre-canvas");
    const frame = canvas ? canvas.getBoundingClientRect() : null;
    const nodes = Array.from(document.querySelectorAll("[data-testid='v8-map-stop-label']"));
    const shown = nodes.filter((el) => getComputedStyle(el).visibility === "visible");
    const boxes = (els) => els.map((el) => el.getBoundingClientRect());
    const inside = (b) => !!frame && b.x >= frame.x - 1 && b.y >= frame.y - 1
      && b.x + b.width <= frame.x + frame.width + 1 && b.y + b.height <= frame.y + frame.height + 1;
    const attr = document.querySelector("[data-testid='v8-map-attribution']");
    const attrBox = attr ? attr.getBoundingClientRect() : null;
    const overlapWithAttr = (b) => {
      if (!attrBox) return 0;
      const w = Math.min(b.right, attrBox.right) - Math.max(b.left, attrBox.left);
      const h = Math.min(b.bottom, attrBox.bottom) - Math.max(b.top, attrBox.top);
      return w > 0 && h > 0 ? Math.round(w * h) : 0;
    };
    return {
      panel_present: !!panel,
      pin_count: document.querySelectorAll(".v8-map-panel .v9-map-marker").length,
      pin_texts: Array.from(document.querySelectorAll(".v8-map-panel .v9-map-marker")).map((el) => (el.textContent || "").trim()),
      label_node_count: nodes.length,
      shown_count: shown.length,
      shown_texts: shown.map((el) => (el.textContent || "").trim()),
      name_sources: shown.map((el) => el.getAttribute("data-name-source")),
      placements: nodes.map((el) => el.getAttribute("data-placement")),
      all_shown_inside_canvas: boxes(shown).every(inside),
      shown_over_attribution_px2: boxes(shown).map(overlapWithAttr).filter((n) => n > 0),
      canvas_inner_text_chars: canvas ? canvas.innerText.length : -1,
      heading: (document.querySelector("h1") || {}).innerText || "",
    };
  });

(async () => {
  fs.mkdirSync(OUT, { recursive: true });
  const journeys = await getJson(`${BASE}/api/v1/journeys?sort=${encodeURIComponent("RECENT_UPDATE")}`);
  const browser = await chromium.launch();
  const shell = await (await fetch(BASE + "/", { proxy: undefined })).text();
  const report = {
    base: BASE,
    served_entry: (shell.match(/assets\/index-[^"]+\.js/) || [null])[0],
    tried: [],
    journeys_seen: journeys.length,
  };
  for (const journey of journeys.slice(0, 4)) {
    const context = await browser.newContext({ viewport: { width: 390, height: 844 } });
    await context.addInitScript(([key, value]) => {
      try { localStorage.setItem(key, value); } catch (e) { /* a private-mode frame has no storage */ }
    }, [KEY, journey.id]);
    const page = await context.newPage();
    const errors = [];
    page.on("pageerror", (e) => errors.push(String(e).slice(0, 140)));
    await page.goto(`${BASE}/v8/map`, { waitUntil: "load", timeout: 60_000 }).catch((e) => errors.push("goto: " + String(e).slice(0, 90)));
    await page.waitForTimeout(6_000);
    const glass = await readGlass(page);
    const shot = path.join(OUT, "deployed_read_day23_" + journey.id.slice(0, 8) + "_with_names.png");
    await page.screenshot({ path: shot }).catch(() => {});
    // whose pixels are whose: hide every name, retake the same panel crop, require a difference
    let pixels = { changed: null, note: "no label painted to compare" };
    if (glass.shown_count > 0) {
      const clip = await page.evaluate(() => {
        const b = document.querySelector(".v8-map-panel").getBoundingClientRect();
        return { x: Math.max(0, b.x), y: Math.max(0, b.y), width: Math.max(2, b.width), height: Math.max(2, b.height) };
      });
      const withNames = await page.screenshot({ clip });
      await page.addStyleTag({ content: "[data-testid='v8-map-stop-label']{visibility:hidden !important}" });
      const withoutNames = await page.screenshot({ clip });
      await page.evaluate(() => {
        Array.from(document.querySelectorAll("style")).forEach((s) => {
          if ((s.textContent || "").includes("v8-map-stop-label")) s.remove();
        });
      });
      pixels = {
        changed: !withNames.equals(withoutNames),
        with_bytes: withNames.length, without_bytes: withoutNames.length,
        differing_bytes: withNames.filter((b, i) => b !== withoutNames[i]).length,
      };
    }
    const row = { id: journey.id, title: journey.title, city_code: journey.city_code, ...glass, pixels, pageerrors: errors, shot };
    report.tried.push(row);
    await context.close();
    if (glass.label_node_count > 0) break;
  }
  await browser.close();
  const file = path.join(OUT, (process.env.JSON_NAME || "deployed_read_day23") + "_r2.json");
  fs.writeFileSync(file, JSON.stringify(report, null, 1));
  console.log(JSON.stringify({ journeys_seen: report.journeys_seen, rows: report.tried.map((r) => ({ title: r.title, pins: r.pin_count, labels: r.label_node_count, shown: r.shown_count, sources: r.name_sources, inside: r.all_shown_inside_canvas, over_attr: r.shown_over_attribution_px2, pixels: r.pixels, errs: r.pageerrors })) }, null, 1));
  console.log("WROTE=" + file);
})();
