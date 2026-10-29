// Enter the classroom journey through the product's own resume key and look at the guardian panel.
import { chromium } from "file:///D:/moodle/_cmdr_rescue_v3_1022/frontend/node_modules/playwright/index.mjs";
import fs from "node:fs";

const BASE = "http://127.0.0.1:14491";
const OUT = "D:/moodle/_cmdr_rescue_v3_1022/trial/results/20261022_v3_human_chrome";
const JOURNEY = process.argv[2];
const lines = [];
function note(value) {
  lines.push(value);
  fs.writeFileSync(OUT + "/guardian-walk-2.txt", lines.join("\n") + "\n", "utf8");
}

const browser = await chromium.launch({ headless: true });
const context = await browser.newContext({ viewport: { width: 390, height: 844 }, deviceScaleFactor: 1 });
await context.addInitScript((journeyId) => {
  localStorage.setItem("citynexus.v8.journey_id", journeyId);
}, JOURNEY);
const page = await context.newPage();
const errors = [];
page.on("pageerror", (error) => errors.push("pageerror: " + String(error).slice(0, 200)));
await page.goto(BASE + "/revolution", { waitUntil: "networkidle", timeout: 45000 }).catch(() => {});
await page.waitForTimeout(3000);
note("URL " + page.url());
note("TEXT " + JSON.stringify((await page.evaluate(() => document.body.innerText)).slice(0, 2500)));
note("BUTTONS " + JSON.stringify(await page.evaluate(() => Array.from(document.querySelectorAll("button")).map((b) => ({ t: (b.textContent || "").trim(), id: b.dataset.testid || null })).filter((b) => b.t).slice(0, 50))));
note("ERRORS " + JSON.stringify(errors.slice(0, 6)));
await page.screenshot({ path: OUT + "/guardian-walk-2.png" });
await browser.close();
