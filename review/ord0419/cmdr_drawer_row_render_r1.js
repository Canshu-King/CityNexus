/* CMDR ORD-0419 r1 -- what the drawer's nav rows actually render as, and whether they can be reached.
 *
 * Every claim is read out of getComputedStyle on the element after layout. No assertion here looks at
 * a class name or a data attribute: the defect being tested is precisely that a rule which "looks
 * applied" in the markup is not applied on screen. The current row is identified by its own visible
 * label (the route the shell is on), not by the class the CSS was supposed to style.
 *
 * Reachability follows the 口径 the commander set for this order, which is ORD-0338 甲 rewritten for a
 * scrolling container: a row is reachable when, after scrolling THE DRAWER'S OWN container so the row
 * is on screen, elementFromPoint(its centre) lands inside it. A centre sitting below the fold at
 * scroll 0 is therefore not a red -- "scrolled and still off-screen" is.
 *
 * The 15th button (the head row's Close) is recorded separately: widening `> button` to ` button`
 * reaches it too, and that exposure is reported rather than assumed harmless.
 *
 * Usage: node cmdr_drawer_row_render_r1.js <base> <out-dir> <label>
 */
const { chromium } = require("D:/moodle/CityNexus/frontend/node_modules/playwright");
const fs = require("fs");

const BASE = (process.argv[2] || "http://127.0.0.1:51313/").replace(/\/$/, "");
const OUT = process.argv[3] || "D:/moodle/_qoder_q_ord0419_20260929/probe/_render_r1/";
const LABEL = process.argv[4] || "unlabelled";
const SHAPES = [[390, 844], [360, 800], [414, 896], [320, 653]];
const LOCALES = ["zh-CN", "en"];
/* The global bare-element rule the rows fall back to (styles.css:47) -- the signature the before arm
   must reproduce and the after arm must not. */
const FALLBACK_BG = "rgb(66, 89, 216)";
const INTENDED_INK = "rgb(117, 129, 150)";   /* #758196, styles.css:331 */
/* The nav label of the route the shell is on, per arm: /v8/hub is Today. */
const CURRENT_LABEL = { "zh-CN": "今天", "en": "Today" };

async function readRows(page, locale) {
  return page.evaluate(({ fallbackBg, intendedInk, currentLabel }) => {
    const d = document.querySelector("#v8-nav-drawer");
    if (!d) return { present: false };
    const sig = (el) => {
      const cs = getComputedStyle(el);
      return { bg: cs.backgroundColor, color: cs.color, weight: cs.fontWeight,
               size: cs.fontSize, radius: cs.borderRadius, padding: cs.padding };
    };
    const head = d.querySelector(":scope > .v8-nav-drawer-head button");
    /* `:scope > div > button` also catches the head row's Close button, which is a different
       control with a different intended look -- it is read separately below. */
    const rows = Array.from(d.querySelectorAll(":scope > div:not(.v8-nav-drawer-head) > button"));
    const read = (b, i) => {
      const r = b.getBoundingClientRect();
      return { i, label: (b.innerText || "").trim().replace(/\s+/g, " "),
               sig: sig(b), box: [Math.round(r.width), Math.round(r.height)],
               centre: [Math.round(r.x + r.width / 2), Math.round(r.y + r.height / 2)],
               is_current: (b.innerText || "").trim() === currentLabel };
    };
    const out = rows.map(read);
    const hit = (el) => {
      const r = el.getBoundingClientRect();
      const c = [Math.round(r.x + r.width / 2), Math.round(r.y + r.height / 2)];
      const top = document.elementFromPoint(c[0], c[1]);
      return { centre: c, on_screen: c[1] >= 0 && c[1] <= window.innerHeight,
               hittable: !!(top && (top === el || el.contains(top))),
               top_el: top ? (top.tagName + (top.className ? "." + String(top.className).split(" ")[0] : "")) : null };
    };
    /* reachability, one row at a time: scroll the drawer's own container, then hit-test */
    const reach = [];
    for (const el of rows) {
      const before = hit(el);
      let after = before;
      const r = el.getBoundingClientRect();
      if (!before.hittable || !before.on_screen) {
        const target = d.scrollTop + (r.top - d.getBoundingClientRect().top)
          - (d.clientHeight / 2 - r.height / 2);
        d.scrollTop = Math.max(0, target);
        after = hit(el);
      }
      reach.push({ at_rest: before, after_scroll: after, drawer_scroll_top: Math.round(d.scrollTop),
                   reached: after.hittable });
      d.scrollTop = 0;
    }
    const distinct = Array.from(new Set(out.map((o) => JSON.stringify([o.sig.bg, o.sig.color, o.sig.weight]))));
    return {
      present: true, client_height: d.clientHeight, scroll_height: d.scrollHeight,
      overflow_px: d.scrollHeight - d.clientHeight,
      row_count: out.length, rows: out,
      signatures_distinct: distinct.length,
      rows_on_fallback_bg: out.filter((o) => o.sig.bg === fallbackBg).length,
      rows_on_intended_ink: out.filter((o) => o.sig.color === intendedInk).length,
      current_row: out.find((o) => o.is_current) || null,
      current_sig_unique: (() => {
        const c = out.find((o) => o.is_current);
        if (!c) return null;
        const key = JSON.stringify([c.sig.bg, c.sig.color, c.sig.weight]);
        return out.filter((o) => JSON.stringify([o.sig.bg, o.sig.color, o.sig.weight]) === key).length === 1;
      })(),
      head_close: head ? { label: (head.innerText || "").trim(), sig: sig(head) } : null,
      reachable_after_scroll: reach.filter((x) => x.reached).length,
      unreachable_rows: reach.map((x, i) => ({ x, i })).filter((o) => !o.x.reached).map((o) => o.i),
      reach_detail: reach.map((x, i) => ({ label: out[i].label, at_rest_hittable: x.at_rest.hittable,
                                            at_rest_on_screen: x.at_rest.on_screen,
                                            after_scroll_hittable: x.after_scroll.hittable,
                                            scrolled_top: x.drawer_scroll_top })),
    };
  }, { fallbackBg: FALLBACK_BG, intendedInk: INTENDED_INK, currentLabel: CURRENT_LABEL[locale] });
}

