import { chromium } from "file:///D:/moodle/_cmdr_rescue_v3_1022/frontend/node_modules/playwright/index.mjs";
import fs from "node:fs";
const BASE = "http://127.0.0.1:14492";
const OUT = "D:/moodle/_cmdr_rescue_v3_1022/trial/results/20261022_v3_human_chrome";
const NL = String.fromCharCode(10);
const lines = [];
const note = (v) => { lines.push(v); fs.writeFileSync(OUT + "/classroom-presenter-hidden-22.txt", lines.join(NL) + NL, "utf8"); };
const browser = await chromium.launch({ headless: true });
for (const vp of [{ w: 430, h: 932, n: "phone" }, { w: 1280, h: 900, n: "desktop" }]) {
  const ctx = await browser.newContext({ viewport: { width: vp.w, height: vp.h }, deviceScaleFactor: 1 });
  await ctx.addInitScript(() => {
    if (!sessionStorage.getItem("__probe_booted")) { localStorage.clear(); sessionStorage.clear(); sessionStorage.setItem("__probe_booted", "1"); }
  });
  const page = await ctx.newPage();
  const errors = [];
  const sims = [];
  page.on("pageerror", (e) => errors.push(String(e).slice(0, 140)));
  page.on("response", (r) => { if (r.url().includes("/simulation/")) sims.push(r.status()); });
  await page.goto(BASE + "/revolution", { waitUntil: "networkidle", timeout: 45000 }).catch(() => {});
  await page.waitForTimeout(1400);
  await page.locator('[data-testid="rev-mobile-tab-trips"]').click(); await page.waitForTimeout(1100);
  await page.locator('[data-testid="rev-demo-session"]').click(); await page.waitForTimeout(3600);
  const presenter = await page.locator('[data-testid="rev-presenter"]').count();
  const clock = await page.locator('[data-testid="rev-classroom-clock"]').isVisible().catch(() => false);
  note(`${vp.n} PRESENTER_COUNT ${presenter} CLOCK_VISIBLE ${clock} SIM_HTTP ${JSON.stringify(sims)} ERRORS ${JSON.stringify(errors.slice(0, 3))}`);
  await ctx.close();
}
await browser.close();
