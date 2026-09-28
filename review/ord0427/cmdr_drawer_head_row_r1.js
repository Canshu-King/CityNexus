/* CMDR ORD-0427 r1 -- one file per cell (four shapes x two arms), both dimensions read at once.
 *
 * The commander's own cmdr_head_widen_check_r1.js covers two shapes and the zh arm in a single pair
 * file; ORD-0427 asks for four shapes x two arms with one evidence file per cell, so this instrument
 * reads the same two dimensions per cell and writes them separately:
 *   dimension 1 (the 14 nav rows)  -- must keep the ORD-0419 shape: 13 rows on transparent background
 *                                     with rgb(117, 129, 150) ink, and exactly one current row on the
 *                                     rgb(241, 243, 255) pill.
 *   dimension 2 (the head row)     -- the Close button must be back to its pre-0419 computed values and
 *                                     the kicker must yield ONE client rect again. Wrap detection is
 *                                     Range.getClientRects().length over the kicker's own contents, not
 *                                     a height division (the commander's own first version got that
 *                                     wrong, and .v8-kicker's line-height computes to `normal`).
 * Everything is read from the rendered tree; no class or data attribute is asserted.
 *
 * Usage: node cmdr_drawer_head_row_r1.js <base> <out-dir> <label>
 */
const { chromium } = require("D:/moodle/CityNexus/frontend/node_modules/playwright");
const fs = require("fs");

const BASE = (process.argv[2] || "http://127.0.0.1:4799/").replace(/\/$/, "");
const OUT = process.argv[3] || "D:/moodle/_qoder_q_ord0427_20260929/probe/_cells/";
const LABEL = process.argv[4] || "cand";
const SHAPES = [[390, 844], [360, 800], [414, 896], [320, 653]];
const ARMS = ["zh-CN", "en"];

async function read(page) {
  return page.evaluate(() => {
    const d = document.querySelector("#v8-nav-drawer");
    if (!d) return { present: false };
    const sig = (x) => { const q = getComputedStyle(x); return {
      bg: q.backgroundColor, color: q.color, weight: q.fontWeight, size: q.fontSize,
      radius: q.borderRadius, padding: q.padding, height: Math.round(x.getBoundingClientRect().height) }; };
    const head = d.querySelector(".v8-nav-drawer-head");
    const kick = head ? head.querySelector(".v8-kicker") : null;
    const close = head ? head.querySelector("button") : null;
    const rng = document.createRange();
    if (kick) rng.selectNodeContents(kick);
    const rows = Array.from(d.querySelectorAll("button")).filter((b) => b.querySelector("svg"));
    const rowSigs = rows.map((b) => ({ label: (b.innerText || "").trim().replace(/\s+/g, " "), ...sig(b) }));
    const TRANSPARENT = "rgba(0, 0, 0, 0)";
    const INK = "rgb(117, 129, 150)";
    const PILL = "rgb(241, 243, 255)";
    const svg = rows[0] ? rows[0].querySelector("svg").getBoundingClientRect() : null;
    return {
      present: true,
      rows: rowSigs.length,
      rows_plain: rowSigs.filter((r) => r.bg === TRANSPARENT && r.color === INK).length,
      rows_pill: rowSigs.filter((r) => r.bg === PILL).length,
      pill_label: (rowSigs.find((r) => r.bg === PILL) || {}).label || null,
      row_height: rowSigs.length ? rowSigs[0].height : null,
      icon_box: svg ? [Math.round(svg.width), Math.round(svg.height)] : null,
      drawer_scroll: d.scrollHeight, drawer_client: d.clientHeight,
      head: {
        close_label: close ? (close.textContent || "").trim() : null,
        close_width: close ? Math.round(close.getBoundingClientRect().width) : null,
        close_box: close ? [Math.round(close.getBoundingClientRect().x), Math.round(close.getBoundingClientRect().y),
                            Math.round(close.getBoundingClientRect().width), Math.round(close.getBoundingClientRect().height)] : null,
        close_sig: close ? sig(close) : null,
        kicker_text: kick ? (kick.textContent || "").trim() : null,
        kicker_width: kick ? Math.round(kick.getBoundingClientRect().width) : null,
        kicker_height: kick ? Math.round(kick.getBoundingClientRect().height) : null,
        kicker_client_rects: kick ? rng.getClientRects().length : null,
        head_row_height: head ? Math.round(head.getBoundingClientRect().height) : null,
      },
    };
  });
}

async function main() {
  fs.mkdirSync(OUT, { recursive: true });
  const browser = await chromium.launch({ channel: "chrome", headless: true });
  const written = [];
  for (const [w, h] of SHAPES) for (const arm of ARMS) {
    const ctx = await browser.newContext({ viewport: { width: w, height: h }, hasTouch: true, locale: arm });
    const page = await ctx.newPage();
    const errors = [];
    page.on("pageerror", (e) => errors.push(String(e).slice(0, 200)));
    const rec = { label: LABEL, base: BASE, shape: `${w}x${h}`, arm, errors };
    try {
      await page.goto(BASE, { waitUntil: "networkidle", timeout: 90000 });
      rec.entryAssets = await page.evaluate(() =>
        Array.from(document.querySelectorAll('script[src*="assets/index-"]')).map((s) => s.getAttribute("src")));
      for (const cand of [page.getByText("使用封存的演示行程", { exact: false }).first(),
                          page.getByText(/sealed demo trip/i).first()]) {
        if (await cand.count()) { rec.sealClicked = (await cand.textContent() || "").trim().slice(0, 40);
          await cand.click(); await page.waitForTimeout(4000); break; }
      }
      const ham = page.locator('[aria-controls="v8-nav-drawer"]');
      if (await ham.count()) { await ham.first().click(); await page.waitForTimeout(1000); }
      rec.reading = await read(page);
      rec.kicker_text_read = rec.reading.head ? rec.reading.head.kicker_text : null;
      await page.screenshot({ path: `${OUT}${LABEL}_${w}x${h}_${arm}.png` });
    } catch (e) {
      rec.fatal = String(e).slice(0, 200);
    }
    const file = `${OUT}${LABEL}_${w}x${h}_${arm}.json`;
    fs.writeFileSync(file, JSON.stringify(rec, null, 1), "utf-8");
    written.push(file);
    const r = rec.reading || {};
    console.log("%s %sx%s %-5s rows=%s plain=%s pill=%s(%s) icon=%s head_close_w=%s close_color=%s close_size=%s kicker_rects=%s kicker=%s%s",
                LABEL, w, h, arm, r.rows, r.rows_plain, r.rows_pill, r.pill_label, JSON.stringify(r.icon_box),
                r.head && r.head.close_width, r.head && r.head.close_sig && r.head.close_sig.color,
                r.head && r.head.close_sig && r.head.close_sig.size, r.head && r.head.kicker_client_rects,
                JSON.stringify(r.head && r.head.kicker_text), rec.fatal ? " FATAL=" + rec.fatal.slice(0, 60) : "");
    await ctx.close();
  }
  await browser.close();
  console.log("wrote %d per-cell files under %s", written.length, OUT);
}
main().catch((e) => { console.log("FATAL", String(e).slice(0, 300)); process.exit(9); });
