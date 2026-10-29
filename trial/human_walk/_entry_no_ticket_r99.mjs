import { chromium } from "file:///D:/moodle/_cmdr_rescue_v3_1022/frontend/node_modules/playwright/index.mjs";
import fs from "node:fs";

const BASE = "http://127.0.0.1:14492";
const OUT = "D:/moodle/_cmdr_rescue_v3_1022/trial/results/20261022_v3_human_chrome/entry-no-ticket-99.txt";
const SHOT = "D:/moodle/_cmdr_rescue_v3_1022/trial/results/20261022_v3_human_chrome/classroom-entry-no-ticket-99.png";
const NL = String.fromCharCode(10);
const lines = [];
const note = (value) => { lines.push(value); fs.writeFileSync(OUT, lines.join(NL) + NL, "utf8"); };
const clean = (value) => String(value || "").replace(/\s+/g, " ").trim();

const browser = await chromium.launch({ headless: true });
const ctx = await browser.newContext({ viewport: { width: 390, height: 844 }, deviceScaleFactor: 1 });
const page = await ctx.newPage();
const errors = [];
page.on("pageerror", (error) => errors.push(String(error).slice(0, 160)));

await page.goto(`${BASE}/revolution`, { waitUntil: "networkidle", timeout: 60000 });
await page.waitForTimeout(4200);
note(`BANNER_BEFORE ${JSON.stringify(clean(await page.locator('[data-testid="rev-demo-error-banner"]').first().textContent().catch(() => null)))}`);
const me = page.locator('[data-testid="rev-mobile-tab-trips"]').first();
note(`TRIPS_TAB ${await me.count()}`);
if (await me.count()) { await me.click().catch(() => {}); await page.waitForTimeout(1500); }
const session = page.locator('[data-testid="rev-demo-session"]').first();
note(`SESSION_BUTTON ${await session.count()}`);
if (await session.count()) {
  await session.scrollIntoViewIfNeeded().catch(() => {});
  await session.click().catch(() => {});
  await page.waitForTimeout(4500);
}
const banner = page.locator('[data-testid="rev-demo-error-banner"]').first();
const text = await banner.textContent().catch(() => null);
note(`BANNER_AFTER ${JSON.stringify(clean(text))}`);
note(`SESSION_AFTER ${await page.locator('[data-testid="rev-demo-session"]').count()}`);
note(`ERRORS ${JSON.stringify(errors.slice(0, 3))}`);
await page.screenshot({ path: SHOT, fullPage: false });
await browser.close();
