/* ORD-0417 lane geometry census r1 -- what the new glass band costs, on a served dist.
 *
 * The 口径 is lane N3's, frozen in `review/n3_0407_evidence_r1/controls_before_79ca877c.json`
 * (blob 5bd1fe669a1a7f9fbcae4c9d63852969983650ae): every control in
 * `button, a[href], input, select, textarea, [role=button], [data-testid=pretrip-empty-action]`,
 * identity by (testid, else name + n-th of that name), reachable = `elementFromPoint` at the control's
 * own centre returns it (or one of its descendants) AND centre.y <= 768 AND the centre is inside the
 * viewport.  This runs the same reading twice on the same scroll offset, once with nothing selected
 * and once with the glass band painted, and it runs on both the tip's dist and this lane's dist, so
 * the cost is a diff between two receipts rather than a claim.
 *
 * It is deliberately not the acceptance gate.  The gate lives in `frontend/e2e/` and asserts; this
 * instrument only measures, so a number can be published that the gate's own green cannot explain.
 *
 * usage: node ord0417_geometry_census_r1.js <base> <out-dir> <label>
 */
const { chromium } = require("D:/moodle/CityNexus/frontend/node_modules/playwright");
const fs = require("fs");

const BASE = (process.argv[2] || "http://127.0.0.1:4832/").replace(/\/$/, "");
const OUT = process.argv[3] || ".";
const LABEL = process.argv[4] || "unlabelled";
const FLOOR = 768;
const SHAPES = [[390, 844], [360, 800], [320, 653], [414, 896]];
const LOCALES = ["zh-CN", "en"];

const CENSUS = (floor) => {
  const sel = "button, a[href], input, select, textarea, [role=button], [data-testid=pretrip-empty-action]";
  const seen = {};
  const controls = Array.from(document.querySelectorAll(sel)).map((el) => {
    const r = el.getBoundingClientRect();
    if (r.width === 0 || r.height === 0) return null;
    const cx = Math.round(r.left + r.width / 2);
    const cy = Math.round(r.top + r.height / 2);
    const hit = document.elementFromPoint(cx, cy);
    const text = (el.textContent ?? "").replace(/\s+/g, " ").trim().slice(0, 60);
    const testid = el.getAttribute("data-testid");
    const name = text || el.getAttribute("aria-label") || el.getAttribute("placeholder") || "(no label)";
    const bare = testid ?? name;
    seen[bare] = (seen[bare] ?? 0) + 1;
    return {
      key: testid ?? `${name}#${seen[bare]}`,
      name,
      centre: [cx, cy],
      in_viewport: cy >= 0 && cy <= window.innerHeight,
      above_floor: cy <= floor,
      hit_test: !!hit && (hit === el || el.contains(hit) || hit.contains(el)),
    };
  }).filter((x) => x !== null);

  const band = document.querySelector(".v8-map-overlay-stack");
  const bb = band && band.getBoundingClientRect();
  const pins = Array.from(document.querySelectorAll(".v8-map-panel .v9-map-marker"))
    .filter((el) => el.getAttribute("role") === "button")
    .map((el) => {
      const r = el.getBoundingClientRect();
      const cx = Math.round(r.x + r.width / 2);
      const cy = Math.round(r.y + r.height / 2);
      const top = document.elementFromPoint(cx, cy);
      const ov = bb
        ? Math.max(0, Math.min(bb.right, r.right) - Math.max(bb.left, r.left)) *
          Math.max(0, Math.min(bb.bottom, r.bottom) - Math.max(bb.top, r.top))
        : 0;
      return {
        painted: (el.textContent ?? "").trim(),
        aria: el.getAttribute("aria-label") ?? "",
        title_attr: el.getAttribute("title"),
        centre: [cx, cy],
        lands: !!top && (top === el || el.contains(top)),
        covered_px2: Math.round(ov),
      };
    });
  const glass = document.querySelector(".v8-map-panel .v8-map-selected-stop");
  const gr = glass && glass.getBoundingClientRect();
  const cs = glass && getComputedStyle(glass);
  return {
    lang: document.documentElement.lang || null,
    scroll_y: Math.round(window.scrollY),
    inner: [window.innerWidth, window.innerHeight],
    controls,
    band_box: bb ? [Math.round(bb.x), Math.round(bb.y), Math.round(bb.width), Math.round(bb.height)] : null,
    pins,
    glass: glass
      ? {
          painted: (glass.innerText ?? "").replace(/\s+/g, " ").trim(),
          box: gr ? [Math.round(gr.x), Math.round(gr.y), Math.round(gr.width), Math.round(gr.height)] : null,
          display: cs.display,
          visibility: cs.visibility,
          opacity: Number(cs.opacity),
        }
      : null,
  };
};

const reachable = (c) => c.controls.filter((x) => x.hit_test && x.above_floor && x.in_viewport).map((x) => x.key);

