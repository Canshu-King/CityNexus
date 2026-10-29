// Classroom rehearsal, teacher's path on a tablet-sized fresh browser, timed step by step.
import { chromium } from "file:///D:/moodle/_cmdr_rescue_v3_1022/frontend/node_modules/playwright/index.mjs";
import fs from "node:fs";

const BASE = "http://127.0.0.1:14492";
const OUT = "D:/moodle/_cmdr_rescue_v3_1022/trial/results/20261022_v3_human_chrome";
const lines = [];
const started = Date.now();
function note(value) {
  lines.push(value);
  fs.writeFileSync(OUT + "/classroom-rehearsal-2.txt", lines.join("\n") + "\n", "utf8");
}
function mark(step) {
  note(`STEP ${step} t=${((Date.now() - started) / 1000).toFixed(1)}s`);
}

const browser = await chromium.launch({ headless: true });
const context = await browser.newContext({ viewport: { width: 430, height: 932 }, deviceScaleFactor: 1 });
await context.addInitScript(() => {
  if (!sessionStorage.getItem("__probe_booted")) {
    localStorage.clear();
    sessionStorage.clear();
    sessionStorage.setItem("__probe_booted", "1");
  }
});
const page = await context.newPage();
const errors = [];
page.on("pageerror", (error) => errors.push("pageerror: " + String(error).slice(0, 200)));

await page.goto(BASE + "/revolution", { waitUntil: "networkidle", timeout: 45000 }).catch(() => {});
await page.waitForTimeout(1500);
mark("open");
await page.screenshot({ path: OUT + "/rehearsal2-1-cold.png" });

await page.locator('[data-testid="rev-mobile-tab-trips"]').click();
await page.waitForTimeout(1200);
mark("trips");
await page.screenshot({ path: OUT + "/rehearsal2-2-trips.png" });

await page.locator('[data-testid="rev-demo-session"]').click();
await page.waitForTimeout(3500);
mark("demo-entry");
const entered = await page.evaluate(() => document.body.innerText);
note("ENTERED " + JSON.stringify(/行程守护|旅途正在继续/.test(entered)));
await page.screenshot({ path: OUT + "/rehearsal2-3-journey.png" });
if (!/行程守护|旅途正在继续/.test(entered)) {
  note("STOP not in cockpit: " + JSON.stringify(entered.slice(0, 400)));
  await browser.close();
  process.exit(1);
}

const guardian = page.getByRole("button", { name: /行程守护/ }).first();
await guardian.click().catch(() => {});
await page.waitForTimeout(2500);
mark("guardian");
const card = page.locator('[data-testid="rev-guardian-proposal"]');
note("PROPOSAL_VISIBLE " + JSON.stringify(await card.isVisible().catch(() => false)));
note("PROPOSAL_TEXT " + JSON.stringify(await page.locator('[data-testid="rev-guardian-proposal-diff"]').innerText().catch(() => "")));
await page.screenshot({ path: OUT + "/rehearsal2-4-proposal.png" });

const accept = page.locator('[data-testid="rev-guardian-accept-replan"]');
await accept.click();
mark("accept");
await page.waitForTimeout(6000);
let body = "";
for (let i = 0; i < 6; i++) {
  body = await page.evaluate(() => document.body.innerText);
  if (/第一站：|行程守护|旅途正在继续/.test(body)) break;
  await page.waitForTimeout(1500);
}
note("RELOAD_BODY_LEN " + JSON.stringify(body.length));
note("AFTER_FIRST_STOP " + JSON.stringify((body.split("第一站：")[1] || "").split(String.fromCharCode(10))[0]));
note("AFTER_NOW " + JSON.stringify((body.split("现在：")[1] || "").split(String.fromCharCode(10))[0]));
await page.screenshot({ path: OUT + "/rehearsal2-5-after.png" });
mark("after-reload");
note("TOTAL_S " + ((Date.now() - started) / 1000).toFixed(1));
note("ERRORS " + JSON.stringify(errors.slice(0, 6)));
await browser.close();
