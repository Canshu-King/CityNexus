/**
 * ORD-0497 follow-up (the commander's 23:53 reading) -- who owns the pointer on the map glass.
 *
 * His reading: at the centre of `map-stamp-date-<uuid>` the hit test comes back with something else
 * (probably the canvas under it), while Playwright's own click on that node does not throw.  This
 * probe measures both surfaces -- the PIN and the DATE BADGE beside it -- in the light and the dark
 * scheme, at 390x844, and says which element answers at each centre.  It changes nothing; it is the
 * reading the ruling asks for.
 *
 * Why the answer is not "the badge is broken": `.v8-map-stamp-date` is `pointer-events: none` on
 * purpose (`frontend/src/map-selection.css`, the ORD-0497 block) -- an element that swallows a tap on
 * the glass takes the pin's hit test and the drag with it, which is the ORD-0134 failure this panel
 * already shipped once.  The pin is the control; the badge is paint.
 */
import { chromium } from "playwright";
import { mkdirSync, writeFileSync } from "node:fs";

const BASE = "http://127.0.0.1:4795";
const JOURNEY = "22222222-2222-4222-8222-222222222222";
const outDir = "D:/moodle/_qoder_ai_ord0387_20260928/ord0530_reads";
mkdirSync(outDir, { recursive: true });

const browser = await chromium.launch();
const report = { base: BASE, journey: JOURNEY, shape: "390x844", schemes: [] };

for (const scheme of ["light", "dark"]) {
  const context = await browser.newContext({ viewport: { width: 390, height: 844 }, locale: "zh-CN" });
  const page = await context.newPage();
  await page.addInitScript((id) => {
    localStorage.setItem("citynexus.v8.journey_id", id);
    localStorage.setItem("citynexus.locale", "zh-CN");
  }, JOURNEY);
  await page.goto(`${BASE}/v8/map`, { waitUntil: "load", timeout: 60000 });
  await page.waitForSelector("[data-testid='v8-maplibre-panel']", { timeout: 30000 });
  await page.waitForSelector(".v8-map-stamp-date", { timeout: 30000 });
  if (scheme === "dark") {
    await page.evaluate(() => {
      const button = Array.from(document.querySelectorAll("button")).find((b) =>
        /暗色|dark|主题|theme/i.test((b.textContent || "") + (b.getAttribute("aria-label") || "")),
      );
      if (button) button.click();
      else document.documentElement.setAttribute("data-theme", "dark");
    });
    await page.waitForTimeout(900);
  }
  const read = await page.evaluate(() => {
    const probe = (el, label) => {
      el.scrollIntoView({ block: "center" });
      const r = el.getBoundingClientRect();
      const cx = Math.round(r.x + r.width / 2);
      const cy = Math.round(r.y + r.height / 2);
      const at = document.elementFromPoint(cx, cy);
      const cs = getComputedStyle(el);
      return {
        label,
        box: { x: Math.round(r.x), y: Math.round(r.y), w: Math.round(r.width), h: Math.round(r.height) },
        centre: { x: cx, y: cy },
        in_viewport: r.top >= 0 && r.bottom <= window.innerHeight,
        pointer_events: cs.pointerEvents,
        hit: at ? at.tagName.toLowerCase() + "." + String(at.className || "").slice(0, 30) : "none",
        hit_is_self: !!(at && (at === el || el.contains(at))),
        hit_is_the_pin: !!(at && at.closest && at.closest(".v9-map-marker")),
      };
    };
    const pin = document.querySelector(".v8-map-panel .v9-map-marker.stamped")
      || document.querySelector(".v8-map-panel .v9-map-marker");
    const badge = document.querySelector(".v8-map-panel .v8-map-stamp-date");
    return {
      theme_attr: document.documentElement.getAttribute("data-theme")
        || document.body.getAttribute("data-theme") || "none",
      pins: document.querySelectorAll(".v8-map-panel .v9-map-marker").length,
      stamped: document.querySelectorAll(".v8-map-panel .v9-map-marker.stamped").length,
      badges: document.querySelectorAll(".v8-map-panel .v8-map-stamp-date").length,
      pin_probe: pin ? probe(pin, "pin") : null,
      badge_probe: badge ? probe(badge, "badge") : null,
    };
  });
  await page.screenshot({ path: `${outDir}/map_pointer_ownership_${scheme}.png` });
  report.schemes.push({ scheme, read });
  await context.close();
}
await browser.close();
writeFileSync(`${outDir}/map_pointer_ownership.json`, JSON.stringify(report, null, 1), "utf8");
for (const s of report.schemes) {
  console.log(s.scheme, "theme", s.read.theme_attr, "pins", s.read.pins, "stamped", s.read.stamped, "badges", s.read.badges);
  console.log("   pin  ", JSON.stringify(s.read.pin_probe));
  console.log("   badge", JSON.stringify(s.read.badge_probe));
}
