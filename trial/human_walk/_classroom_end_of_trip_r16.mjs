import { chromium } from "file:///D:/moodle/_cmdr_rescue_v3_1022/frontend/node_modules/playwright/index.mjs";
import fs from "node:fs";
const BASE = "http://127.0.0.1:14492";
const OUT = "D:/moodle/_cmdr_rescue_v3_1022/trial/results/20261022_v3_human_chrome";
const NL = String.fromCharCode(10);
const lines = [];
const note = (v) => { lines.push(v); fs.writeFileSync(OUT + "/classroom-end-of-trip-16.txt", lines.join(NL) + NL, "utf8"); };
const browser = await chromium.launch({ headless: true });
const ctx = await browser.newContext({ viewport: { width: 430, height: 932 }, deviceScaleFactor: 1 });
await ctx.addInitScript(() => {
  if (!sessionStorage.getItem("__probe_booted")) { localStorage.clear(); sessionStorage.clear(); sessionStorage.setItem("__probe_booted", "1"); }
});
const page = await ctx.newPage();
const errors = [];
page.on("pageerror", (e) => errors.push(String(e).slice(0, 160)));
await page.goto(BASE + "/revolution", { waitUntil: "networkidle", timeout: 45000 }).catch(() => {});
await page.waitForTimeout(1200);
await page.locator('[data-testid="rev-mobile-tab-trips"]').click(); await page.waitForTimeout(1000);
await page.locator('[data-testid="rev-demo-session"]').click(); await page.waitForTimeout(3200);
const strip = page.locator('[data-testid="rev-classroom-clock"]');
await strip.scrollIntoViewIfNeeded().catch(() => {});
note("START " + JSON.stringify(await strip.innerText().catch(() => "")));
await page.locator('[data-testid="rev-clock-next"]').click();
await page.waitForTimeout(5000);
note("AFTER_1 " + JSON.stringify(await strip.innerText().catch(() => "")));
await page.locator('[data-testid="rev-clock-next"]').click();
await page.waitForTimeout(5000);
note("AFTER_2 " + JSON.stringify(await strip.innerText().catch(() => "")));
note("NOTE_2 " + JSON.stringify(await page.locator('[data-testid="rev-clock-next-note"]').innerText().catch(() => "")));
const status = await page.evaluate(async () => {
  const token = sessionStorage.getItem("citynexus.traveler.bearer");
  const response = await fetch("/api/v1/journeys/2e9cd67d-10ca-4ecd-920b-76c81a350c71", {
    headers: token ? { Authorization: "Bearer " + token } : {},
  });
  if (!response.ok) return { http: response.status };
  const body = await response.json();
  return { http: response.status, status: body.status, current_activity_id: body.current_activity_id };
});
note("JOURNEY " + JSON.stringify(status));
const body = await page.evaluate(() => document.body.innerText);
note("BODY_TAIL " + JSON.stringify((body.match(/(已完成|全部完成|行程结束|终点|SIMULATED)[^\n]*/g) || []).slice(0, 5)));
note("ERRORS " + JSON.stringify(errors.slice(0, 5)));
await page.screenshot({ path: OUT + "/rehearsal16-end.png" });
await browser.close();
