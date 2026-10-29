import { chromium } from "file:///D:/moodle/_cmdr_rescue_v3_1022/frontend/node_modules/playwright/index.mjs";
import fs from "node:fs";
const BASE = "http://127.0.0.1:14492";
const OUT = "D:/moodle/_cmdr_rescue_v3_1022/trial/results/20261022_v3_human_chrome";
const NL = String.fromCharCode(10);
const lines = [];
const note = (v) => { lines.push(v); fs.writeFileSync(OUT + "/classroom-day-boundary-13.txt", lines.join(NL) + NL, "utf8"); };
const browser = await chromium.launch({ headless: true });
const ctx = await browser.newContext({ viewport: { width: 430, height: 932 }, deviceScaleFactor: 1 });
await ctx.addInitScript(() => {
  if (!sessionStorage.getItem("__probe_booted")) { localStorage.clear(); sessionStorage.clear(); sessionStorage.setItem("__probe_booted", "1"); }
});
const page = await ctx.newPage();
const errors = [];
page.on("pageerror", (e) => errors.push(String(e).slice(0, 160)));
await page.goto(BASE + "/revolution", { waitUntil: "networkidle", timeout: 45000 }).catch(() => {});
await page.waitForTimeout(1200);
await page.locator('[data-testid="rev-mobile-tab-trips"]').click(); await page.waitForTimeout(1000);
await page.locator('[data-testid="rev-demo-session"]').click(); await page.waitForTimeout(3200);
const strip = page.locator('[data-testid="rev-classroom-clock"]');
await strip.scrollIntoViewIfNeeded().catch(() => {});
note("BEFORE " + JSON.stringify(await strip.innerText().catch(() => "")));
await page.locator('[data-testid="rev-clock-next"]').click();
await page.waitForTimeout(6000);
note("NOTE " + JSON.stringify(await page.locator('[data-testid="rev-clock-next-note"]').innerText().catch(() => "")));
note("AFTER " + JSON.stringify(await strip.innerText().catch(() => "")));
await page.screenshot({ path: OUT + "/rehearsal13-day2.png" });
await page.reload({ waitUntil: "networkidle", timeout: 45000 }).catch(() => {});
await page.waitForTimeout(2600);
if (!(await strip.count())) {
  await page.locator('[data-testid="rev-mobile-tab-trips"]').click().catch(() => {});
  await page.waitForTimeout(800);
  await page.locator('[data-testid="rev-demo-session"]').click().catch(() => {});
  await page.waitForTimeout(2600);
}
note("RELOAD " + JSON.stringify(await strip.innerText().catch(() => "")));
note("ERRORS " + JSON.stringify(errors.slice(0, 5)));
await browser.close();
