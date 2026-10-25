import { chromium } from "file:///D:/moodle/_cmdr_rescue_v3_1022/frontend/node_modules/playwright/index.mjs";
import fs from "node:fs";
const BASE = "http://127.0.0.1:14492";
const OUT = "D:/moodle/_cmdr_rescue_v3_1022/trial/results/20261022_v3_human_chrome";
const NL = String.fromCharCode(10);
const lines = [];
const note = (v) => { lines.push(v); fs.writeFileSync(OUT + "/classroom-done-plus-49.txt", lines.join(NL) + NL, "utf8"); };
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

const next = page.getByRole("button", { name: /到下一站/ }).first();
const clock = () => page.locator('[data-testid="rev-clock-virtual"]').innerText().catch(() => "");
for (let i = 0; i < 8; i += 1) {
  if (!(await next.count())) break;
  if (await next.isDisabled().catch(() => true)) break;
  await next.scrollIntoViewIfNeeded().catch(() => {});
  await next.click().catch(() => {});
  await page.waitForTimeout(1400);
}
note(`CLOCK_DONE ${JSON.stringify(clean(await clock()))}`);
note(`DONE_BADGE ${await page.locator('[data-testid="rev-clock-done"]').count()}`);
const plus60 = page.locator('[data-testid="rev-clock-plus60"]');
note(`PLUS60_DISABLED ${await plus60.isDisabled().catch(() => null)}`);
await plus60.scrollIntoViewIfNeeded().catch(() => {});
await plus60.click().catch((e) => note(`PLUS60_CLICK_ERROR ${String(e).slice(0, 100)}`));
await page.waitForTimeout(3200);
note(`CLOCK_AFTER_PLUS ${JSON.stringify(clean(await clock()))}`);
note(`NOTE_AFTER_PLUS ${JSON.stringify(clean(await page.locator('[data-testid="rev-clock-next-note"]').innerText().catch(() => "")))}`);
note(`DONE_BADGE_AFTER ${await page.locator('[data-testid="rev-clock-done"]').count()}`);
await page.screenshot({ path: OUT + "/classroom-done-plus-49.png", fullPage: false });
note(`ERRORS ${JSON.stringify(errors.slice(0, 3))}`);
await ctx.close();
await browser.close();
