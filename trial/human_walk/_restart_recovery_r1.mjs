// The restart case: only a signed bearer survives, no local journey pointer.
// 我的旅程 must list the ACTIVE journey and 继续这趟 must reopen it.
import { chromium } from "file:///D:/moodle/_cmdr_rescue_v3_1022/frontend/node_modules/playwright/index.mjs";
import fs from "node:fs";

const BASE = "http://127.0.0.1:14491";
const OUT = "D:/moodle/_cmdr_rescue_v3_1022/trial/results/20261022_v3_human_chrome";
const TRAVELER = process.env.TRAVELER_ID || "";
const TOKEN = process.env.SIM_TOKEN || "";
const lines = [];
function note(value) {
  lines.push(value);
  fs.writeFileSync(OUT + "/restart-recovery-1.txt", lines.join("\n") + "\n", "utf8");
}

const browser = await chromium.launch({ headless: true });
const context = await browser.newContext({ viewport: { width: 390, height: 844 }, deviceScaleFactor: 1 });
await context.addInitScript(({ token, travelerId }) => {
  sessionStorage.setItem("citynexus.traveler.bearer", token);
  sessionStorage.setItem("citynexus.traveler.session-id", travelerId);
  localStorage.removeItem("citynexus.v8.journey_id");
  localStorage.removeItem("citynexus.revolution.firstlook.journey");
}, { token: TOKEN, travelerId: TRAVELER });
const page = await context.newPage();
const errors = [];
page.on("pageerror", (error) => errors.push("pageerror: " + String(error).slice(0, 200)));
await page.goto(BASE + "/revolution", { waitUntil: "networkidle", timeout: 45000 }).catch(() => {});
await page.waitForTimeout(2000);
note("COLD_TEXT " + JSON.stringify((await page.evaluate(() => document.body.innerText)).slice(0, 300)));

await page.locator('[data-testid="rev-mobile-tab-trips"]').click().catch(() => {});
await page.waitForTimeout(2500);
const list = page.locator('[data-testid="rev-saved-trips"]');
note("LIST_VISIBLE " + JSON.stringify(await list.isVisible().catch(() => false)));
note("LIST_TEXT " + JSON.stringify(await list.innerText().catch(() => "")));
await page.screenshot({ path: OUT + "/restart-trips-390.png" });

const resume = page.locator('[data-testid="rev-trip-resume"]').first();
note("RESUME_COUNT " + JSON.stringify(await resume.count()));
await resume.click().catch(() => {});
await page.waitForTimeout(3500);
const body = await page.evaluate(() => document.body.innerText);
note("RESUMED_TEXT " + JSON.stringify(body.slice(0, 600)));
note("HAS_COCKPIT " + JSON.stringify(/行程守护|旅途正在继续/.test(body)));
note("ERRORS " + JSON.stringify(errors.slice(0, 6)));
await page.screenshot({ path: OUT + "/restart-resumed-390.png" });
await browser.close();
