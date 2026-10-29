import { chromium } from "file:///D:/moodle/_cmdr_rescue_v3_1022/frontend/node_modules/playwright/index.mjs";
import fs from "node:fs";

const BASE = process.env.PAIR_BASE || "http://127.0.0.1:14495";
const OUT = process.env.PAIR_OUT || "D:/moodle/_cmdr_rescue_v3_1022/trial/results/20261022_v3_human_chrome/clock-two-day-61.txt";
const TICKET = process.env.PAIR_TICKET || "";
const NL = String.fromCharCode(10);
const lines = [];
const note = (value) => { lines.push(value); fs.writeFileSync(OUT, lines.join(NL) + NL, "utf8"); };
const clean = (value) => String(value || "").replace(/\s+/g, " ").trim();

const browser = await chromium.launch({ headless: true });
const W = Number(process.env.PAIR_W || 390);
const H = Number(process.env.PAIR_H || 844);
const SHOT = process.env.PAIR_SHOT || "D:/moodle/_cmdr_rescue_v3_1022/trial/results/20261022_v3_human_chrome/classroom-clock-run-61-finish.png";
const ctx = await browser.newContext({ viewport: { width: W, height: H }, deviceScaleFactor: 1 });
const page = await ctx.newPage();
const errors = [];
page.on("pageerror", (error) => errors.push(String(error).slice(0, 160)));

await page.goto(`${BASE}/revolution#pair=${encodeURIComponent(TICKET)}`, { waitUntil: "networkidle", timeout: 60000 });
await page.waitForTimeout(4200);
if (!(await page.locator('[data-testid="rev-classroom-clock"]').count())) {
  await page.locator('[data-testid="rev-mobile-tab-trips"]').click().catch(() => {});
  await page.waitForTimeout(1200);
  const reopen = page.locator('[data-testid="rev-demo-session"]');
  if (await reopen.count()) { await reopen.first().click().catch(() => {}); await page.waitForTimeout(3800); }
}
const start = page.getByRole("button", { name: /开演/ }).first();
if (await start.count()) { await start.scrollIntoViewIfNeeded().catch(() => {}); await start.click().catch(() => {}); }
for (let wait = 0; wait < 25; wait += 1) {
  if (await page.locator('[data-testid="rev-clock-run"]').count()) break;
  await page.waitForTimeout(1000);
}
note(`RUN_OWNED ${await page.locator('[data-testid="rev-clock-run"]').count()}`);

const clock = page.locator('[data-testid="rev-clock-virtual"]');
const next = page.locator('[data-testid="rev-clock-next"]');
const readClock = async () => clean(await clock.first().innerText().catch(() => ""));
note(`START ${JSON.stringify(await readClock())}`);
for (let press = 1; press <= 8; press += 1) {
  if (!(await next.count())) { note(`PRESS_${press}_BUTTON_ABSENT`); break; }
  if (await next.first().isDisabled().catch(() => true)) { note(`PRESS_${press}_DISABLED`); break; }
  await next.first().scrollIntoViewIfNeeded().catch(() => {});
  await next.first().click().catch(() => {});
  await page.waitForTimeout(3600);
  const text = await readClock();
  note(`PRESS_${press} ${JSON.stringify(text)}`);
  note(`PRESS_${press}_NOTE ${JSON.stringify(clean(await page.locator('[data-testid="rev-clock-next-note"]').first().innerText().catch(() => "")))}`);
  if (/模拟行程已完成/.test(text)) break;
}
await clock.first().scrollIntoViewIfNeeded().catch(() => {});
await page.screenshot({ path: SHOT, fullPage: false });
note(`FINAL ${JSON.stringify(await readClock())}`);
note(`DONE_LINE ${JSON.stringify(clean(await page.locator('[data-testid="rev-clock-done"]').first().innerText().catch(() => "")))}`);
for (const id of ["rev-clock-plus30", "rev-clock-plus60", "rev-clock-next"]) {
  const locator = page.locator(`[data-testid="${id}"]`).first();
  note(`${id.toUpperCase()}_DISABLED ${await locator.count() ? await locator.isDisabled().catch(() => null) : "absent"}`);
}
note(`ERRORS ${JSON.stringify(errors.slice(0, 3))}`);
await ctx.close();
await browser.close();
