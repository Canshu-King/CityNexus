import { chromium } from "file:///D:/moodle/_cmdr_rescue_v3_1022/frontend/node_modules/playwright/index.mjs";
import fs from "node:fs";
const BASE = "http://127.0.0.1:14492";
const OUT = "D:/moodle/_cmdr_rescue_v3_1022/trial/results/20261022_v3_human_chrome";
const NL = String.fromCharCode(10);
const lines = [];
const note = (v) => { lines.push(v); fs.writeFileSync(OUT + "/classroom-after-finish-17.txt", lines.join(NL) + NL, "utf8"); };
const browser = await chromium.launch({ headless: true });
const ctx = await browser.newContext({ viewport: { width: 430, height: 932 }, deviceScaleFactor: 1 });
await ctx.addInitScript(() => {
  if (!sessionStorage.getItem("__probe_booted")) { localStorage.clear(); sessionStorage.clear(); sessionStorage.setItem("__probe_booted", "1"); }
});
const page = await ctx.newPage();
const errors = [];
const calls = [];
page.on("pageerror", (e) => errors.push(String(e).slice(0, 160)));
page.on("response", (r) => { if (r.url().includes("/demo/session")) calls.push(`${r.status()}`); });
await page.goto(BASE + "/revolution", { waitUntil: "networkidle", timeout: 45000 }).catch(() => {});
await page.waitForTimeout(1500);
await page.locator('[data-testid="rev-mobile-tab-trips"]').click(); await page.waitForTimeout(1600);
const body = await page.evaluate(() => document.body.innerText);
note("TRIPS_HAS_TITLE " + JSON.stringify(/北京 · 2日行程/.test(body)));
note("TRIPS_HAS_DEMO " + JSON.stringify(/课堂演示/.test(body)));
note("TRIPS_LINES " + JSON.stringify((body.match(/(北京[^\n]*|课堂演示[^\n]*|已出发[^\n]*|已完成[^\n]*)/g) || []).slice(0, 8)));
if (await page.locator('[data-testid="rev-demo-session"]').count()) {
  await page.locator('[data-testid="rev-demo-session"]').click();
  await page.waitForTimeout(3500);
  const after = await page.evaluate(() => document.body.innerText);
  note("AFTER_DEMO_CLICK " + JSON.stringify(after.slice(0, 200)));
  note("AFTER_HAS_ERROR " + JSON.stringify(/(失败|错误|不可|没有|404|409)/.test(after)));
}
note("DEMO_SESSION_HTTP " + JSON.stringify(calls));
note("ERRORS " + JSON.stringify(errors.slice(0, 5)));
await page.screenshot({ path: OUT + "/rehearsal17-after-finish.png" });
await browser.close();
