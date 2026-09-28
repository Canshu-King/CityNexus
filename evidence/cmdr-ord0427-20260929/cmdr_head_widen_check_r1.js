/* CMDR ORD-0427 premise instrument r1 - the ORD-0419 selector widening also captured the head row.
 * Lane 2d2d7428 reported this and asked me to rule; this is my own independent reading, taken as a
 * before/after PAIR on one instrument so the two bases cannot drift apart:
 *   before = the tip ORD-0419 was cut from (my :4805 stage)
 *   after  = the tip with ORD-0419 landed       (my :4806 stage)
 * Wrap detection uses Range.getClientRects().length over the kicker's own text nodes, NOT the element
 * height: my first attempt judged "lines" from height/line-height and called a visibly two-line kicker
 * "1 line" (line-height computes to `normal`, so the division never happened).  A wrapped inline run
 * always yields more than one client rect, which is what this records.
 * Usage: node cmdr_head_widen_check_r1.js <before-base> <after-base> <out-file>
 */
const { chromium } = require("D:/moodle/CityNexus/frontend/node_modules/playwright");
const fs = require("fs");

const BEFORE = process.argv[2] || "http://127.0.0.1:4805/";
const AFTER = process.argv[3] || "http://127.0.0.1:4806/";
const OUT = process.argv[4] || "D:/moodle/_qoder_cmdr_ref_20260921/live_checks/_head_widen_r1.json";
const SHAPES = [[390, 844], [320, 653]];

async function read(browser, base, w, h) {
  const ctx = await browser.newContext({ viewport: { width: w, height: h }, hasTouch: true, locale: "zh" });
  const page = await ctx.newPage();
  const out = { base, entryAssets: null, sealClicked: null };
  try {
    await page.goto(base, { waitUntil: "networkidle", timeout: 90000 });
    out.entryAssets = await page.evaluate(() =>
      Array.from(document.querySelectorAll('script[src*="assets/index-"]')).map((s) => s.getAttribute("src")));
    for (const cand of [page.getByText("使用封存的演示行程", { exact: false }).first(),
                        page.getByText(/sealed demo trip/i).first()]) {
      if (await cand.count()) {
        out.sealClicked = (await cand.textContent() || "").trim().slice(0, 40);
        await cand.click();
        await page.waitForTimeout(4000);
        break;
      }
    }
    const ham = page.locator('[aria-controls="v8-nav-drawer"]');
    if (await ham.count()) { await ham.first().click(); await page.waitForTimeout(1000); }
    Object.assign(out, await page.evaluate(() => {
      const d = document.querySelector("#v8-nav-drawer");
      if (!d) return { error: "DRAWER_NOT_FOUND" };
      const head = d.querySelector(".v8-nav-drawer-head");
      const kick = head.querySelector(".v8-kicker");
      const close = head.querySelector("button");
      const cr = close.getBoundingClientRect();
      const kr = kick.getBoundingClientRect();
      const rng = document.createRange();
      rng.selectNodeContents(kick);
      const cs = getComputedStyle(close);
      const rows = Array.from(d.querySelectorAll("button")).filter((x) => x.querySelector("svg"));
      const sig = (x) => { const q = getComputedStyle(x); return [q.backgroundColor, q.color, q.fontSize].join(" | "); };
      const rowSigs = rows.map(sig);
      return {
        closeWidthPx: Math.round(cr.width),
        closeColor: cs.color,
        closeFontSize: cs.fontSize,
        kickerText: (kick.textContent || "").trim(),
        kickerWidthPx: Math.round(kr.width),
        kickerHeightPx: Math.round(kr.height),
        kickerClientRects: rng.getClientRects().length,
        headRowHeightPx: Math.round(head.getBoundingClientRect().height),
        navRows: rows.length,
        distinctRowSignatures: Array.from(new Set(rowSigs)).length,
        rowSignatureList: Array.from(new Set(rowSigs)),
      };
    }));
  } finally {
    await ctx.close();
  }
  return out;
}

async function main() {
  const browser = await chromium.launch({ channel: "chrome", headless: true });
  const report = { instrument: "cmdr_head_widen_check_r1", shapes: {} };
  for (const [w, h] of SHAPES) {
    const key = `${w}x${h}`;
    report.shapes[key] = { before: await read(browser, BEFORE, w, h), after: await read(browser, AFTER, w, h) };
    const b = report.shapes[key].before, a = report.shapes[key].after;
    report.shapes[key].delta = {
      closeWidthPx: (a.closeWidthPx || 0) - (b.closeWidthPx || 0),
      kickerWrappedBefore: (b.kickerClientRects || 0) > 1,
      kickerWrappedAfter: (a.kickerClientRects || 0) > 1,
      closeStyleChanged: b.closeColor !== a.closeColor || b.closeFontSize !== a.closeFontSize,
      rowSignaturesSplitAfter: (a.distinctRowSignatures || 0) > 1,
    };
  }
  await browser.close();
  fs.writeFileSync(OUT, JSON.stringify(report, null, 2));
  console.log(JSON.stringify({ out: OUT, shapes: Object.fromEntries(Object.entries(report.shapes).map(([k, v]) => [k, v.delta])) }, null, 2));
}

main().catch((e) => { console.error("FATAL", e); process.exit(1); });
