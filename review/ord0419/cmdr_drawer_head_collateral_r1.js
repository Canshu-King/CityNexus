/* CMDR ORD-0419 collateral probe r1 -- the head row of the drawer, measured in three states.
 *
 * Widening `#v8-nav-drawer > button` to `#v8-nav-drawer button` (which is what ORD-0419 asks for, and
 * what makes the 14 nav rows render as their own design instead of the global blue button) also reaches
 * a 15th button: the head row's Close. This instrument measures that exposure rather than asserting it:
 *   before  -- the tip build, where the nav rows are wrong and the head is as authored;
 *   after   -- this branch's build;
 *   after + the narrow rule restated for the head button only (a runtime probe on MY browser, 0 product
 *            bytes), which is what the alternative selector `div:not(.v8-nav-drawer-head) > button`
 *            would do, so the commander can choose with numbers.
 *
 * Usage: node cmdr_drawer_head_collateral_r1.js <base> <out-dir> <label> [--probe]
 */
const { chromium } = require("D:/moodle/CityNexus/frontend/node_modules/playwright");
const fs = require("fs");

const BASE = (process.argv[2] || "http://127.0.0.1:64920/").replace(/\/$/, "");
const OUT = process.argv[3] || "D:/moodle/_qoder_q_ord0419_20260929/probe/_head_r1/";
const LABEL = process.argv[4] || "after";
const PROBE = process.argv.includes("--probe");
/* The head button's own authored intent, from `.v8-quiet-button` (styles.css:167). */
const NARROW = "#v8-nav-drawer .v8-nav-drawer-head button {"
  + " width: auto; padding: 5px 0; border-radius: 0; font-size: 12px; font-weight: 750;"
  + " color: var(--v8-indigo); background: transparent; }";

async function read(page) {
  return page.evaluate(() => {
    const h = document.querySelector(".v8-nav-drawer-head");
    const kick = h.querySelector(".v8-kicker"), btn = h.querySelector("button");
    const box = (e) => { const q = e.getBoundingClientRect(); return [Math.round(q.x), Math.round(q.y), Math.round(q.width), Math.round(q.height)]; };
    const cs = getComputedStyle(btn);
    const rows = Array.from(document.querySelectorAll("#v8-nav-drawer > div:not(.v8-nav-drawer-head) > button"));
    const sigs = Array.from(new Set(rows.map((b) => { const c = getComputedStyle(b);
      return JSON.stringify([c.backgroundColor, c.color, c.fontWeight]); })));
    return { head_box: box(h), kicker_box: box(kick), close_box: box(btn),
             close_share_of_head_pct: Math.round(100 * box(btn)[2] / box(h)[2]),
             kicker_wraps: box(kick)[3] > 20,
             close: { bg: cs.backgroundColor, color: cs.color, weight: cs.fontWeight, size: cs.fontSize,
                      padding: cs.padding, radius: cs.borderRadius },
             row_count: rows.length, row_signatures: sigs.length };
  });
}

/* A second base is passed as a URL, not a port: the before and after builds are served by two
   different preview processes on unrelated ports, and neither port tells you which one it is. */
const BASES = (process.env.CNX_BASES || BASE).split(",").map((s) => s.replace(/\/$/, ""));

async function main() {
  fs.mkdirSync(OUT, { recursive: true });
  const browser = await chromium.launch({ channel: "chrome", headless: true });
  const states = [];
  for (const target of BASES) {
    const page = await browser.newPage({ viewport: { width: 390, height: 844 } });
    await page.goto(`${target}/v8/hub`, { waitUntil: "networkidle", timeout: 60000 });
    const seal = page.getByText("使用封存的演示行程", { exact: false }).first();
    if (await seal.count()) { await seal.click(); await page.waitForTimeout(3200); }
    await page.locator("[aria-controls='v8-nav-drawer']").first().click();
    await page.waitForTimeout(900);
    const before = await read(page);
    let probed = null;
    if (PROBE) {
      await page.addStyleTag({ content: NARROW });
      await page.waitForTimeout(400);
      probed = await read(page);
      await page.screenshot({ path: `${OUT}${LABEL}_${target.replace(/[^0-9]/g, "")}_with_narrow_probe.png` });
    }
    states.push({ state: LABEL, target, reading: before, narrow_probe: probed,
                  probe_rule: PROBE ? NARROW : null,
                  probe_scope: PROBE ? "style added to this browser session only; no file changed" : null });
    await page.close();
  }
  fs.writeFileSync(`${OUT}${LABEL}.receipt.json`, JSON.stringify(
    { at: new Date().toISOString(), base: BASE, states }, null, 1), "utf-8");
  for (const s of states) {
    console.log("%s :%s close_box=%s share=%s%% kicker_wraps=%s rows=%s sigs=%s | probe close=%s share=%s%% wraps=%s sigs=%s",
                s.state, s.target, JSON.stringify(s.reading.close_box), s.reading.close_share_of_head_pct,
                s.reading.kicker_wraps, s.reading.row_count, s.reading.row_signatures,
                s.narrow_probe ? JSON.stringify(s.narrow_probe.close_box) : "-",
                s.narrow_probe ? s.narrow_probe.close_share_of_head_pct : "-",
                s.narrow_probe ? s.narrow_probe.kicker_wraps : "-",
                s.narrow_probe ? s.narrow_probe.row_signatures : "-");
  }
  await browser.close();
}
main().catch((e) => { console.log("FATAL", String(e).slice(0, 300)); process.exit(9); });
