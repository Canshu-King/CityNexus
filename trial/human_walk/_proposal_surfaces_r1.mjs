// One decision surface on the phone, both surfaces on the desktop.
import { chromium } from "file:///D:/moodle/_cmdr_rescue_v3_1022/frontend/node_modules/playwright/index.mjs";
import fs from "node:fs";

const BASE = "http://127.0.0.1:14492";
const OUT = "D:/moodle/_cmdr_rescue_v3_1022/trial/results/20261022_v3_human_chrome";
const width = Number(process.argv[2] || 390);
const height = Number(process.argv[3] || 844);
const label = `${width}x${height}`;
const lines = [];
function note(value) {
  lines.push(value);
  fs.writeFileSync(OUT + `/proposal-surfaces-${label}.txt`, lines.join("\n") + "\n", "utf8");
}

const browser = await chromium.launch({ headless: true });
const context = await browser.newContext({ viewport: { width, height }, deviceScaleFactor: 1 });
await context.addInitScript(() => { localStorage.clear(); sessionStorage.clear(); });
const page = await context.newPage();
await page.goto(BASE + "/revolution", { waitUntil: "networkidle", timeout: 45000 }).catch(() => {});
await page.waitForTimeout(1500);
await page.locator('[data-testid="rev-mobile-tab-trips"]').click().catch(() => {});
await page.waitForTimeout(1200);
await page.locator('[data-testid="rev-demo-session"]').click().catch(() => {});
await page.waitForTimeout(3500);
note("VIEWPORT " + JSON.stringify(await page.evaluate(() => ({ w: innerWidth, h: innerHeight }))));
const guardian = page.getByRole("button", { name: /行程守护/ }).first();
await guardian.click().catch(() => {});
await page.waitForTimeout(2500);

const desktopCards = page.locator('[data-testid="live-proposal"]');
const total = await desktopCards.count();
let visible = 0;
for (let i = 0; i < total; i++) {
  if (await desktopCards.nth(i).isVisible().catch(() => false)) visible++;
}
const panelCard = page.locator('[data-testid="rev-guardian-proposal"]');
note("LIVE_PROPOSAL_TOTAL " + JSON.stringify(total));
note("LIVE_PROPOSAL_VISIBLE " + JSON.stringify(visible));
note("PANEL_PROPOSAL_VISIBLE " + JSON.stringify(await panelCard.isVisible().catch(() => false)));
note("PANEL_TEXT " + JSON.stringify(await page.locator('[data-testid="rev-guardian-proposal-diff"]').innerText().catch(() => "")));
await page.screenshot({ path: OUT + `/proposal-surfaces-${label}.png` });
await browser.close();
