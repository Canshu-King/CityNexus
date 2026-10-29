import { chromium } from "file:///D:/moodle/_cmdr_rescue_v3_1022/frontend/node_modules/playwright/index.mjs";
import fs from "node:fs";

const BASE = "http://127.0.0.1:14492";
const DIR = "D:/moodle/_cmdr_rescue_v3_1022/trial/results/20261022_v3_human_chrome";
const OUT = DIR + "/dual-device-stale-135.txt";
const SHOT = DIR + "/classroom-dual-device-stale-135.png";
const NL = String.fromCharCode(10);
const lines = [];
const note = (value) => { lines.push(value); fs.writeFileSync(OUT, lines.join(NL) + NL, "utf8"); };
const raw = JSON.parse(fs.readFileSync("D:/moodle/_cmdr_v3_live_1022/.demo_pairing_ticket", "utf8"));
const tickets = (raw.tickets && raw.tickets.length ? raw.tickets : [raw.ticket]).filter(Boolean);

const browser = await chromium.launch({ headless: true });
const aCtx = await browser.newContext({ viewport: { width: 390, height: 844 }, deviceScaleFactor: 1 });
const bCtx = await browser.newContext({ viewport: { width: 1280, height: 900 }, deviceScaleFactor: 1 });
const a = await aCtx.newPage();
const b = await bCtx.newPage();
const errors = [];

async function enter(page, ticket) {
  await page.goto(`${BASE}/revolution#pair=${encodeURIComponent(ticket)}`, { waitUntil: "domcontentloaded", timeout: 60000 });
  await page.waitForTimeout(6500);
  const jump = page.getByRole("button", { name: /去课堂控制台/ }).first();
  if (await jump.count()) { await jump.click().catch(() => {}); await page.waitForTimeout(1000); }
}

async function statusLine(page) {
  return page.locator('[data-testid="rev-clock-virtual"]').first().textContent().catch(() => null);
}

await enter(a, tickets[0]);
const start = a.getByRole("button", { name: /开演（模拟两日）/ }).first();
note(`START_BUTTON ${await start.count()}`);
if (await start.count()) { await start.click().catch(() => {}); }
await a.waitForTimeout(2500);
note(`A_START ${JSON.stringify((await statusLine(a) || "").trim())}`);

await enter(b, tickets[1] || tickets[0]);
await b.waitForTimeout(3000);
note(`B_BEFORE ${JSON.stringify((await statusLine(b) || "").trim())}`);

// A advances; B still holds the old sequence and presses right away.
const plusA = a.locator('[data-testid="rev-clock-plus30"]').first();
await plusA.click().catch(() => {});
await a.waitForTimeout(400);
const plusB = b.locator('[data-testid="rev-clock-plus30"]').first();
await plusB.click().catch(() => {});
await b.waitForTimeout(2500);

const bNote = b.locator('[data-testid="rev-clock-next-note"]').first();
const bNoteText = (await bNote.textContent().catch(() => "")) || "";
note(`B_NOTE ${JSON.stringify(bNoteText.trim())}`);
note(`B_AFTER ${JSON.stringify((await statusLine(b) || "").trim())}`);
note(`A_AFTER ${JSON.stringify((await statusLine(a) || "").trim())}`);
await b.screenshot({ path: SHOT, fullPage: false });
note(`ERRORS ${JSON.stringify(errors.slice(0, 3))}`);
await browser.close();
