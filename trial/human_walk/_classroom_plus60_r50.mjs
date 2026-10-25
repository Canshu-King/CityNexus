import { chromium } from "file:///D:/moodle/_cmdr_rescue_v3_1022/frontend/node_modules/playwright/index.mjs";
import fs from "node:fs";
const BASE = "http://127.0.0.1:14492";
const OUT = "D:/moodle/_cmdr_rescue_v3_1022/trial/results/20261022_v3_human_chrome";
const NL = String.fromCharCode(10);
const lines = [];
const note = (v) => { lines.push(v); fs.writeFileSync(OUT + "/classroom-plus60-50.txt", lines.join(NL) + NL, "utf8"); };
const clean = (s) => String(s || "").replace(/\s+/g, " ").trim();

const browser = await chromium.launch({ headless: true });
const ctx = await browser.newContext({ viewport: { width: 430, height: 932 }, deviceScaleFactor: 1 });
await ctx.addInitScript(() => {
  if (!sessionStorage.getItem("__probe_booted")) { localStorage.clear(); sessionStorage.clear(); sessionStorage.setItem("__probe_booted", "1"); }
});
const page = await ctx.newPage();
const errors = [];
page.on("pageerror", (e) => errors.push(String(e).slice(0, 160)));
await page.goto(BASE + "/revolution", { waitUntil: "networkidle", timeout: 60000 });
await page.waitForTimeout(1400);
await page.locator('[data-testid="rev-mobile-tab-trips"]').click();
await page.waitForTimeout(1000);
await page.locator('[data-testid="rev-demo-session"]').click();
await page.waitForTimeout(3600);


const plus60 = page.locator('[data-testid="rev-clock-plus60"]');
await plus60.scrollIntoViewIfNeeded().catch(() => {});
await plus60.click().catch((e) => note(`PLUS60_CLICK_ERROR ${String(e).slice(0, 100)}`));
await page.waitForTimeout(3000);
note(`CLOCK ${JSON.stringify(clean(await page.locator('[data-testid="rev-clock-virtual"]').innerText().catch(() => "")))}`);
note(`NOTE ${JSON.stringify(clean(await page.locator('[data-testid="rev-clock-next-note"]').innerText().catch(() => "")))}`);
note(`DONE_BADGE ${await page.locator('[data-testid="rev-clock-done"]').count()}`);
await page.screenshot({ path: OUT + "/classroom-plus60-50.png", fullPage: false });
note(`ERRORS ${JSON.stringify(errors.slice(0, 3))}`);
await ctx.close();
await browser.close();
