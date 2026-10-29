// A teacher on a fresh browser: no token, no pointer. The classroom entry must sign her in.
import { chromium } from "file:///D:/moodle/_cmdr_rescue_v3_1022/frontend/node_modules/playwright/index.mjs";
import fs from "node:fs";

const BASE = "http://127.0.0.1:14491";
const OUT = "D:/moodle/_cmdr_rescue_v3_1022/trial/results/20261022_v3_human_chrome";
const lines = [];
function note(value) {
  lines.push(value);
  fs.writeFileSync(OUT + "/demo-entry-1.txt", lines.join("\n") + "\n", "utf8");
}

const browser = await chromium.launch({ headless: true });
const context = await browser.newContext({ viewport: { width: 390, height: 844 }, deviceScaleFactor: 1 });
await context.addInitScript(() => {
  localStorage.clear();
  sessionStorage.clear();
});
const page = await context.newPage();
const errors = [];
page.on("pageerror", (error) => errors.push("pageerror: " + String(error).slice(0, 200)));
await page.goto(BASE + "/revolution", { waitUntil: "networkidle", timeout: 45000 }).catch(() => {});
await page.waitForTimeout(2000);
note("COLD_HAS_BEARER " + JSON.stringify(await page.evaluate(() => Boolean(sessionStorage.getItem("citynexus.traveler.bearer")))));

await page.locator('[data-testid="rev-mobile-tab-trips"]').click().catch(() => {});
await page.waitForTimeout(1500);
const demo = page.locator('[data-testid="rev-demo-session"]');
note("DEMO_BUTTON " + JSON.stringify(await demo.innerText().catch(() => "")));
await demo.click().catch(() => {});
await page.waitForTimeout(4500);
const body = await page.evaluate(() => document.body.innerText);
note("AFTER_TEXT " + JSON.stringify(body.slice(0, 700)));
note("HAS_COCKPIT " + JSON.stringify(/行程守护|旅途正在继续/.test(body)));
note("BEARER_AFTER " + JSON.stringify(await page.evaluate(() => Boolean(sessionStorage.getItem("citynexus.traveler.bearer")))));
note("ERRORS " + JSON.stringify(errors.slice(0, 6)));
await page.screenshot({ path: OUT + "/demo-entry-390.png" });
await browser.close();
