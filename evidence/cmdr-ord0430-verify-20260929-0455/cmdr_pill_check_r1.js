/* CMDR own-eyeball check for ORD-0430 at tip ae69f63a (generation index-BvJw3mnZ.js).
 * The ruling I made: yielding must MOVE the pill inside the viewport, and it must stay hittable.
 * The failure mode I am testing for is the one the lane's own readings exposed last time:
 * covering_arms went to zero because the pill was hidden (opacity/visibility/pointer-events),
 * so panel_opened dropped instead of overlap. Both directions are read here, from the DOM.
 */
const { chromium } = require("D:/moodle/CityNexus/frontend/node_modules/playwright");
const fs = require("fs");

const BASE = process.argv[2] || "http://127.0.0.1:4822";
const OUT = process.argv[3] || "D:/moodle/_qoder_cmdr_ref_20260921/live_checks/_pill_check_r1/";
fs.mkdirSync(OUT, { recursive: true });

(async () => {
  const browser = await chromium.launch({ chromiumSandbox: false });
  const ctx = await browser.newContext({ locale: "zh-CN" });
  const page = await ctx.newPage();
  await page.setViewportSize({ width: 390, height: 844 });
  const errors = [];
  page.on("pageerror", (e) => errors.push(String(e).slice(0, 140)));
  const rec = { base: BASE, errors: errors, screens: {} };

  await page.goto(BASE + "/", { waitUntil: "networkidle", timeout: 60000 });
  const entry = page.getByText("使用封存的演示行程", { exact: false }).first();
  rec.entry_used = (await entry.count()) > 0;
  if (rec.entry_used) await entry.click({ timeout: 8000 }).catch(() => {});
  await page.waitForTimeout(3000);

  for (const route of ["twin", "discover", "hub"]) {
    await page.goto(BASE + "/v8/" + route, { waitUntil: "networkidle", timeout: 60000 });
    await page.waitForTimeout(3000);
    const before = await page.evaluate(() => {
      const dock = document.querySelector("[data-testid='v18-copilot-dock']");
      if (!dock) return { present: false };
      const r = dock.getBoundingClientRect();
      const cs = getComputedStyle(dock);
      const cx = r.left + r.width / 2, cy = r.top + r.height / 2;
      const hit = document.elementFromPoint(cx, cy);
      const textLeaves = [];
      const walk = document.createElement("div");
      document.querySelectorAll("h1,h2,h3,h4,p,span,strong,li").forEach((e) => {
        const t = (e.innerText || "").trim();
        if (!t || t.length > 90) return;
        const rr = e.getBoundingClientRect();
        if (rr.width <= 0 || rr.height <= 0) return;
        const ox = Math.max(0, Math.min(r.right, rr.right) - Math.max(r.left, rr.left));
        const oy = Math.max(0, Math.min(r.bottom, rr.bottom) - Math.max(r.top, rr.top));
        if (ox >= 4 && oy >= 4) textLeaves.push({ text: t.slice(0, 60), ox: Math.round(ox), oy: Math.round(oy) });
      });
      return {
        present: true, rect: { x: Math.round(r.x), y: Math.round(r.y), w: Math.round(r.width), h: Math.round(r.height) },
        in_viewport: r.left >= 0 && r.top >= 0 && r.right <= innerWidth && r.bottom <= innerHeight,
        styles: { opacity: cs.opacity, visibility: cs.visibility, pointer_events: cs.pointerEvents, transform: cs.transform.slice(0, 40) },
        hit_is_dock_or_child: !!hit && (hit === dock || dock.contains(hit)),
        hit_tag: hit ? hit.tagName : null,
        overlapping_text: textLeaves.slice(0, 5),
        yield_class: dock.className,
      };
    });
    const opened = await page.evaluate(async () => {
      const dock = document.querySelector("[data-testid='v18-copilot-dock']");
      if (!dock) return { clicked: false };
      const r = dock.getBoundingClientRect();
      const cx = r.left + r.width / 2, cy = r.top + r.height / 2;
      const hit = document.elementFromPoint(cx, cy);
      const target = hit && (hit === dock || dock.contains(hit)) ? hit : (hit || null);
      if (target) target.dispatchEvent(new PointerEvent("pointerdown", { bubbles: true })),
        target.dispatchEvent(new PointerEvent("pointerup", { bubbles: true })),
        target.dispatchEvent(new MouseEvent("click", { bubbles: true }));
      return { clicked: !!target, hit_tag: target ? target.tagName : null };
    });
    await page.waitForTimeout(1800);
    const panel = await page.evaluate(() => {
      const cand = document.querySelector("[data-testid*='agent'], [data-testid*='copilot'], textarea, [role='dialog']");
      const body = (document.body.innerText || "");
      return {
        candidate_testid: cand ? cand.getAttribute("data-testid") : null,
        body_len: body.length,
        has_input: !!document.querySelector("textarea, input[type='text']"),
      };
    });
    rec.screens[route] = { dock: before, click: opened, after_click: panel, reached_route: await page.evaluate(() => location.pathname) };
    await page.screenshot({ path: OUT + "pill_" + route + ".png" });
  }
  await browser.close();
  const bad = Object.entries(rec.screens).filter(([, v]) => !v.dock.present || !v.dock.in_viewport || !v.dock.hit_is_dock_or_child || (v.dock.overlapping_text || []).length > 0);
  rec.verdict = bad.length ? "PILL_STILL_COVERS_OR_UNHITTABLE_ON:" + bad.map((b) => b[0]).join(",") : "PILL_MOVED_AND_STILL_HITTABLE";
  fs.writeFileSync(OUT + "pill_check_r1.json", JSON.stringify(rec, null, 1));
  console.log(JSON.stringify(Object.fromEntries(Object.entries(rec.screens).map(([k, v]) => [k, { rect: v.dock.rect, in_vp: v.dock.in_viewport, hit: v.dock.hit_is_dock_or_child, styles: v.dock.styles, overlaps: (v.dock.overlapping_text || []).length, panel_after: v.after_click }])), null, 1));
  console.log("VERDICT", rec.verdict);
})();
