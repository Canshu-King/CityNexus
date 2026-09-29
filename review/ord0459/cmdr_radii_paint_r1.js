/* ORD-0459 -- for every sampled element, record what it actually paints.
 *
 * The joiner found 19 elements whose computed radius changed and only 4 whose own crop moved pixels.
 * "The other 15 did not move" is not an acceptable sentence -- the reason has to be measured. So this
 * instrument reads, per element, the properties that decide whether a corner can be seen at all:
 * background-image, background-color, the four border widths and colours, box-shadow, overflow of a
 * child that covers the corner, and the corner's own pixel via a canvas-free geometry check.
 *
 * Usage: node cmdr_radii_paint_r1.js <base> <out.json>
 */
const { chromium } = require("D:/moodle/CityNexus/frontend/node_modules/playwright");
const fs = require("fs");

const BASE = (process.argv[2] || "").replace(/\/$/, "");
const OUT = process.argv[3];
const VP = { width: +(process.argv[5] || 390), height: +(process.argv[6] || 844) };

(async () => {
  const b = await chromium.launch({ chromiumSandbox: false });
  const p = await (await b.newContext({ viewport: VP, locale: "zh-CN" })).newPage();
  await p.goto(BASE + "/", { waitUntil: "networkidle", timeout: 60000 });
  const e = p.getByText("使用封存的演示行程", { exact: false }).first();
  if (await e.count()) await e.click({ timeout: 8000 }).catch(() => {});
  // the same settle the shot instrument uses, or the two runs are not on the same screen
  const started = Date.now();
  let last = -1, stableFor = 0;
  while (Date.now() - started < 25000) {
    const n = await p.evaluate(() => performance.getEntriesByType("resource")
      .filter((x) => /tile\.openstreetmap\.org/.test(x.name)).length);
    if (n === last) { stableFor += 1; } else { stableFor = 0; last = n; }
    if (stableFor >= 3) break;
    await p.waitForTimeout(700);
  }
  await p.waitForTimeout(1200);
  const screen = await p.evaluate(() => ({
    has_hub_cta: !!document.querySelector('[data-testid="today-hero-cta"]'),
    has_pending: !!document.querySelector('[data-testid="pending-empty-action"]'),
    h1: (document.querySelector("h1") || {}).textContent || null,
  }));
  const rows = await p.evaluate(() => {
    const sel = "button, [class*=card], [class*=panel], input";
    const out = [];
    document.querySelectorAll(sel).forEach((el) => {
      const cs = getComputedStyle(el);
      const r = el.getBoundingClientRect();
      if (cs.display === "none" || cs.visibility === "hidden" || r.width < 2 || r.height < 2) return;
      const sides = ["TopLeft", "TopRight", "BottomLeft", "BottomRight"];
      const corner = {};
      sides.forEach((s) => {
        const bw = parseFloat(cs["border" + s + "Width"] || "0");
        const bc = cs["border" + s + "Color"];
        corner[s] = { border_width_px: bw, border_color: bc };
      });
      out.push({
        tag: el.tagName.toLowerCase(),
        cls: String(el.className || "").slice(0, 70),
        testid: el.getAttribute("data-testid") || null,
        radius: cs.borderRadius,
        background_color: cs.backgroundColor,
        background_image: cs.backgroundImage === "none" ? "none" : "set",
        box_shadow: cs.boxShadow === "none" ? "none" : "set",
        border_widths: corner,
        rect: [Math.round(r.x), Math.round(r.y), Math.round(r.width), Math.round(r.height)],
      });
    });
    return out;
  });
  const paintable = rows.map((x) => {
    const anyBorder = Object.values(x.border_widths).some((c) => c.border_width_px > 0);
    const filled = x.background_color !== "rgba(0, 0, 0, 0)" && x.background_color !== "transparent";
    return { ...x, has_border: anyBorder, has_fill: filled, corner_can_paint: anyBorder || filled || x.box_shadow === "set" || x.background_image === "set" };
  });
  fs.writeFileSync(OUT, JSON.stringify({ base: BASE, viewport: `${VP.width}x${VP.height}`,
                                        screen, elements: paintable }, null, 1) + "\n", "utf-8");
  const can = paintable.filter((x) => x.corner_can_paint).length;
  console.log(BASE + ": " + paintable.length + " elements, screen " + JSON.stringify(screen) +
              ", corners that can paint: " + can + ", cannot paint: " + (paintable.length - can));
  for (const x of paintable.filter((y) => !y.corner_can_paint)) {
    console.log("   no-edge: " + x.tag + " cls=" + x.cls.slice(0, 34) + " testid=" + (x.testid || "-") +
                " bg=" + x.background_color + " border=" + x.has_border + " shadow=" + x.box_shadow);
  }
  await b.close();
})();
