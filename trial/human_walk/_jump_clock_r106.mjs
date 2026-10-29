import { chromium } from "file:///D:/moodle/_cmdr_rescue_v3_1022/frontend/node_modules/playwright/index.mjs";
import fs from "node:fs";

const BASE = "http://127.0.0.1:14492";
const OUT = "D:/moodle/_cmdr_rescue_v3_1022/trial/results/20261022_v3_human_chrome/jump-clock-106.txt";
const TICKET_FILE = "D:/moodle/_cmdr_v3_live_1022/.demo_pairing_ticket";
const NL = String.fromCharCode(10);
const lines = [];
const note = (value) => { lines.push(value); fs.writeFileSync(OUT, lines.join(NL) + NL, "utf8"); };
const raw = JSON.parse(fs.readFileSync(TICKET_FILE, "utf8"));
const tickets = (raw.tickets && raw.tickets.length ? raw.tickets : [raw.ticket]).filter(Boolean);

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
  const jump = page.locator('[data-testid="rev-jump-clock"]').first();
  const before = await page.evaluate(() => {
    const node = document.querySelector('[data-testid="rev-jump-clock"]');
    const rect = node ? node.getBoundingClientRect() : null;
    const hit = rect
      ? document.elementFromPoint(Math.round(rect.left + rect.width / 2), Math.round(rect.top + rect.height / 2))
      : null;
    return {
      scrollY: Math.round(window.scrollY),
      jump: Boolean(node),
      text: node ? node.textContent : null,
      top: rect ? Math.round(rect.top) : null,
      inView: rect ? rect.top >= 0 && rect.bottom <= window.innerHeight : false,
      hitSelf: Boolean(node && hit && (hit === node || node.contains(hit))),
    };
  });
  note(`${label}_BEFORE ${JSON.stringify(before)}`);
  await page.screenshot({ path: `D:/moodle/_cmdr_rescue_v3_1022/trial/results/20261022_v3_human_chrome/classroom-jump-106-${label.toLowerCase()}-before-106.png`, fullPage: false });
  if (!(await jump.count())) { note(`${label}_JUMP_ABSENT`); await ctx.close(); return; }
  await jump.scrollIntoViewIfNeeded().catch(() => {});
  await page.waitForTimeout(200);
  await jump.click().catch(() => {});
  await page.waitForTimeout(1200);
  const after = await page.evaluate(() => {
    const clock = document.querySelector('[data-testid="rev-classroom-clock"]');
    const rect = clock ? clock.getBoundingClientRect() : null;
    return {
      scrollY: Math.round(window.scrollY),
      clockTop: rect ? Math.round(rect.top) : null,
      clockInView: rect ? rect.top >= -4 && rect.top < window.innerHeight * 0.6 : false,
    };
  });
  note(`${label}_AFTER ${JSON.stringify(after)}`);
  note(`${label}_ERRORS ${JSON.stringify(errors.slice(0, 2))}`);
  await page.screenshot({ path: `D:/moodle/_cmdr_rescue_v3_1022/trial/results/20261022_v3_human_chrome/classroom-jump-106-${label.toLowerCase()}-106.png`, fullPage: false });
  await ctx.close();
}

await probe(390, 844, tickets[0], "PHONE");
await probe(1024, 768, tickets[1] || tickets[0], "TABLET");
await probe(1280, 900, tickets[2] || tickets[0], "PROJECTOR");
await browser.close();
