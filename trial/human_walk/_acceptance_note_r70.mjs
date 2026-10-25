import { chromium } from "file:///D:/moodle/_cmdr_rescue_v3_1022/frontend/node_modules/playwright/index.mjs";
import fs from "node:fs";

const BASE = process.env.PAIR_BASE || "http://127.0.0.1:14495";
const OUT = "D:/moodle/_cmdr_rescue_v3_1022/trial/results/20261022_v3_human_chrome/acceptance-note-70.txt";
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
await page.waitForTimeout(5000);
if (!(await page.locator('[data-testid="rev-classroom-clock"]').count())) {
  await page.locator('[data-testid="rev-mobile-tab-trips"]').click().catch(() => {});
  await page.waitForTimeout(1200);
}
const presenter = page.locator('[data-testid="rev-presenter-run"]');
note(`PRESENTER_RUN ${JSON.stringify(clean(await presenter.first().innerText().catch(() => "")))}`);
note(`ACCEPTANCE_NOTE ${JSON.stringify(clean(await page.locator('[data-testid="rev-presenter-acceptance-note"]').first().innerText().catch(() => "")))}`);
note(`RESUME_BUTTONS ${await page.getByRole("button", { name: /继续模拟/ }).count()}`);
note(`ADVANCE_HINT ${JSON.stringify(clean(await page.locator('[data-testid="rev-presenter-advance-hint"]').first().innerText().catch(() => "")))}`);
await page.locator('[data-testid="rev-presenter"]').first().scrollIntoViewIfNeeded().catch(() => {});
await page.screenshot({ path: "D:/moodle/_cmdr_rescue_v3_1022/trial/results/20261022_v3_human_chrome/classroom-clock-run-70-acceptance.png", fullPage: false });
note(`ERRORS ${JSON.stringify(errors.slice(0, 3))}`);
await ctx.close();
await browser.close();
