import { chromium } from "file:///D:/moodle/_cmdr_rescue_v3_1022/frontend/node_modules/playwright/index.mjs";
import fs from "node:fs";

const BASE = process.env.PAIR_BASE || "http://127.0.0.1:14495";
const OUT = "D:/moodle/_cmdr_rescue_v3_1022/trial/results/20261022_v3_human_chrome/tablet-hit-73.txt";
const TICKET = process.env.PAIR_TICKET || "";
const NL = String.fromCharCode(10);
const lines = [];
const note = (value) => { lines.push(value); fs.writeFileSync(OUT, lines.join(NL) + NL, "utf8"); };
const clean = (value) => String(value || "").replace(/\s+/g, " ").trim();

const browser = await chromium.launch({ headless: true });
const ctx = await browser.newContext({ viewport: { width: 1024, height: 768 }, deviceScaleFactor: 1 });
const page = await ctx.newPage();
const errors = [];
page.on("pageerror", (error) => errors.push(String(error).slice(0, 160)));

await page.goto(`${BASE}/revolution#pair=${encodeURIComponent(TICKET)}`, { waitUntil: "networkidle", timeout: 60000 });
await page.waitForTimeout(4200);
if (!(await page.locator('[data-testid="rev-classroom-clock"]').count())) {
  await page.locator('[data-testid="rev-mobile-tab-trips"]').click().catch(() => {});
  await page.waitForTimeout(1200);
}
const start = page.getByRole("button", { name: /开演/ }).first();
if (await start.count()) { await start.scrollIntoViewIfNeeded().catch(() => {}); await start.click().catch(() => {}); }
await page.waitForTimeout(5200);
note(`RUN_OWNED ${await page.locator('[data-testid="rev-clock-run"]').count()}`);

const ids = ["rev-open-trip", "rev-clock-plus30", "rev-clock-plus60", "rev-clock-next"];
for (const id of ids) {
  const locator = page.locator(`[data-testid="${id}"]`).first();
  const count = await locator.count();
  if (!count) { note(`${id} ABSENT`); continue; }
  await locator.scrollIntoViewIfNeeded().catch(() => {});
  await page.waitForTimeout(250);
  const box = await locator.boundingBox().catch(() => null);
  const hit = await page.evaluate(({ testId }) => {
    const node = document.querySelector(`[data-testid="${testId}"]`);
    if (!node) return { hit: false, why: "missing" };
    const rect = node.getBoundingClientRect();
    const x = rect.left + rect.width / 2;
    const y = rect.top + rect.height / 2;
    const top = document.elementFromPoint(x, y);
    return { hit: Boolean(top && (top === node || node.contains(top))), top: top ? (top.tagName + "." + (top.className || "").toString().slice(0, 40)) : "",
             inViewport: rect.top >= 0 && rect.bottom <= window.innerHeight && rect.left >= 0 && rect.right <= window.innerWidth };
  }, { testId: id });
  note(`${id} ${JSON.stringify({ box: box ? { x: Math.round(box.x), y: Math.round(box.y), w: Math.round(box.width), h: Math.round(box.height) } : null, ...hit })}`);
}
await page.locator('[data-testid="rev-classroom-clock"]').first().scrollIntoViewIfNeeded().catch(() => {});
await page.screenshot({ path: "D:/moodle/_cmdr_rescue_v3_1022/trial/results/20261022_v3_human_chrome/classroom-tablet-hit-73.png", fullPage: false });
note(`ERRORS ${JSON.stringify(errors.slice(0, 3))}`);
await ctx.close();
await browser.close();
