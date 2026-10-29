import { chromium } from "file:///D:/moodle/_cmdr_rescue_v3_1022/frontend/node_modules/playwright/index.mjs";
import fs from "node:fs";
const BASE = "http://127.0.0.1:14492";
const OUT = "D:/moodle/_cmdr_rescue_v3_1022/trial/results/20261022_v3_human_chrome";
const lines = [];
const note = (v) => { lines.push(v); fs.writeFileSync(OUT + "/clockstrip-1.txt", lines.join("\n") + "\n", "utf8"); };
const browser = await chromium.launch({ headless: true });
const ctx = await browser.newContext({ viewport: { width: 390, height: 844 }, deviceScaleFactor: 1 });
await ctx.addInitScript(() => {
  if (!sessionStorage.getItem("__probe_booted")) {
    localStorage.clear();
    sessionStorage.clear();
    sessionStorage.setItem("__probe_booted", "1");
  }
});
const page = await ctx.newPage();
const errors = [];
page.on("pageerror", (e) => errors.push(String(e).slice(0, 160)));
await page.goto(BASE + "/revolution", { waitUntil: "networkidle", timeout: 45000 }).catch(() => {});
await page.waitForTimeout(1200);
await page.locator('[data-testid="rev-mobile-tab-trips"]').click().catch(() => {});
await page.waitForTimeout(1000);
await page.locator('[data-testid="rev-demo-session"]').click().catch(() => {});
await page.waitForTimeout(3500);
const strip = page.locator('[data-testid="rev-classroom-clock"]');
note("STRIP_VISIBLE " + JSON.stringify(await strip.isVisible().catch(() => false)));
await strip.scrollIntoViewIfNeeded().catch(() => {});
note("BEFORE " + JSON.stringify(await page.locator('[data-testid="rev-clock-virtual"]').innerText().catch(() => "")));
await page.locator('[data-testid="rev-clock-plus60"]').click().catch(() => {});
await page.waitForTimeout(2000);
note("AFTER " + JSON.stringify(await page.locator('[data-testid="rev-clock-virtual"]').innerText().catch(() => "")));
await page.reload({ waitUntil: "networkidle" }).catch(() => {});
await page.waitForTimeout(2500);
await page.locator('[data-testid="rev-classroom-clock"]').scrollIntoViewIfNeeded().catch(() => {});
note("RELOADED " + JSON.stringify(await page.locator('[data-testid="rev-clock-virtual"]').innerText().catch(() => "")));
note("ERRORS " + JSON.stringify(errors));
await page.screenshot({ path: OUT + "/clockstrip-390.png" });
await browser.close();
