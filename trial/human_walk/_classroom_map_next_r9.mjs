import { chromium } from "file:///D:/moodle/_cmdr_rescue_v3_1022/frontend/node_modules/playwright/index.mjs";
import fs from "node:fs";
const BASE = "http://127.0.0.1:14492";
const OUT = "D:/moodle/_cmdr_rescue_v3_1022/trial/results/20261022_v3_human_chrome";
const NL = String.fromCharCode(10);
const lines = [];
const note = (v) => { lines.push(v); fs.writeFileSync(OUT + "/classroom-map-next-9.txt", lines.join(NL) + NL, "utf8"); };
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
await page.locator('[data-testid="rev-clock-next"]').click();
await page.waitForTimeout(4500);
note("STATION_AFTER " + JSON.stringify(await page.locator('[data-testid="rev-classroom-clock"]').innerText().catch(() => "")));
await page.getByRole("button", { name: "地图", exact: true }).first().click().catch(() => {});
await page.waitForTimeout(900);
await page.getByRole("button", { name: /加载地图/ }).first().click().catch(() => {});
let dot = false;
for (let i = 0; i < 15; i++) { dot = await page.locator('[data-testid="rev-map-traveller"]').isVisible().catch(() => false); if (dot) break; await page.waitForTimeout(1000); }
note("BLUE_DOT " + JSON.stringify(dot));
note("DOT_STATE " + JSON.stringify(await page.locator('[data-testid="rev-map-traveller-state"]').innerText().catch(() => "")));
note("ERRORS " + JSON.stringify(errors.slice(0, 5)));
await page.screenshot({ path: OUT + "/rehearsal9-map-after-next.png" });
await browser.close();