async function run(browser, shape, locale) {
  const [w, h] = shape;
  const page = await browser.newPage({ viewport: { width: w, height: h } });
  const errors = [];
  page.on("pageerror", (e) => errors.push(String(e).slice(0, 200)));
  const rec = { label: LABEL, shape: `${w}x${h}`, arm: locale, errors };
  try {
    await page.goto(`${BASE}/v8/hub`, { waitUntil: "networkidle", timeout: 60000 });
    const seal = page.getByText("使用封存的演示行程", { exact: false }).first();
    if (await seal.count()) { await seal.click(); await page.waitForTimeout(3200); }
    const lang = page.locator("[data-testid='topbar-language']").first();
    const offered = (await lang.innerText()).trim();
    if ((locale === "en") === (offered === "EN")) { await lang.click(); await page.waitForTimeout(1200); }
    await page.locator("[aria-controls='v8-nav-drawer']").first().click();
    await page.waitForTimeout(900);
    rec.reading = await readRows(page, locale);
    await page.screenshot({ path: `${OUT}${LABEL}_${w}x${h}_${locale}.png` });
  } catch (e) {
    rec.fatal = String(e).slice(0, 200);
  }
  rec.errors = errors;
  await page.close();
  const r = rec.reading || {};
  rec.verdict = {
    rows_off_fallback_bg: (r.rows_on_fallback_bg === 0),
    rows_on_intended_ink: (r.rows_on_intended_ink === (r.row_count || 0) - 1),
    current_sig_unique: !!r.current_sig_unique,
    all_reachable_after_scroll: (r.reachable_after_scroll === r.row_count),
  };
  const ok = Object.values(rec.verdict).every(Boolean);
  rec.pass = ok;
  console.log([LABEL, rec.shape, rec.arm, "rows=" + r.row_count, "fallback_bg=" + r.rows_on_fallback_bg,
               "intended_ink=" + r.rows_on_intended_ink, "sigs=" + r.signatures_distinct,
               "current_unique=" + r.current_sig_unique,
               "reachable=" + r.reachable_after_scroll + "/" + r.row_count, "overflow=" + r.overflow_px,
               "close_bg=" + (r.head_close ? r.head_close.sig.bg : "-"),
               "verdict=" + JSON.stringify(rec.verdict), ok ? "PASS" : "FAIL",
               rec.fatal ? "FATAL=" + rec.fatal.slice(0, 80) : ""].join(" "));
  return rec;
}

async function main() {
  fs.mkdirSync(OUT, { recursive: true });
  const browser = await chromium.launch({ channel: "chrome", headless: true });
  const results = [];
  for (const shape of SHAPES) for (const locale of LOCALES) results.push(await run(browser, shape, locale));
  const failing = results.filter((r) => !r.pass).length;
  fs.writeFileSync(`${OUT}${LABEL}.receipt.json`, JSON.stringify({
    at: new Date().toISOString(), base: BASE, label: LABEL,
    predicates: { fallback_bg: FALLBACK_BG, intended_ink: INTENDED_INK },
    cells: results.length, failing, results }, null, 1), "utf-8");
  console.log("%s cells=%d failing=%d -> %s", LABEL, results.length, failing, `${OUT}${LABEL}.receipt.json`);
  await browser.close();
  process.exit(LABEL === "before" ? 0 : (failing ? 3 : 0));
}
main().catch((e) => { console.log("FATAL", String(e).slice(0, 300)); process.exit(9); });
