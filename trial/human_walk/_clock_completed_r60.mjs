import { chromium } from "file:///D:/moodle/_cmdr_rescue_v3_1022/frontend/node_modules/playwright/index.mjs";
import fs from "node:fs";

const BASE = process.env.PAIR_BASE || "http://127.0.0.1:14495";
const OUT = "D:/moodle/_cmdr_rescue_v3_1022/trial/results/20261022_v3_human_chrome/clock-completed-60.txt";
const TICKET = process.env.PAIR_TICKET || "";
const NL = String.fromCharCode(10);
const lines = [];
const note = (value) => { lines.push(value); fs.writeFileSync(OUT, lines.join(NL) + NL, "utf8"); };
const clean = (value) => String(value || "").replace(/\s+/g, " ").trim();

const browser = await chromium.launch({ headless: true });
const ctx = await browser.newContext({ viewport: { width: 390, height: 844 }, deviceScaleFactor: 1 });
const page = await ctx.newPage();
const errors = [];
page.on("pageerror", (error) => errors.push(String(error).slice(0, 160)));

await page.goto(`${BASE}/revolution#pair=${encodeURIComponent(TICKET)}`, { waitUntil: "networkidle", timeout: 60000 });
await page.waitForTimeout(5200);
if (!(await page.locator('[data-testid="rev-classroom-clock"]').count())) {
  await page.locator('[data-testid="rev-mobile-tab-trips"]').click().catch(() => {});
  await page.waitForTimeout(1200);
  const reopen = page.locator('[data-testid="rev-demo-session"]');
  if (await reopen.count()) { await reopen.first().click().catch(() => {}); await page.waitForTimeout(4000); }
}
const clock = page.locator('[data-testid="rev-classroom-clock"]');
await clock.first().scrollIntoViewIfNeeded({ timeout: 3000 }).catch(() => {});
note(`CLOCK_PRESENT ${await clock.count()}`);
note(`CLOCK_TEXT ${JSON.stringify(clean(await page.locator('[data-testid="rev-clock-virtual"]').first().innerText({ timeout: 3000 }).catch(() => "")))}`);
note(`DONE_LINE ${JSON.stringify(clean(await page.locator('[data-testid="rev-clock-done"]').first().innerText({ timeout: 3000 }).catch(() => "")))}`);
note(`RUN_OWNED ${await page.locator('[data-testid="rev-clock-run"]').count()}`);
for (const id of ["rev-clock-plus30", "rev-clock-plus60", "rev-clock-next"]) {
  note(`${id.toUpperCase()}_DISABLED ${await page.locator(`[data-testid="${id}"]`).first().isDisabled().catch(() => null)}`);
}
note(`PRESENTER_DONE ${JSON.stringify(clean(await page.locator('[data-testid="rev-presenter-done"]').first().innerText({ timeout: 3000 }).catch(() => "")))}`);
await page.screenshot({ path: "D:/moodle/_cmdr_rescue_v3_1022/trial/results/20261022_v3_human_chrome/classroom-clock-run-60-completed.png", fullPage: false });
await page.locator('[data-testid="rev-clock-plus30"]').first().click({ force: true, timeout: 3000 }).catch(() => {});
await page.waitForTimeout(1200);
note(`AFTER_FORCED_CLICK ${JSON.stringify(clean(await page.locator('[data-testid="rev-clock-virtual"]').first().innerText({ timeout: 3000 }).catch(() => "")))}`);
note(`NOTE_AFTER ${JSON.stringify(clean(await page.locator('[data-testid="rev-clock-next-note"]').first().innerText({ timeout: 3000 }).catch(() => "")))}`);
note(`ERRORS ${JSON.stringify(errors.slice(0, 3))}`);
await ctx.close();
await browser.close();
