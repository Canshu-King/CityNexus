/* CMDR ORD-0413 cause probe r1 -- why the drawer is 4,512 px tall, measured, and what a one-selector
 * correction would cost. No product byte is touched: the correction is injected into the live DOM of MY
 * browser session as a measurement probe, and the receipt says so on every row.
 *
 * The grouping instrument (cmdr_drawer_grouping_r1.js) found 14 nav rows occupying 4,512 px of scroll
 * height, i.e. ~310 px per row. A nav row that reads "今天" with a 17 px icon is not 310 px tall unless
 * something is wrong with the icon. styles.css carries
 *     #v8-nav-drawer > button svg { width: 17px; height: 17px }
 * but every button is wrapped in a <div> (the group heading sits in the same wrapper), so the child
 * combinator never matches and the <svg> -- which has a viewBox and no width/height attribute -- falls
 * back to the replaced-element default. This instrument reads that directly, then re-measures with the
 * descendant form of the same rule injected, so the proposal can quote a number instead of a hunch.
 *
 * Usage: node cmdr_drawer_cause_probe_r1.js <base> <out-dir>
 */
const { chromium } = require("D:/moodle/CityNexus/frontend/node_modules/playwright");
const fs = require("fs");

const BASE = (process.argv[2] || "http://127.0.0.1:50991/").replace(/\/$/, "");
const OUT = process.argv[3] || "D:/moodle/_qoder_q_ord0413_20260928/probe/_cause_r1/";
const FLOOR = 768;
const FIX = "#v8-nav-drawer button svg { width: 17px; height: 17px }";

async function measure(page) {
  return page.evaluate((floor) => {
    const d = document.querySelector("#v8-nav-drawer");
    if (!d) return { present: false };
    const items = Array.from(d.querySelectorAll(":scope > div > button"));
    const first = items[1];
    const svg = first ? first.querySelector("svg") : null;
    const cs = svg ? getComputedStyle(svg) : null;
    let directMatch = false;
    for (const sheet of document.styleSheets) {
      let rules;
      try { rules = sheet.cssRules; } catch (e) { continue; }
      for (const r of Array.from(rules || [])) {
        if (r.selectorText && r.selectorText.includes("#v8-nav-drawer > button svg")) {
          directMatch = !!(first && first.matches("#v8-nav-drawer > button"));
        }
      }
    }
    /* index 0 is the head row's Close button -- same wrapper shape, no icon, and not a nav entry. */
    const rows = items.slice(1).map((b) => {
      const r = b.getBoundingClientRect();
      const c = [Math.round(r.x + r.width / 2), Math.round(r.y + r.height / 2)];
      const top = document.elementFromPoint(c[0], c[1]);
      return { label: (b.innerText || "").trim().replace(/\s+/g, " "), h: Math.round(r.height),
               centre: c, hittable: !!(top && (b.contains(top) || b === top)),
               above_floor: c[1] <= floor };
    });
    return { present: true, scroll_height: d.scrollHeight, client_height: d.clientHeight,
             overflow_px: d.scrollHeight - d.clientHeight,
             rows: Math.max(items.length - 1, 0),
             row_height_min: Math.min(...rows.map((r) => r.h)), row_height_max: Math.max(...rows.map((r) => r.h)),
             rows_within_floor: rows.filter((r) => r.hittable && r.above_floor).length,
             svg_computed: cs ? [cs.width, cs.height] : null,
             svg_box: svg ? [Math.round(svg.getBoundingClientRect().width), Math.round(svg.getBoundingClientRect().height)] : null,
             svg_has_width_attr: svg ? svg.hasAttribute("width") : null,
             svg_viewbox: svg ? svg.getAttribute("viewBox") : null,
             child_selector_matches_a_real_row: directMatch,
             labels: rows.map((r) => r.label) };
  }, FLOOR);
}

async function arm(browser, locale) {
  const page = await browser.newPage({ viewport: { width: 390, height: 844 } });
  const errors = [];
  page.on("pageerror", (e) => errors.push(String(e).slice(0, 200)));
  const rec = { arm: locale };
  try {
    await page.goto(BASE + "/v8/hub", { waitUntil: "networkidle", timeout: 60000 });
    const seal = page.getByText("使用封存的演示行程", { exact: false }).first();
    if (await seal.count()) { await seal.click(); await page.waitForTimeout(3200); }
    const lang = page.locator("[data-testid='topbar-language']").first();
    const offered = (await lang.innerText()).trim();
    if ((locale === "en") === (offered === "EN")) { await lang.click(); await page.waitForTimeout(1200); }
    await page.locator("[aria-controls='v8-nav-drawer']").first().click();
    await page.waitForTimeout(900);
    rec.before = await measure(page);
    /* The probe: same document, one added style rule, nothing reloaded. This is a measurement of what
       the corrected selector would produce, not a deployed change -- the product tree is untouched. */
    await page.addStyleTag({ content: FIX });
    await page.waitForTimeout(500);
    rec.after_probe = await measure(page);
    rec.probe_rule = FIX;
    rec.probe_scope = "live DOM of this browser session only; no file in frontend/src was modified";
    await page.screenshot({ path: `${OUT}${locale}_after_probe.png` });
  } catch (e) {
    rec.fatal = String(e).slice(0, 200);
  }
  rec.errors = errors;
  await page.close();
  const b = rec.before || {}, a = rec.after_probe || {};
  console.log("%s scroll %s->%s  overflow %s->%s  rows %s  row_h %s..%s -> %s..%s  rows_within_floor %s->%s  svg %s -> %s  child_selector_matches=%s",
              locale, b.scroll_height, a.scroll_height, b.overflow_px, a.overflow_px, b.rows,
              b.row_height_min, b.row_height_max, a.row_height_min, a.row_height_max,
              b.rows_within_floor, a.rows_within_floor, JSON.stringify(b.svg_box), JSON.stringify(a.svg_box),
              b.child_selector_matches_a_real_row);
  return rec;
}

async function main() {
  fs.mkdirSync(OUT, { recursive: true });
  const browser = await chromium.launch({ channel: "chrome", headless: true });
  const results = [];
  for (const locale of ["zh-CN", "en"]) results.push(await arm(browser, locale));
  fs.writeFileSync(`${OUT}receipt.json`, JSON.stringify({
    at: new Date().toISOString(), base: BASE, hit_floor_px: FLOOR, results }, null, 1), "utf-8");
  await browser.close();
}
main().catch((e) => { console.log("FATAL", String(e).slice(0, 300)); process.exit(9); });
