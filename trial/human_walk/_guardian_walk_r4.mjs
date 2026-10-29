// Walk the classroom journey as its owner: open the guardian panel and read the pending proposal.
import { chromium } from "file:///D:/moodle/_cmdr_rescue_v3_1022/frontend/node_modules/playwright/index.mjs";
import fs from "node:fs";

const BASE = "http://127.0.0.1:14491";
const OUT = "D:/moodle/_cmdr_rescue_v3_1022/trial/results/20261022_v3_human_chrome";
const JOURNEY = process.argv[2];
const TRAVELER = process.env.TRAVELER_ID || "";
const TOKEN = process.env.SIM_TOKEN || "";
const lines = [];
function note(value) {
  lines.push(value);
  fs.writeFileSync(OUT + "/guardian-walk-4.txt", lines.join("\n") + "\n", "utf8");
}

const browser = await chromium.launch({ headless: true });
const context = await browser.newContext({ viewport: { width: 390, height: 844 }, deviceScaleFactor: 1 });
await context.addInitScript(({ journeyId, token, travelerId }) => {
  localStorage.setItem("citynexus.v8.journey_id", journeyId);
  sessionStorage.setItem("citynexus.traveler.bearer", token);
  sessionStorage.setItem("citynexus.traveler.session-id", travelerId);
}, { journeyId: JOURNEY, token: TOKEN, travelerId: TRAVELER });
const page = await context.newPage();
const errors = [];
page.on("pageerror", (error) => errors.push("pageerror: " + String(error).slice(0, 200)));
await page.goto(BASE + "/revolution", { waitUntil: "networkidle", timeout: 45000 }).catch(() => {});
await page.waitForTimeout(3500);

let text = await page.evaluate(() => document.body.innerText);
note("STEP1_URL " + page.url());
note("STEP1_TEXT " + JSON.stringify(text.slice(0, 1200)));
if (!/行程守护/.test(text)) {
  await page.locator('[data-testid="rev-mobile-tab-trips"]').click().catch(() => {});
  await page.waitForTimeout(2500);
  text = await page.evaluate(() => document.body.innerText);
  note("STEP2_TEXT " + JSON.stringify(text.slice(0, 1200)));
  const card = page.getByText("北京 · 2日行程", { exact: false }).first();
  if (await card.count()) {
    await card.click().catch(() => {});
    await page.waitForTimeout(3000);
    text = await page.evaluate(() => document.body.innerText);
    note("STEP3_TEXT " + JSON.stringify(text.slice(0, 1200)));
  }
}

const guardian = page.getByRole("button", { name: /行程守护/ }).first();
note("GUARDIAN_BUTTON " + JSON.stringify(await guardian.count()));
await guardian.click().catch(() => {});
await page.waitForTimeout(2500);
const proposal = page.locator('[data-testid="rev-guardian-proposal"]');
note("PROPOSAL_VISIBLE " + JSON.stringify(await proposal.isVisible().catch(() => false)));
note("PROPOSAL_TEXT " + JSON.stringify(await proposal.innerText().catch(() => "")));
note("DIFF_TEXT " + JSON.stringify(await page.locator('[data-testid="rev-guardian-proposal-diff"]').innerText().catch(() => "")));
note("ACCEPT_BUTTON " + JSON.stringify(await page.locator('[data-testid="rev-guardian-accept-replan"]').innerText().catch(() => "")));
note("ERRORS " + JSON.stringify(errors.slice(0, 6)));
await page.screenshot({ path: OUT + "/guardian-panel-390.png" });
await page.locator('[data-testid="rev-guardian-proposal"]').scrollIntoViewIfNeeded().catch(() => {});
await page.screenshot({ path: OUT + "/guardian-proposal-390.png" });
await browser.close();
