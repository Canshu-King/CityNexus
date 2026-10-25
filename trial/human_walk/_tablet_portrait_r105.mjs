import { chromium } from "file:///D:/moodle/_cmdr_rescue_v3_1022/frontend/node_modules/playwright/index.mjs";
import fs from "node:fs";

const BASE = "http://127.0.0.1:14492";
const OUT = "D:/moodle/_cmdr_rescue_v3_1022/trial/results/20261022_v3_human_chrome/tablet-portrait-105.txt";
const SHOT = "D:/moodle/_cmdr_rescue_v3_1022/trial/results/20261022_v3_human_chrome/classroom-tablet-portrait-105.png";
const TICKET_FILE = "D:/moodle/_cmdr_v3_live_1022/.demo_pairing_ticket";
const NL = String.fromCharCode(10);
const lines = [];
const note = (value) => { lines.push(value); fs.writeFileSync(OUT, lines.join(NL) + NL, "utf8"); };
const raw = JSON.parse(fs.readFileSync(TICKET_FILE, "utf8"));
const tickets = (raw.tickets && raw.tickets.length ? raw.tickets : [raw.ticket]).filter(Boolean);

const browser = await chromium.launch({ headless: true });
const ctx = await browser.newContext({ viewport: { width: 768, height: 1024 }, deviceScaleFactor: 1 });
const page = await ctx.newPage();
const errors = [];
page.on("pageerror", (error) => errors.push(String(error).slice(0, 160)));

await page.goto(`${BASE}/revolution#pair=${encodeURIComponent(tickets[0])}`, { waitUntil: "networkidle", timeout: 60000 });
await page.waitForTimeout(5200);

const before = await page.evaluate(() => {
  const node = document.querySelector('[data-testid="rev-jump-clock"]');
  const rect = node ? node.getBoundingClientRect() : null;
  return { scrollY: Math.round(window.scrollY), jump: Boolean(node), top: rect ? Math.round(rect.top) : null,
           left: rect ? Math.round(rect.left) : null };
});
note(`BEFORE ${JSON.stringify(before)}`);
const jump = page.locator('[data-testid="rev-jump-clock"]').first();
if (await jump.count()) { await jump.click().catch(() => {}); await page.waitForTimeout(1800); }

const after = await page.evaluate(() => {
  const readBox = (id) => {
    const node = document.querySelector(`[data-testid="${id}"]`);
    if (!node) return null;
    const rect = node.getBoundingClientRect();
    const hit = document.elementFromPoint(
      Math.round(rect.left + Math.min(rect.width / 2, 40)),
      Math.round(rect.top + Math.min(rect.height / 2, 20)),
    );
    return {
      top: Math.round(rect.top), left: Math.round(rect.left), right: Math.round(rect.right),
      w: Math.round(rect.width), h: Math.round(rect.height),
      inView: rect.top >= -4 && rect.bottom <= window.innerHeight + 4
        && rect.left >= -4 && rect.right <= window.innerWidth + 4,
      hitSelf: Boolean(node && hit && (hit === node || node.contains(hit))),
    };
  };
  const spatial = document.querySelector(".cn-mission-spatial");
  return {
    scrollY: Math.round(window.scrollY),
    spatialScrollLeft: spatial ? Math.round(spatial.scrollLeft) : null,
    clock: readBox("rev-classroom-clock"),
    start: (() => {
      const buttons = Array.from(document.querySelectorAll("button")).filter((item) => /开演/.test(item.textContent || ""));
      const node = buttons[0];
      if (!node) return null;
      const rect = node.getBoundingClientRect();
      const hit = document.elementFromPoint(Math.round(rect.left + rect.width / 2), Math.round(rect.top + rect.height / 2));
      return { top: Math.round(rect.top), left: Math.round(rect.left), w: Math.round(rect.width), h: Math.round(rect.height),
               inView: rect.top >= 0 && rect.bottom <= window.innerHeight && rect.left >= 0 && rect.right <= window.innerWidth,
               hitSelf: Boolean(hit && (hit === node || node.contains(hit))) };
    })(),
  };
});
note(`AFTER_JUMP ${JSON.stringify(after)}`);
if (after.start && after.start.inView && after.start.hitSelf) {
  await page.getByRole("button", { name: /开演/ }).first().click().catch(() => {});
  await page.waitForTimeout(5200);
}
const runText = await page.locator('[data-testid="rev-presenter-run"]').first().innerText().catch(() => null);
note(`RUN ${JSON.stringify(runText)}`);
note(`ERRORS ${JSON.stringify(errors.slice(0, 3))}`);
await page.screenshot({ path: SHOT, fullPage: false });
await browser.close();
