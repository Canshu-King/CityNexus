import { chromium } from "file:///D:/moodle/_cmdr_rescue_v3_1022/frontend/node_modules/playwright/index.mjs";
import { execFileSync } from "node:child_process";
import fs from "node:fs";

const BASE = "http://127.0.0.1:14492";
const DIR = "D:/moodle/_cmdr_rescue_v3_1022/trial/results/20261022_v3_human_chrome";
const OUT = DIR + "/guardian-lag-note-133.txt";
const SHOT = DIR + "/classroom-guardian-lag-note-133.png";
const HELPER = "D:/moodle/_cmdr_rescue_v3_1022/trial/human_walk/_guardian_lag_inject_r1.py";
const NL = String.fromCharCode(10);
const lines = [];
const note = (value) => { lines.push(value); fs.writeFileSync(OUT, lines.join(NL) + NL, "utf8"); };
const raw = JSON.parse(fs.readFileSync("D:/moodle/_cmdr_v3_live_1022/.demo_pairing_ticket", "utf8"));
const tickets = (raw.tickets && raw.tickets.length ? raw.tickets : [raw.ticket]).filter(Boolean);

const browser = await chromium.launch({ headless: true });
const ctx = await browser.newContext({ viewport: { width: 390, height: 844 }, deviceScaleFactor: 1 });
const page = await ctx.newPage();
const errors = [];
page.on("pageerror", (error) => errors.push(String(error).slice(0, 120)));

async function press(name, timeout = 15000) {
  const target = page.getByRole("button", { name }).first();
  try { await target.waitFor({ state: "visible", timeout }); } catch { note(`MISS_BUTTON ${name}`); return false; }
  await target.scrollIntoViewIfNeeded().catch(() => {});
  await page.waitForTimeout(250);
  await target.click({ timeout: 8000 }).catch(() => {});
  return true;
}

await page.goto(`${BASE}/revolution#pair=${encodeURIComponent(tickets[0])}`, { waitUntil: "networkidle", timeout: 60000 });
await page.waitForTimeout(5200);
if (await press("去课堂控制台")) await page.waitForTimeout(1000);
if (!(await press("开演（模拟两日）"))) note("NO_START");
await page.waitForTimeout(2600);
if (!(await press("闭馆"))) note("NO_CLOSURE");
await page.waitForTimeout(3000);

const injected = JSON.parse(execFileSync("python", [HELPER, "inject"], { encoding: "utf-8" }).trim());
note(`INJECTED ${JSON.stringify(injected)}`);
await page.waitForTimeout(13000);
const failed = page.locator('[data-testid="rev-presenter-guardian-failed"]').first();
const count = await failed.count();
const detail = count ? await failed.evaluate((node) => {
  const box = node.getBoundingClientRect();
  return {
    text: (node.textContent || "").trim(),
    visible: box.width > 0 && box.height > 0,
    inViewport: box.top >= 0 && box.bottom <= window.innerHeight,
  };
}) : null;
note(`LAG_NOTE ${count} ${JSON.stringify(detail)}`);
await page.screenshot({ path: SHOT, fullPage: false });
note(`RESTORE ${execFileSync("python", [HELPER, "restore", JSON.stringify(injected)], { encoding: "utf-8" }).trim()}`);
note(`ERRORS ${JSON.stringify(errors.slice(0, 3))}`);
await browser.close();
