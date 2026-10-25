import { chromium } from "file:///D:/moodle/_cmdr_rescue_v3_1022/frontend/node_modules/playwright/index.mjs";
import fs from "node:fs";
const BASE = "http://127.0.0.1:14492";
const OUT = "D:/moodle/_cmdr_rescue_v3_1022/trial/results/20261022_v3_human_chrome";
const NL = String.fromCharCode(10);
const lines = [];
const note = (v) => { lines.push(v); fs.writeFileSync(OUT + "/classroom-finish-47.txt", lines.join(NL) + NL, "utf8"); };
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

const clockText = () => page.locator('[data-testid="rev-clock-virtual"]').innerText().catch(() => "");
const next = page.getByRole("button", { name: /到下一站/ }).first();
let presses = 0;
for (let i = 0; i < 18; i += 1) {
  const count = await next.count();
  if (!count) break;
  const disabled = await next.isDisabled().catch(() => true);
  if (disabled) break;
  await next.scrollIntoViewIfNeeded().catch(() => {});
  await next.click().catch(() => {});
  presses += 1;
  await page.waitForTimeout(1400);
  const text = clean(await clockText());
  if (/已完成/.test(text)) break;
}
note(`PRESSES ${presses}`);
note(`CLOCK_AT_END ${JSON.stringify(clean(await clockText()))}`);
const bodyEnd = await page.evaluate(() => document.body.innerText);
note(`DONE_LINE ${JSON.stringify(clean((bodyEnd.split("模拟行程已完成")[1] || "").split(NL)[0]))}`);
note(`NEXT_DISABLED ${await next.count() ? await next.first().isDisabled().catch(() => null) : "absent"}`);
await page.screenshot({ path: OUT + "/classroom-finish-47-end.png", fullPage: false });

// A teacher who reopens the classroom link after the trip is sealed must be told so.
const fresh = await ctx.newPage();
await fresh.addInitScript(() => { localStorage.clear(); sessionStorage.clear(); });
const freshErrors = [];
fresh.on("pageerror", (e) => freshErrors.push(String(e).slice(0, 140)));
await fresh.goto(BASE + "/revolution", { waitUntil: "networkidle", timeout: 60000 });
await fresh.waitForTimeout(1400);
await fresh.locator('[data-testid="rev-mobile-tab-trips"]').click();
await fresh.waitForTimeout(1000);
await fresh.locator('[data-testid="rev-demo-session"]').click();
await fresh.waitForTimeout(4500);
const banner = fresh.locator('[data-testid="rev-demo-error-banner"]');
note(`REENTRY_BANNER ${JSON.stringify(clean(await banner.first().innerText().catch(() => "")))}`);
note(`REENTRY_BANNER_COUNT ${await banner.count()}`);
await fresh.screenshot({ path: OUT + "/classroom-finish-47-reentry.png", fullPage: false });
note(`ERRORS ${JSON.stringify([...errors, ...freshErrors].slice(0, 3))}`);
await ctx.close();
await browser.close();
