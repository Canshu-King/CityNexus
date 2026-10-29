import { chromium } from "file:///D:/moodle/_cmdr_rescue_v3_1022/frontend/node_modules/playwright/index.mjs";
import fs from "node:fs";

const BASE = process.env.PAIR_BASE || "http://127.0.0.1:14495";
const OUT = "D:/moodle/_cmdr_rescue_v3_1022/trial/results/20261022_v3_human_chrome/clock-scene-guardian-59.txt";
const TICKET = process.env.PAIR_TICKET || "";
const NL = String.fromCharCode(10);
const lines = [];
const note = (value) => { lines.push(value); fs.writeFileSync(OUT, lines.join(NL) + NL, "utf8"); };
const clean = (value) => String(value || "").replace(/\s+/g, " ").trim();
const shot = (page, name) => page.screenshot({ path: `D:/moodle/_cmdr_rescue_v3_1022/trial/results/20261022_v3_human_chrome/${name}`, fullPage: false });

const browser = await chromium.launch({ headless: true });
const ctx = await browser.newContext({ viewport: { width: 390, height: 844 }, deviceScaleFactor: 1 });
const page = await ctx.newPage();
const errors = [];
page.on("pageerror", (error) => errors.push(String(error).slice(0, 160)));
const presenter = page.locator('[data-testid="rev-presenter-run"]');
const message = page.locator('[data-testid="rev-presenter-message"]');

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
note(`AFTER_START ${JSON.stringify(clean(await presenter.first().innerText().catch(() => "")))}`);

const next = page.locator('[data-testid="rev-clock-next"]');
await next.first().scrollIntoViewIfNeeded().catch(() => {});
await next.first().click().catch(() => {});
await page.waitForTimeout(2600);
note(`AFTER_ADVANCE ${JSON.stringify(clean(await presenter.first().innerText().catch(() => "")))}`);

const rain = page.getByRole("button", { name: /^下雨$/ }).first();
note(`SCENE_BUTTON ${await rain.count()}`);
if (await rain.count()) {
  await rain.scrollIntoViewIfNeeded().catch(() => {});
  await rain.click().catch(() => {});
  await page.waitForTimeout(3000);
  note(`AFTER_SCENE ${JSON.stringify(clean(await presenter.first().innerText().catch(() => "")))}`);
  note(`AFTER_SCENE_MSG ${JSON.stringify(clean(await message.first().innerText().catch(() => "")))}`);
  await shot(page, "classroom-clock-run-59-scene.png");
}

const guardian = page.getByRole("button", { name: /交给守护助手/ }).first();
note(`GUARDIAN_BUTTON ${await guardian.count()}`);
if (await guardian.count()) {
  await guardian.scrollIntoViewIfNeeded().catch(() => {});
  await guardian.click().catch(() => {});
  let settled = "";
  for (let wait = 0; wait < 90; wait += 3) {
    await page.waitForTimeout(3000);
    settled = clean(await presenter.first().innerText().catch(() => ""));
    if (!/守护正在分析/.test(settled)) break;
  }
  note(`AFTER_GUARDIAN ${JSON.stringify(settled)}`);
  note(`AFTER_GUARDIAN_MSG ${JSON.stringify(clean(await message.first().innerText().catch(() => "")))}`);
  await shot(page, "classroom-clock-run-59-guardian.png");
}

const resume = page.getByRole("button", { name: /继续模拟/ }).first();
note(`RESUME_BUTTON ${await resume.count()}`);
if (await resume.count()) {
  await resume.scrollIntoViewIfNeeded().catch(() => {});
  await resume.click().catch(() => {});
  await page.waitForTimeout(3000);
  note(`AFTER_RESUME ${JSON.stringify(clean(await presenter.first().innerText().catch(() => "")))}`);
  note(`AFTER_RESUME_MSG ${JSON.stringify(clean(await message.first().innerText().catch(() => "")))}`);
  await shot(page, "classroom-clock-run-59-resume.png");
}

note(`CLOCK ${JSON.stringify(clean(await page.locator('[data-testid="rev-clock-virtual"]').first().innerText().catch(() => "")))}`);
note(`ERRORS ${JSON.stringify(errors.slice(0, 3))}`);
await ctx.close();
await browser.close();
