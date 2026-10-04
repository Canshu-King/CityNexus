/* ORD-0553 r3 -- read the painted text of the three slots, per generation, in one state.
 *
 * The e2e that pins the button name is only interesting if both generations' button text is on record at
 * the SAME store state, so this reads the activity-status cells, the two state values and the footer
 * button verbatim.  No judgement here -- it prints what is painted; the block quotes it.
 * usage: node cmdra_0553_slot_text_r1.js <base> <out.json> <zh|en>
 */
const { chromium } = require("D:/moodle/CityNexus/frontend/node_modules/playwright");
const crypto = require("crypto");
const fs = require("fs");

const BASE = process.argv[2];
const OUT = process.argv[3];
const LOCALE = process.argv[4] || "en";

async function main() {
  const browser = await chromium.launch({ channel: "chrome", headless: true });
  const ctx = await browser.newContext({ viewport: { width: 390, height: 844 }, hasTouch: true, locale: LOCALE });
  const page = await ctx.newPage();
  const pageErrors = [];
  page.on("pageerror", (e) => pageErrors.push(String(e).slice(0, 160)));
  await page.goto(BASE, { waitUntil: "networkidle", timeout: 90000 });
  const entry = await page.evaluate(() =>
    Array.from(document.querySelectorAll('script[src*="assets/index-"]')).map((s) => s.getAttribute("src")));
  for (const cand of [page.getByText("使用封存的演示行程", { exact: false }).first(),
                      page.getByText(/sealed demo trip/i).first()]) {
    if (await cand.count()) { await cand.click(); await page.waitForTimeout(4500); break; }
  }
  await page.goto(BASE.replace(/\/$/, "") + "/v8/authoritative", { waitUntil: "domcontentloaded", timeout: 60000 });
  await page.waitForTimeout(3000);
  const read = await page.evaluate(() => {
    const texts = (sel) => Array.from(document.querySelectorAll(sel))
      .map((e) => (e.textContent || "").replace(/\s+/g, " ").trim());
    const rows = Array.from(document.querySelectorAll(".v12-activity-row")).map((r) => ({
      title: (r.querySelector(".v12-activity-title") || {}).textContent || "",
      status: (r.querySelector(".v12-activity-status") || {}).textContent || "",
    }));
    const nowCard = document.querySelector(".v12-state-card.now");
    const nextCard = document.querySelector(".v12-state-card.next");
    return {
      panelPresent: Boolean(document.querySelector('[data-testid="v12-authoritative-panel"]')),
      activityStatus: texts(".v12-activity-status"),
      stateValues: texts(".v12-state-value"),
      footerButton: texts(".v12-panel-footer button"),
      rows,
      nowTitle: nowCard ? (nowCard.querySelector("strong") || {}).textContent : null,
      nextTitle: nextCard ? (nextCard.querySelector("strong") || {}).textContent : null,
    };
  });
  const report = {
    instrument: "cmdra_0553_slot_text_r1",
    script_sha256: crypto.createHash("sha256").update(fs.readFileSync(__filename)).digest("hex"),
    base: BASE, locale: LOCALE, entryAssets: entry, viewport: "390x844", read, pageErrors,
  };
  fs.writeFileSync(OUT, JSON.stringify(report, null, 2));
  await ctx.close();
  await browser.close();
  console.log(JSON.stringify({ out: OUT, entry, footerButton: read.footerButton,
    stateValues: read.stateValues, activityStatus: read.activityStatus,
    rows: read.rows.map((r) => r.title + "=" + r.status), pageErrors: pageErrors.length }, null, 2));
}
main().catch((e) => { console.error("FATAL", e); process.exit(1); });
