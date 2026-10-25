import { chromium } from "file:///D:/moodle/_cmdr_rescue_v3_1022/frontend/node_modules/playwright/index.mjs";
import fs from "node:fs";
const BASE = "http://127.0.0.1:14492";
const OUT = "D:/moodle/_cmdr_rescue_v3_1022/trial/results/20261022_v3_human_chrome";
const NL = String.fromCharCode(10);
const lines = [];
const note = (v) => { lines.push(v); fs.writeFileSync(OUT + "/classroom-backend-down-42.txt", lines.join(NL) + NL, "utf8"); };
const clean = (s) => String(s || "").replace(/\s+/g, " ").trim();

const browser = await chromium.launch({ headless: true });
const ctx = await browser.newContext({ viewport: { width: 430, height: 932 }, deviceScaleFactor: 1 });
await ctx.addInitScript(() => {
  if (!sessionStorage.getItem("__probe_booted")) { localStorage.clear(); sessionStorage.clear(); sessionStorage.setItem("__probe_booted", "1"); }
});
const page = await ctx.newPage();
const errors = [];
page.on("pageerror", (e) => errors.push(String(e).slice(0, 160)));
await page.goto(BASE + "/revolution", { waitUntil: "domcontentloaded", timeout: 60000 }).catch((e) => note(`GOTO ${String(e).slice(0, 100)}`));
await page.waitForTimeout(2500);
await page.locator('[data-testid="rev-mobile-tab-trips"]').click();
await page.waitForTimeout(900);
const button = page.locator('[data-testid="rev-demo-session"]');
note(`ENTRY_BUTTON ${await button.count()} DISABLED ${await button.count() ? await button.first().isDisabled() : null}`);
await button.click().catch(() => {});
await page.waitForTimeout(4500);
const banner = page.locator('[data-testid="rev-demo-error-banner"]');
note(`BANNER_COUNT ${await banner.count()}`);
note(`BANNER_TEXT ${JSON.stringify(clean(await banner.first().innerText().catch(() => "")))}`);
const box = await banner.count() ? await banner.first().boundingBox().catch(() => null) : null;
note(`BANNER_BOX ${JSON.stringify(box)}`);
note(`STILL_ON_TRIPS ${JSON.stringify(clean(await page.locator('[data-testid="revolution-first-look"]').innerText().catch(() => "")).includes("课堂演示：进入示例行程"))}`);
await page.screenshot({ path: OUT + "/classroom-backend-down-42.png", fullPage: false });
note(`ERRORS ${JSON.stringify(errors.slice(0, 3))}`);
await ctx.close();
await browser.close();
