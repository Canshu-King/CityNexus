import { chromium } from "file:///D:/moodle/_cmdr_rescue_v3_1022/frontend/node_modules/playwright/index.mjs";
import fs from "node:fs";

const BASE = "http://127.0.0.1:14492";
const OUT = "D:/moodle/_cmdr_rescue_v3_1022/trial/results/20261022_v3_human_chrome/guardian-panel-no-run-88.txt";
const SHOT = "D:/moodle/_cmdr_rescue_v3_1022/trial/results/20261022_v3_human_chrome/classroom-guardian-panel-88.png";
const TICKET_FILE = "D:/moodle/_cmdr_v3_live_1022/.demo_pairing_ticket";
const NL = String.fromCharCode(10);
const lines = [];
const note = (value) => { lines.push(value); fs.writeFileSync(OUT, lines.join(NL) + NL, "utf8"); };
const raw = JSON.parse(fs.readFileSync(TICKET_FILE, "utf8"));
const tickets = (raw.tickets && raw.tickets.length ? raw.tickets : [raw.ticket]).filter(Boolean);

const browser = await chromium.launch({ headless: true });
const ctx = await browser.newContext({ viewport: { width: 390, height: 844 }, deviceScaleFactor: 1 });
const page = await ctx.newPage();
const errors = [];
const responses = [];
page.on("pageerror", (error) => errors.push(String(error).slice(0, 160)));
page.on("response", (response) => {
  const url = response.url();
  if (/simulation|replans/.test(url)) responses.push(`${response.status()} ${url.replace(/^https?:\/\/[^/]+/, "")}`);
});

await page.goto(`${BASE}/revolution#pair=${encodeURIComponent(tickets[0])}`, { waitUntil: "networkidle", timeout: 60000 });
await page.waitForTimeout(5000);
const guardianTab = page.getByRole("button", { name: "行程守护", exact: true }).first();
note(`GUARDIAN_TAB ${await guardianTab.count()}`);
if (await guardianTab.count()) {
  await guardianTab.scrollIntoViewIfNeeded().catch(() => {});
  await guardianTab.click().catch(() => {});
  await page.waitForTimeout(6000);
}
const diff = page.locator('[data-testid="rev-guardian-proposal-diff"]');
const origin = page.locator('[data-testid="rev-guardian-proposal-origin"]');
const accept = page.locator('[data-testid="rev-guardian-accept-replan"]');
const panel = page.locator('[data-testid="rev-guardian-reality-panel"]');
note(`PANEL ${await panel.count()} PROPOSAL ${await diff.count()} ACCEPT ${await accept.count()}`);
note(`DIFF ${JSON.stringify(await diff.first().textContent().catch(() => null))}`);
note(`ORIGIN ${JSON.stringify(await origin.first().textContent().catch(() => null))}`);
const rect = await accept.first().boundingBox().catch(() => null);
const hit = await page.evaluate(() => {
  const node = document.querySelector('[data-testid="rev-guardian-accept-replan"]');
  if (!node) return null;
  const box = node.getBoundingClientRect();
  const target = document.elementFromPoint(Math.round(box.left + box.width / 2), Math.round(box.top + box.height / 2));
  return { hitSelf: Boolean(target && (target === node || node.contains(target))), top: Math.round(box.top), inView: box.top >= 0 && box.bottom <= window.innerHeight };
}).catch(() => null);
note(`ACCEPT_BOX ${JSON.stringify({ rect, hit })}`);
note(`RESPONSES ${JSON.stringify(responses.slice(-8))}`);
note(`ERRORS ${JSON.stringify(errors.slice(0, 3))}`);
await page.screenshot({ path: SHOT, fullPage: false });
await browser.close();
