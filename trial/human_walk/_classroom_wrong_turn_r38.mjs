import { chromium } from "file:///D:/moodle/_cmdr_rescue_v3_1022/frontend/node_modules/playwright/index.mjs";
import fs from "node:fs";
const BASE = "http://127.0.0.1:14492";
const OUT = "D:/moodle/_cmdr_rescue_v3_1022/trial/results/20261022_v3_human_chrome";
const NL = String.fromCharCode(10);
const lines = [];
const note = (v) => { lines.push(v); fs.writeFileSync(OUT + "/classroom-wrong-turn-38.txt", lines.join(NL) + NL, "utf8"); };
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
await page.waitForTimeout(3000);

await page.locator('[data-testid="rev-mobile-tab-trips"]').click();
await page.waitForTimeout(1200);
const explore = page.getByRole("button", { name: /开始探索/ }).first();
note(`EXPLORE_BUTTON ${await explore.count()}`);
await explore.click().catch(() => {});
await page.waitForTimeout(1800);
note(`AFTER_EXPLORE_TITLE ${JSON.stringify(clean(await page.locator("h1").first().innerText().catch(() => "")))}`);
note(`AFTER_EXPLORE_HAS_FORM ${await page.locator('[data-testid="rev-trip-request-form"]').count()}`);
await page.screenshot({ path: OUT + "/classroom-wrong-turn-38-explore.png", fullPage: false });

await page.locator('[data-testid="rev-mobile-tab-trips"]').click();
await page.waitForTimeout(1400);
const demo = page.locator('[data-testid="rev-demo-session"]');
note(`TRIPS_DEMO_BUTTON ${await demo.count()}`);
note(`TRIPS_TEXT ${JSON.stringify(clean(await page.locator('[data-testid="revolution-first-look"]').innerText().catch(() => "")).slice(0, 180))}`);
await page.screenshot({ path: OUT + "/classroom-wrong-turn-38-back.png", fullPage: false });

if (await demo.count()) {
  await demo.click();
  await page.waitForTimeout(4200);
  note(`RECOVERED_PRESENTER ${await page.locator('[data-testid="rev-presenter"]').count()}`);
  note(`RECOVERED_CLOCK ${JSON.stringify(clean(await page.locator('[data-testid="rev-clock-virtual"]').innerText().catch(() => "")))}`);
}
note(`ERRORS ${JSON.stringify(errors.slice(0, 3))}`);
await ctx.close();
await browser.close();
