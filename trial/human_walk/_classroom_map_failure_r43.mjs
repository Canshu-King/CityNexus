import { chromium } from "file:///D:/moodle/_cmdr_rescue_v3_1022/frontend/node_modules/playwright/index.mjs";
import fs from "node:fs";
const BASE = "http://127.0.0.1:14492";
const OUT = "D:/moodle/_cmdr_rescue_v3_1022/trial/results/20261022_v3_human_chrome";
const NL = String.fromCharCode(10);
const lines = [];
const note = (v) => { lines.push(v); fs.writeFileSync(OUT + "/classroom-map-failure-43.txt", lines.join(NL) + NL, "utf8"); };
const clean = (s) => String(s || "").replace(/\s+/g, " ").trim();

const browser = await chromium.launch({ headless: true });
const ctx = await browser.newContext({ viewport: { width: 430, height: 932 }, deviceScaleFactor: 1 });
await ctx.addInitScript(() => {
  if (!sessionStorage.getItem("__probe_booted")) { localStorage.clear(); sessionStorage.clear(); sessionStorage.setItem("__probe_booted", "1"); }
});
const page = await ctx.newPage();
const errors = [];
let blocked = 0;
page.on("pageerror", (e) => errors.push(String(e).slice(0, 160)));
await page.route("**/tile.openstreetmap.org/**", async (route) => { blocked += 1; await route.abort(); });
await page.route("**/*.tile.openstreetmap.org/**", async (route) => { blocked += 1; await route.abort(); });

await page.goto(BASE + "/revolution", { waitUntil: "networkidle", timeout: 60000 });
await page.waitForTimeout(1400);
await page.locator('[data-testid="rev-mobile-tab-trips"]').click();
await page.waitForTimeout(1000);
await page.locator('[data-testid="rev-demo-session"]').click();
await page.waitForTimeout(3600);
await page.getByRole("button", { name: /地图/ }).first().click();
await page.waitForTimeout(1800);
const load = page.getByRole("button", { name: /加载地图/ }).first();
note(`LOAD_BUTTON ${await load.count()}`);
await load.click().catch((e) => note(`LOAD_CLICK_ERROR ${String(e).slice(0, 100)}`));
await page.waitForTimeout(7000);
const statuses = await page.locator('[role="status"]').allInnerTexts();
note(`STATUS_LINES ${JSON.stringify(statuses.map(clean).slice(0, 5))}`);
note(`BLOCKED_TILES ${blocked}`);
note(`TRAVELLER_STATE ${JSON.stringify(clean(await page.locator('[data-testid="rev-map-traveller-state"]').innerText().catch(() => "")))}`);
note(`CANVAS ${await page.locator('[data-testid="rev-workspace-map-canvas"]').count()}`);
await page.screenshot({ path: OUT + "/classroom-map-failure-43.png", fullPage: false });
note(`ERRORS ${JSON.stringify(errors.slice(0, 3))}`);
await ctx.close();
await browser.close();
