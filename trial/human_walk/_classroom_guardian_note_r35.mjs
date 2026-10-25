import { chromium } from "file:///D:/moodle/_cmdr_rescue_v3_1022/frontend/node_modules/playwright/index.mjs";
import fs from "node:fs";
const BASE = process.env.SIM_BASE || "http://127.0.0.1:14494";
const TICKET = process.env.PAIR_TICKET || "";
const TAG = process.env.PROBE_TAG || "";
const OUT = "D:/moodle/_cmdr_rescue_v3_1022/trial/results/20261022_v3_human_chrome";
const NL = String.fromCharCode(10);
const lines = [];
const note = (v) => { lines.push(v); fs.writeFileSync(OUT + `/classroom-guardian-note-35${TAG}.txt`, lines.join(NL) + NL, "utf8"); };
const clean = (s) => String(s || "").replace(/\s+/g, " ").trim();

const browser = await chromium.launch({ headless: true });
const ctx = await browser.newContext({ viewport: { width: 430, height: 932 }, deviceScaleFactor: 1 });
await ctx.addInitScript(() => {
  if (!sessionStorage.getItem("__probe_booted")) {
    localStorage.clear(); sessionStorage.clear();
    sessionStorage.setItem("__probe_booted", "1");
  }
});
const page = await ctx.newPage();
const errors = [];
page.on("pageerror", (e) => errors.push(String(e).slice(0, 160)));

await page.goto(`${BASE}/revolution#pair=${encodeURIComponent(TICKET)}`, { waitUntil: "networkidle", timeout: 60000 });
await page.waitForTimeout(6500);
const status = () => page.locator('[data-testid="rev-presenter-run"]').innerText().catch(() => "");
note(`BEFORE ${JSON.stringify(clean(await status()))}`);

const closure = page.locator('[data-testid="rev-presenter-scenes"] button', { hasText: "闭馆" });
note(`SCENES_BUTTONS ${await page.locator('[data-testid="rev-presenter-scenes"] button').count()}`);
await closure.first().click();
await page.waitForTimeout(2800);
note(`AFTER_SCENE ${JSON.stringify(clean(await status()))}`);
await page.screenshot({ path: OUT + `/classroom-guardian-note-35${TAG}-paused.png`, fullPage: false });

const guardian = page.locator('.rev-presenter-actions button', { hasText: "交给守护助手" });
const present = await guardian.count();
note(`GUARDIAN_BUTTON ${present}`);
if (present) {
  await guardian.first().click();
  await page.waitForTimeout(1800);
  const slow = page.locator('[data-testid="rev-presenter-slow"]');
  note(`SLOW_TEXT ${JSON.stringify(clean(await slow.innerText().catch(() => "")))}`);
  note(`SLOW_VISIBLE ${await slow.count() ? await slow.first().isVisible() : false}`);
  note(`BUSY_BUTTON_DISABLED ${await guardian.first().isDisabled().catch(() => null)}`);
  await page.screenshot({ path: OUT + `/classroom-guardian-note-35${TAG}-waiting.png`, fullPage: false });
}
note(`ERRORS ${JSON.stringify(errors.slice(0, 3))}`);
await ctx.close();
await browser.close();