async function arm(browser, w, h, locale) {
  const page = await browser.newPage({ viewport: { width: w, height: h } });
  const errors = [];
  page.on("pageerror", (e) => errors.push(String(e).slice(0, 200)));
  const rec = { label: LABEL, shape: `${w}x${h}`, arm: locale, hit_floor_px: FLOOR, base: BASE, errors };
  try {
    await page.goto(BASE + "/v8/map", { waitUntil: "networkidle", timeout: 60000 });
    const seal = page.getByText("使用封存的演示行程", { exact: false }).first();
    if (await seal.count()) { await seal.click(); await page.waitForTimeout(5000); }
    /* the language is the product's own stored choice; reload makes the app re-read it */
    await page.evaluate((l) => localStorage.setItem("citynexus.locale", l), locale);
    await page.reload({ waitUntil: "networkidle" });
    const seal2 = page.getByText("使用封存的演示行程", { exact: false }).first();
    if (await seal2.count()) { await seal2.click(); await page.waitForTimeout(5000); }
    await page.waitForTimeout(1200);

    const idle = await page.evaluate(CENSUS, FLOOR);
    const hittable = idle.pins.filter((p) => p.lands && p.aria);
    rec.pins_total = idle.pins.length;
    rec.pins_individually_hittable = hittable.length;
    rec.pins_co_located = idle.pins.filter((p) => !p.lands).map((p) => ({ painted: p.painted, centre: p.centre }));
    if (!hittable.length) {
      rec.fatal = "no pin answers a hit-test at its own centre";
      rec.idle = idle;
      await page.close();
      return rec;
    }
    const target = hittable[Math.min(1, hittable.length - 1)];
    rec.tapped = { painted: target.painted, aria: target.aria, centre: target.centre };
    await page.mouse.click(target.centre[0], target.centre[1]);
    await page.waitForTimeout(2000);
    const scrolled = await page.evaluate(() => Math.round(window.scrollY));
    await page.evaluate(() => window.scrollTo(0, 0));
    await page.waitForTimeout(900);
    const live = await page.evaluate(CENSUS, FLOOR);

    const before = reachable(idle);
    const afterKeys = new Set(reachable(live));
    const idleLands = new Set(idle.pins.filter((p) => p.lands).map((p) => p.painted));
    const idleCovered = new Map(idle.pins.map((p) => [p.painted, p.covered_px2]));
    const idleBelow = new Set(idle.pins.filter((p) => p.centre[1] > FLOOR).map((p) => p.painted));

    rec.autoscroll_to_card_px = scrolled;
    rec.controls_idle = idle.controls.length;
    rec.controls_with_band = live.controls.length;
    rec.reachable_idle = before.length;
    rec.reachable_with_band = afterKeys.size;
    rec.lost_reachable = before.filter((k) => !afterKeys.has(k));
    rec.band_box_idle = idle.band_box;
    rec.band_box_with_band = live.band_box;
    rec.band_growth_px = idle.band_box && live.band_box ? live.band_box[3] - idle.band_box[3] : null;
    rec.glass = live.glass;
    rec.newly_covered_pins = live.pins
      .filter((p) => (idleCovered.get(p.painted) ?? 0) === 0 && p.covered_px2 > 0)
      .map((p) => ({ painted: p.painted, aria: p.aria, px2: p.covered_px2 }));
    rec.newly_unhittable_pins = live.pins
      .filter((p) => idleLands.has(p.painted) && !p.lands)
      .map((p) => ({ painted: p.painted, centre: p.centre }));
    rec.newly_below_floor_pins = live.pins
      .filter((p) => p.centre[1] > FLOOR && !idleBelow.has(p.painted))
      .map((p) => ({ painted: p.painted, centre: p.centre }));
    rec.name_painted_on_glass = !!(live.glass && target.aria && live.glass.painted.includes(target.aria));
    rec.glass_visible = !!(live.glass && live.glass.display !== "none" && live.glass.visibility === "visible" && live.glass.opacity > 0 && live.glass.box && live.glass.box[2] > 40 && live.glass.box[3] > 0);
    rec.idle = idle;
    rec.live = live;
    await page.screenshot({ path: `${OUT}/${LABEL}_${w}x${h}_${locale}.png` });
  } catch (e) {
    rec.fatal = String(e).slice(0, 240);
  }
  await page.close();
  return rec;
}

(async () => {
  fs.mkdirSync(OUT, { recursive: true });
  const browser = await chromium.launch({ channel: "chrome", headless: true });
  const results = [];
  for (const [w, h] of SHAPES) for (const locale of LOCALES) results.push(await arm(browser, w, h, locale));
  await browser.close();
  const path = `${OUT}/${LABEL}.census.json`;
  fs.writeFileSync(path, JSON.stringify({ base: BASE, label: LABEL, hit_floor_px: FLOOR, shapes: SHAPES, arms: LOCALES, results }, null, 1), "utf-8");
  for (const r of results) {
    console.log(`${LABEL} ${r.shape} ${r.arm} pins=${r.pins_total} hittable=${r.pins_individually_hittable ?? "-"} tapped=${JSON.stringify((r.tapped || {}).aria)} controls ${r.controls_idle}->${r.controls_with_band} reachable ${r.reachable_idle}->${r.reachable_with_band} lost=${JSON.stringify(r.lost_reachable)} band_grew=${r.band_growth_px}px name_painted=${r.name_painted_on_glass} visible=${r.glass_visible} covered=${JSON.stringify(r.newly_covered_pins)} unhittable=${JSON.stringify(r.newly_unhittable_pins)} below=${JSON.stringify(r.newly_below_floor_pins)} err=${r.errors.length}${r.fatal ? " FATAL=" + r.fatal : ""}`);
  }
  console.log("wrote", path);
})().catch((e) => { console.log("FATAL", String(e).slice(0, 300)); process.exit(9); });
