import { chromium } from "file:///D:/moodle/_cmdr_rescue_v3_1022/frontend/node_modules/playwright/index.mjs";
import fs from "node:fs";

const BASE = "http://127.0.0.1:14492";
const OUT = "D:/moodle/_cmdr_rescue_v3_1022/trial/results/20261022_v3_human_chrome/two-screen-sync-102.txt";
const SHOT = "D:/moodle/_cmdr_rescue_v3_1022/trial/results/20261022_v3_human_chrome/classroom-two-screen-102.png";
const TICKET_FILE = "D:/moodle/_cmdr_v3_live_1022/.demo_pairing_ticket";
const NL = String.fromCharCode(10);
const lines = [];
const note = (value) => { lines.push(value); fs.writeFileSync(OUT, lines.join(NL) + NL, "utf8"); };
const raw = JSON.parse(fs.readFileSync(TICKET_FILE, "utf8"));
const tickets = (raw.tickets && raw.tickets.length ? raw.tickets : [raw.ticket]).filter(Boolean);

const browser = await chromium.launch({ headless: true });

async function open(width, height, ticket) {
  const ctx = await browser.newContext({ viewport: { width, height }, deviceScaleFactor: 1 });
  const page = await ctx.newPage();
  const errors = [];
  page.on("pageerror", (error) => errors.push(String(error).slice(0, 120)));
  await page.goto(`${BASE}/revolution#pair=${encodeURIComponent(ticket)}`, { waitUntil: "networkidle", timeout: 60000 });
  await page.waitForTimeout(5200);
  const jump = page.locator('[data-testid="rev-jump-clock"]').first();
  if (await jump.count()) { await jump.click().catch(() => {}); await page.waitForTimeout(1400); }
  return { ctx, page, errors };
}

async function read(page) {
  return page.evaluate(() => {
    const pick = (id) => {
      const node = document.querySelector(`[data-testid="${id}"]`);
      return node ? node.textContent : null;
    };
    return { virtual: pick("rev-clock-virtual"), run: pick("rev-presenter-run") };
  });
}

const phone = await open(390, 844, tickets[0]);
const start = phone.page.getByRole("button", { name: /开演/ }).first();
note(`PHONE_START_BUTTON ${await start.count()}`);
if (await start.count()) { await start.scrollIntoViewIfNeeded().catch(() => {}); await start.click().catch(() => {}); }
await phone.page.waitForTimeout(5200);
note(`PHONE_AFTER_START ${JSON.stringify(await read(phone.page))}`);

const projector = await open(1280, 900, tickets[1] || tickets[0]);
note(`PROJECTOR_INITIAL ${JSON.stringify(await read(projector.page))}`);

const plus = phone.page.locator('[data-testid="rev-clock-plus30"]').first();
note(`PHONE_PLUS30 ${await plus.count()} disabled=${await plus.isDisabled().catch(() => null)}`);
if (await plus.count()) { await plus.scrollIntoViewIfNeeded().catch(() => {}); await plus.click().catch(() => {}); }
await phone.page.waitForTimeout(3500);
note(`PHONE_AFTER_PLUS ${JSON.stringify(await read(phone.page))}`);

let synced = null;
for (let tick = 0; tick < 8; tick += 1) {
  await projector.page.waitForTimeout(2500);
  const reading = await read(projector.page);
  if (tick === 0 || reading.virtual !== null) note(`PROJECTOR_POLL ${tick} ${JSON.stringify(reading)}`);
  if (reading.virtual && reading.virtual.includes("09:30")) { synced = reading; break; }
}
note(`PROJECTOR_SYNCED ${JSON.stringify(synced)}`);
note(`PHONE_ERRORS ${JSON.stringify(phone.errors.slice(0, 2))}`);
note(`PROJECTOR_ERRORS ${JSON.stringify(projector.errors.slice(0, 2))}`);
await phone.page.screenshot({ path: SHOT.replace(".png", "-phone.png"), fullPage: false });
await projector.page.screenshot({ path: SHOT, fullPage: false });
await phone.ctx.close();
await projector.ctx.close();
await browser.close();
