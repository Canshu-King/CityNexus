import { chromium } from "file:///D:/moodle/_cmdr_rescue_v3_1022/frontend/node_modules/playwright/index.mjs";
import fs from "node:fs";
const BASE = "http://127.0.0.1:14492";
const OUT = "D:/moodle/_cmdr_rescue_v3_1022/trial/results/20261022_v3_human_chrome";
const NL = String.fromCharCode(10);
const lines = [];
const note = (v) => { lines.push(v); fs.writeFileSync(OUT + "/classroom-guard-regression-18.txt", lines.join(NL) + NL, "utf8"); };
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
await page.locator('[data-testid="rev-mobile-tab-trips"]').click(); await page.waitForTimeout(1200);
await page.locator('[data-testid="rev-demo-session"]').click(); await page.waitForTimeout(3800);
const body = await page.evaluate(() => document.body.innerText);
note("ENTERED_TITLE " + JSON.stringify(/北京 · 2日行程/.test(body)));
note("ENTERED_STOP " + JSON.stringify(/第一站|故宫博物院/.test(body)));
note("ERROR_VISIBLE " + JSON.stringify(await page.locator('[data-testid="rev-demo-error"]').innerText().catch(() => "")));
note("HAS_EMPTY_PLAN " + JSON.stringify(/0 项安排/.test(body)));
note("ERRORS " + JSON.stringify(errors.slice(0, 4)));
await page.screenshot({ path: OUT + "/rehearsal18-guard-regression.png" });
await browser.close();
