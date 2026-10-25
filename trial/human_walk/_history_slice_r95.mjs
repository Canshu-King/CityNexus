import { chromium } from "file:///D:/moodle/_cmdr_rescue_v3_1022/frontend/node_modules/playwright/index.mjs";
import fs from "node:fs";

const BASE = "http://127.0.0.1:14492";
const OUT = "D:/moodle/_cmdr_rescue_v3_1022/trial/results/20261022_v3_human_chrome/history-slice-95.txt";
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
page.on("pageerror", (error) => errors.push(String(error).slice(0, 160)));

await page.goto(`${BASE}/revolution#pair=${encodeURIComponent(tickets[0])}`, { waitUntil: "networkidle", timeout: 60000 });
await page.waitForTimeout(5200);
const jump = page.locator('[data-testid="rev-jump-clock"]').first();
if (await jump.count()) { await jump.click().catch(() => {}); await page.waitForTimeout(1500); }
const start = page.getByRole("button", { name: /开演/ }).first();
if (await start.count()) { await start.scrollIntoViewIfNeeded().catch(() => {}); await start.click().catch(() => {}); }
await page.waitForTimeout(4500);

for (let index = 0; index < 4; index += 1) {
  const plus = page.locator('[data-testid="rev-clock-plus30"]').first();
  if (!(await plus.count())) break;
  await plus.scrollIntoViewIfNeeded().catch(() => {});
  await plus.click().catch(() => {});
  await page.waitForTimeout(2200);
}

const read = await page.evaluate(async () => {
  const node = document.querySelector('[data-testid="rev-presenter-history"]');
  const items = node ? Array.from(node.querySelectorAll("li")).map((item) => item.textContent) : [];
  const token = sessionStorage.getItem("citynexus.traveler.bearer");
  const jid = localStorage.getItem("citynexus.v8.journey_id");
  let historyLength = null;
  let events = null;
  if (token && jid) {
    const current = await fetch(`/api/v1/journeys/${jid}/simulation/runs/current`, {
      headers: { Accept: "application/json", Authorization: `Bearer ${token}` }, cache: "no-store",
    }).then((response) => (response.ok ? response.json() : null)).catch(() => null);
    historyLength = current && current.history ? current.history.length : null;
    events = current && current.history ? current.history.map((item) => item.event) : null;
  }
  return { li_count: items.length, items, historyLength, events };
});
note(`SCREEN ${JSON.stringify(read)}`);
note(`ERRORS ${JSON.stringify(errors.slice(0, 3))}`);
await browser.close();
