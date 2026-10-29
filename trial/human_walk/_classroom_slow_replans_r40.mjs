import { chromium } from "file:///D:/moodle/_cmdr_rescue_v3_1022/frontend/node_modules/playwright/index.mjs";
import fs from "node:fs";
const BASE = "http://127.0.0.1:14492";
const OUT = "D:/moodle/_cmdr_rescue_v3_1022/trial/results/20261022_v3_human_chrome";
const NL = String.fromCharCode(10);
const lines = [];
const note = (v) => { lines.push(v); fs.writeFileSync(OUT + "/classroom-slow-replans-40.txt", lines.join(NL) + NL, "utf8"); };
const clean = (s) => String(s || "").replace(/\s+/g, " ").trim();

const browser = await chromium.launch({ headless: true });
const ctx = await browser.newContext({ viewport: { width: 430, height: 932 }, deviceScaleFactor: 1 });
await ctx.addInitScript(() => {
  if (!sessionStorage.getItem("__probe_booted")) { localStorage.clear(); sessionStorage.clear(); sessionStorage.setItem("__probe_booted", "1"); }
});
const page = await ctx.newPage();
const errors = [];
page.on("pageerror", (e) => errors.push(String(e).slice(0, 160)));
let delayed = 0;
await page.route("**/replans*", async (route) => {
  if (route.request().method() === "GET") {
    delayed += 1;
    await new Promise((resolve) => setTimeout(resolve, 3000));
  }
  await route.continue().catch(() => {});
});

await page.goto(BASE + "/revolution", { waitUntil: "networkidle", timeout: 60000 });
await page.waitForTimeout(1400);
await page.locator('[data-testid="rev-mobile-tab-trips"]').click();
await page.waitForTimeout(1000);
await page.locator('[data-testid="rev-demo-session"]').click();
await page.waitForTimeout(3600);
await page.getByRole("button", { name: /行程守护/ }).first().click();

await page.waitForTimeout(900);
const loading = page.locator('[data-testid="rev-guardian-proposal-loading"]');
note(`LOADING_COUNT ${await loading.count()} VISIBLE ${await loading.count() ? await loading.first().isVisible() : false}`);
note(`LOADING_TEXT ${JSON.stringify(clean(await loading.first().innerText().catch(() => "")))}`);
const loadingBox = await loading.first().boundingBox().catch(() => null);
note(`LOADING_BOX ${JSON.stringify(loadingBox)}`);
note(`LOADING_IN_VIEW ${JSON.stringify(!!loadingBox && loadingBox.y >= 0 && loadingBox.y + loadingBox.height <= 932)}`);
await page.screenshot({ path: OUT + "/classroom-slow-replans-40-loading.png", fullPage: false });

await page.waitForTimeout(4200);
const card = page.locator('[data-testid="rev-guardian-proposal"]');
note(`CARD_AFTER ${await card.count()}`);
note(`CARD_TEXT ${JSON.stringify(clean(await page.locator('[data-testid="rev-guardian-proposal-diff"]').innerText().catch(() => "")))}`);
note(`LOADING_AFTER ${await page.locator('[data-testid="rev-guardian-proposal-loading"]').count()}`);
note(`DELAYED_GETS ${delayed}`);
await page.screenshot({ path: OUT + "/classroom-slow-replans-40-card.png", fullPage: false });
note(`ERRORS ${JSON.stringify(errors.slice(0, 3))}`);
await ctx.close();
await browser.close();
