import { chromium } from "file:///D:/moodle/_cmdr_rescue_v3_1022/frontend/node_modules/playwright/index.mjs";
import fs from "node:fs";

const BASE = process.env.PAIR_BASE || "http://127.0.0.1:14495";
const OUT = process.env.PAIR_OUT || "D:/moodle/_cmdr_rescue_v3_1022/trial/results/20261022_v3_human_chrome/clock-run-lan-63.txt";
const TICKET = process.env.PAIR_TICKET || "";
const NL = String.fromCharCode(10);
const lines = [];
const note = (value) => {
  lines.push(value);
  fs.writeFileSync(OUT, lines.join(NL) + NL, "utf8");
};
const clean = (value) => String(value || "").replace(/\s+/g, " ").trim();
const stepOf = (text) => {
  const match = /执行第\s*(\d+)\s*步/.exec(text || "");
  return match ? Number(match[1]) : null;
};

const browser = await chromium.launch({ headless: true });
const ctx = await browser.newContext({ viewport: { width: 390, height: 844 }, deviceScaleFactor: 1 });
await ctx.addInitScript(() => {
  if (!sessionStorage.getItem("__clock_probe")) {
    localStorage.clear();
    sessionStorage.clear();
    sessionStorage.setItem("__clock_probe", "1");
  }
});
const page = await ctx.newPage();
const errors = [];
page.on("pageerror", (error) => errors.push(String(error).slice(0, 160)));

const clock = page.locator('[data-testid="rev-classroom-clock"]');
const virtual = page.locator('[data-testid="rev-clock-virtual"]');
const plus30 = page.locator('[data-testid="rev-clock-plus30"]');
const next = page.locator('[data-testid="rev-clock-next"]');
const shot = async (name) => {
  await page.screenshot({ path: `D:/moodle/_cmdr_rescue_v3_1022/trial/results/20261022_v3_human_chrome/${name}`, fullPage: false });
};

await page.goto(`${BASE}/revolution#pair=${encodeURIComponent(TICKET)}`, { waitUntil: "networkidle", timeout: 60000 });
await page.waitForTimeout(4200);
if (!(await clock.count())) {
  await page.locator('[data-testid="rev-mobile-tab-trips"]').click().catch(() => {});
  await page.waitForTimeout(1200);
  const reopen = page.locator('[data-testid="rev-demo-session"]');
  if (await reopen.count()) { await reopen.first().click().catch(() => {}); await page.waitForTimeout(3800); }
}
await clock.first().scrollIntoViewIfNeeded().catch(() => {});
note(`CLOCK_PRESENT ${await clock.count()}`);
note(`BEFORE ${JSON.stringify(clean(await virtual.first().innerText().catch(() => "")))}`);

note(`CITIES ${JSON.stringify(clean(await page.locator('[data-testid="rev-presenter-cities"]').first().innerText().catch(() => "")))}`);
await shot("classroom-clock-run-63-pre.png");
const startButton = page.getByRole("button", { name: /开演/ }).first();
if (await startButton.count()) {
  note("START_BUTTON present");
  await startButton.scrollIntoViewIfNeeded().catch(() => {});
  await startButton.click().catch(() => {});
  await page.waitForTimeout(3500);
} else {
  note("START_BUTTON absent");
}
await clock.first().scrollIntoViewIfNeeded().catch(() => {});
note(`RUN_OWNED ${await page.locator('[data-testid="rev-clock-run"]').count()}`);
note(`RUN_OWNED_LATE ${await page.locator('[data-testid="rev-clock-run"]').count()}`);
const afterStart = clean(await virtual.first().innerText().catch(() => ""));
note(`AFTER_START ${JSON.stringify(afterStart)}`);
note(`PRESENTER_RUN ${JSON.stringify(clean(await page.locator('[data-testid="rev-presenter-run"]').first().innerText().catch(() => "")))}`);
note(`PRESENTER_MESSAGE ${JSON.stringify(clean(await page.locator('[data-testid="rev-presenter-message"]').first().innerText().catch(() => "")))}`);
note(`STEP_START ${stepOf(afterStart)}`);
await shot("classroom-clock-run-63-a.png");

for (let index = 1; index <= 2; index += 1) {
  await plus30.first().scrollIntoViewIfNeeded().catch(() => {});
  const disabled = await plus30.first().isDisabled().catch(() => true);
  note(`PLUS30_${index}_DISABLED ${disabled}`);
  if (disabled) break;
  await plus30.first().click().catch(() => {});
  await page.waitForTimeout(1800);
  const text = clean(await virtual.first().innerText().catch(() => ""));
  note(`PLUS30_${index}_TEXT ${JSON.stringify(text)}`);
  note(`PLUS30_${index}_STEP ${stepOf(text)}`);
  note(`PLUS30_${index}_NOTE ${JSON.stringify(clean(await page.locator('[data-testid="rev-clock-next-note"]').first().innerText().catch(() => "")))}`);
  note(`PLUS30_${index}_PRESENTER ${JSON.stringify(clean(await page.locator('[data-testid="rev-presenter-run"]').first().innerText().catch(() => "")))}`);
}
await shot("classroom-clock-run-63-b.png");

const nextDisabled = await next.first().isDisabled().catch(() => true);
note(`NEXT_DISABLED ${nextDisabled}`);
if (!nextDisabled) {
  await next.first().click().catch(() => {});
  await page.waitForTimeout(4200);
  note(`AFTER_NEXT ${JSON.stringify(clean(await virtual.first().innerText().catch(() => "")))}`);
  note(`AFTER_NEXT_STEP ${stepOf(clean(await virtual.first().innerText().catch(() => "")))}`);
  note(`AFTER_NEXT_NOTE ${JSON.stringify(clean(await page.locator('[data-testid="rev-clock-next-note"]').first().innerText().catch(() => "")))}`);
}
await shot("classroom-clock-run-63-c.png");

const beforeReload = clean(await virtual.first().innerText().catch(() => ""));
await page.reload({ waitUntil: "networkidle", timeout: 60000 });
await page.waitForTimeout(4200);
await clock.first().scrollIntoViewIfNeeded().catch(() => {});
const afterReload = clean(await virtual.first().innerText().catch(() => ""));
note(`BEFORE_RELOAD ${JSON.stringify(beforeReload)}`);
note(`AFTER_RELOAD ${JSON.stringify(afterReload)}`);
note(`RELOAD_SAME_STEP ${stepOf(beforeReload) === stepOf(afterReload)}`);
note(`RUN_OWNED_END ${await page.locator('[data-testid="rev-clock-run"]').count()}`);
await shot("classroom-clock-run-63-d.png");

note(`ERRORS ${JSON.stringify(errors.slice(0, 3))}`);
await ctx.close();
await browser.close();
