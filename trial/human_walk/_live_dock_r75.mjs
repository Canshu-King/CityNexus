import { chromium } from "file:///D:/moodle/_cmdr_rescue_v3_1022/frontend/node_modules/playwright/index.mjs";
import fs from "node:fs";

const BASE = "http://127.0.0.1:14492";
const OUT = "D:/moodle/_cmdr_rescue_v3_1022/trial/results/20261022_v3_human_chrome/live-dock-75.txt";
const TICKET_FILE = "D:/moodle/_cmdr_v3_live_1022/.demo_pairing_ticket";
const NL = String.fromCharCode(10);
const lines = [];
const note = (value) => { lines.push(value); fs.writeFileSync(OUT, lines.join(NL) + NL, "utf8"); };
const raw = JSON.parse(fs.readFileSync(TICKET_FILE, "utf8"));
const allTickets = (raw.tickets && raw.tickets.length ? raw.tickets : [raw.ticket]).filter(Boolean);
// Each pairing ticket is one-use; a second probe in the same scene starts later in the file.
const OFFSET = Number(process.env.PAIR_TICKET_OFFSET || 0);
const tickets = allTickets.slice(OFFSET);
note(`TICKETS ${tickets.length} OFFSET ${OFFSET}`);

const browser = await chromium.launch({ headless: true });

async function probe(width, height, ticket, label) {
  const ctx = await browser.newContext({ viewport: { width, height }, deviceScaleFactor: 1 });
  const page = await ctx.newPage();
  const errors = [];
  page.on("pageerror", (error) => errors.push(String(error).slice(0, 120)));
  await page.goto(`${BASE}/revolution#pair=${encodeURIComponent(ticket)}`, { waitUntil: "networkidle", timeout: 60000 });
  await page.waitForTimeout(4800);
  if (!(await page.locator('[data-testid="rev-classroom-clock"]').count())) {
    await page.locator('[data-testid="rev-mobile-tab-trips"]').click().catch(() => {});
    await page.waitForTimeout(1200);
  }
  await page.locator('[data-testid="rev-clock-plus30"]').first().scrollIntoViewIfNeeded().catch(() => {});
  await page.waitForTimeout(400);
  const info = await page.evaluate(() => {
    const dock = document.querySelector(".rev-mission-chat-dock");
    const btn = document.querySelector('[data-testid="rev-clock-plus30"]');
    let hit = null;
    let top = null;
    let box = null;
    if (btn) {
      const rect = btn.getBoundingClientRect();
      const el = document.elementFromPoint(rect.left + rect.width / 2, rect.top + rect.height / 2);
      hit = Boolean(el && (el === btn || btn.contains(el)));
      top = el ? el.tagName + "." + String(el.className || "").slice(0, 30) : "";
      box = { x: Math.round(rect.x), y: Math.round(rect.y) };
    }
    return {
      scrollY: Math.round(window.scrollY),
      docHeight: Math.round(document.documentElement.scrollHeight),
      clock: Boolean(document.querySelector('[data-testid="rev-classroom-clock"]')),
      dock: dock ? getComputedStyle(dock).display : "absent",
      hit,
      top,
      plus30: box,
    };
  });
  note(`${label} ${JSON.stringify(info)}`);
  note(`${label}_ERRORS ${JSON.stringify(errors.slice(0, 2))}`);
  await page.locator('[data-testid="rev-classroom-clock"]').first().scrollIntoViewIfNeeded().catch(() => {});
  await page.screenshot({ path: `D:/moodle/_cmdr_rescue_v3_1022/trial/results/20261022_v3_human_chrome/classroom-live-${label.toLowerCase()}-75.png`, fullPage: false });
  await ctx.close();
}

await probe(390, 844, tickets[0], "PHONE");
await probe(1024, 768, tickets[1] || tickets[0], "TABLET");await browser.close();
