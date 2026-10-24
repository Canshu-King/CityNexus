// First look at the isolated frontend: which entry points does the classroom journey offer?
import { chromium } from "file:///D:/moodle/_cmdr_rescue_v3_1022/frontend/node_modules/playwright/index.mjs";
import fs from "node:fs";

const BASE = "http://127.0.0.1:14491";
const OUT = "D:/moodle/_cmdr_rescue_v3_1022/trial/results/20261022_v3_human_chrome";
const lines = [];
function note(value) {
  lines.push(value);
  fs.writeFileSync(OUT + "/guardian-walk-1.txt", lines.join("\n") + "\n", "utf8");
}

const browser = await chromium.launch({ headless: true });
const context = await browser.newContext({ viewport: { width: 390, height: 844 }, deviceScaleFactor: 1 });
const page = await context.newPage();
const errors = [];
page.on("console", (message) => { if (message.type() === "error") errors.push(message.text().slice(0, 200)); });
page.on("pageerror", (error) => errors.push("pageerror: " + String(error).slice(0, 200)));

await page.goto(BASE + "/revolution", { waitUntil: "networkidle", timeout: 45000 }).catch(() => {});
await page.waitForTimeout(2500);
note("URL " + page.url());
note("TITLE " + (await page.title()));
note("TEXT " + JSON.stringify((await page.evaluate(() => document.body.innerText)).slice(0, 2500)));
note("BUTTONS " + JSON.stringify(await page.evaluate(() => Array.from(document.querySelectorAll("button")).map((b) => (b.textContent || "").trim()).filter(Boolean).slice(0, 40))));
note("STORAGE " + JSON.stringify(await page.evaluate(() => Object.fromEntries(Object.entries(localStorage).map(([k, v]) => [k, String(v).slice(0, 120)])))));
note("VIEWPORT " + JSON.stringify(await page.evaluate(() => ({ w: innerWidth, h: innerHeight, dpr: devicePixelRatio }))));
note("ERRORS " + JSON.stringify(errors.slice(0, 8)));
await page.screenshot({ path: OUT + "/guardian-walk-1.png" });
await browser.close();
