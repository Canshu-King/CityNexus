import { chromium } from "file:///D:/moodle/_cmdr_rescue_v3_1022/frontend/node_modules/playwright/index.mjs";
import fs from "node:fs";
const BASE = process.env.SIM_BASE || "http://127.0.0.1:14494";
const TICKET = process.env.PAIR_TICKET || "";
const OUT = "D:/moodle/_cmdr_rescue_v3_1022/trial/results/20261022_v3_human_chrome";
const NL = String.fromCharCode(10);
const lines = [];
const note = (v) => { lines.push(v); fs.writeFileSync(OUT + "/classroom-resume-32.txt", lines.join(NL) + NL, "utf8"); };

const browser = await chromium.launch({ headless: true });
const ctx = await browser.newContext({ viewport: { width: 430, height: 932 }, deviceScaleFactor: 1 });
await ctx.addInitScript(() => {
  if (!sessionStorage.getItem("__probe_booted")) { localStorage.clear(); sessionStorage.clear(); sessionStorage.setItem("__probe_booted", "1"); }
});
const page = await ctx.newPage();
const errors = [];
page.on("pageerror", (e) => errors.push(String(e).slice(0, 140)));
const presenterState = async () => {
  const panel = page.locator('[data-testid="rev-presenter"]');
  const count = await panel.count();
  if (!count) return { present: false };
  return {
    present: true,
    status: (await page.locator('[data-testid="rev-presenter-run"]').innerText().catch(() => "")).replace(/\s+/g, " ").trim(),
    done: await page.locator('[data-testid="rev-presenter-done"]').count(),
    history: (await page.locator('[data-testid="rev-presenter-history"] li').allInnerTexts()).map((h) => h.replace(/\s+/g, " ").trim()),
  };
};
const entryError = async () =>
  (await page.locator('[data-testid="rev-demo-error"]').innerText().catch(() => "")).replace(/\s+/g, " ").trim();

await page.goto(`${BASE}/revolution#pair=${encodeURIComponent(TICKET)}`, { waitUntil: "networkidle", timeout: 60000 });
await page.waitForTimeout(4500);
note(`FIRST ${JSON.stringify(await presenterState())}`);
note(`FIRST_ERROR ${JSON.stringify(await entryError())}`);

await page.reload({ waitUntil: "networkidle", timeout: 60000 });
await page.waitForTimeout(4500);
note(`AFTER_RELOAD ${JSON.stringify(await presenterState())}`);
note(`RELOAD_ERROR ${JSON.stringify(await entryError())}`);

await page.locator('[data-testid="rev-mobile-tab-trips"]').click().catch(() => {});
await page.waitForTimeout(900);
await page.locator('[data-testid="rev-demo-session"]').click().catch(() => {});
await page.waitForTimeout(3600);
note(`AFTER_ENTRY_CLICK ${JSON.stringify(await presenterState())}`);
note(`ENTRY_CLICK_ERROR ${JSON.stringify(await entryError())}`);
await page.screenshot({ path: OUT + "/classroom-resume-32-phone.png", fullPage: false });
note(`ERRORS ${JSON.stringify(errors.slice(0, 3))}`);
await ctx.close();
await browser.close();
