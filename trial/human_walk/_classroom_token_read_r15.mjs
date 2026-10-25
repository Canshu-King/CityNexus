import { chromium } from "file:///D:/moodle/_cmdr_rescue_v3_1022/frontend/node_modules/playwright/index.mjs";
import fs from "node:fs";
const BASE = "http://127.0.0.1:14492";
const OUT = "D:/moodle/_cmdr_rescue_v3_1022/trial/results/20261022_v3_human_chrome";
const NL = String.fromCharCode(10);
const lines = [];
const note = (v) => { lines.push(v); fs.writeFileSync(OUT + "/classroom-token-read-15.txt", lines.join(NL) + NL, "utf8"); };
const browser = await chromium.launch({ headless: true });
const ctx = await browser.newContext({ viewport: { width: 430, height: 932 }, deviceScaleFactor: 1 });
await ctx.addInitScript(() => {
  if (!sessionStorage.getItem("__probe_booted")) { localStorage.clear(); sessionStorage.clear(); sessionStorage.setItem("__probe_booted", "1"); }
});
const page = await ctx.newPage();
const errors = [];
const calls = [];
page.on("pageerror", (e) => errors.push(String(e).slice(0, 160)));
page.on("response", (r) => {
  const url = r.url();
  if (url.includes("/demo/simulation-clock/") || url.includes("/plans/") || url.includes("/twin")) {
    calls.push(`${url.split("/api/v1/")[1]} ${r.status()} auth=${Boolean(r.request().headers()["authorization"])}`);
  }
});
await page.goto(BASE + "/revolution", { waitUntil: "networkidle", timeout: 45000 }).catch(() => {});
await page.waitForTimeout(1200);
await page.locator('[data-testid="rev-mobile-tab-trips"]').click(); await page.waitForTimeout(1000);
await page.locator('[data-testid="rev-demo-session"]').click(); await page.waitForTimeout(3200);
const strip = page.locator('[data-testid="rev-classroom-clock"]');
await strip.scrollIntoViewIfNeeded().catch(() => {});
note("CLOCK " + JSON.stringify(await page.locator('[data-testid="rev-clock-virtual"]').innerText().catch(() => "")));
await page.locator('[data-testid="rev-clock-plus60"]').click();
await page.waitForTimeout(2000);
note("CLOCK_AFTER " + JSON.stringify(await page.locator('[data-testid="rev-clock-virtual"]').innerText().catch(() => "")));
await page.getByRole("button", { name: /行程守护/ }).first().click(); await page.waitForTimeout(2400);
note("PROPOSAL " + JSON.stringify(await page.locator('[data-testid="rev-guardian-proposal-diff"]').innerText().catch(() => "")));
note("CALLS " + JSON.stringify(calls.slice(0, 8)));
note("ERRORS " + JSON.stringify(errors.slice(0, 4)));
await page.screenshot({ path: OUT + "/rehearsal15-token.png" });
await browser.close();
