import { chromium } from "file:///D:/moodle/_cmdr_rescue_v3_1022/frontend/node_modules/playwright/index.mjs";
import fs from "node:fs";

const BASE = "http://127.0.0.1:14492";
const OUT = "D:/moodle/_cmdr_rescue_v3_1022/trial/results/20261022_v3_human_chrome/clock-next-hit-122.txt";
const raw = JSON.parse(fs.readFileSync("D:/moodle/_cmdr_v3_live_1022/.demo_pairing_ticket", "utf8"));
const tickets = (raw.tickets && raw.tickets.length ? raw.tickets : [raw.ticket]).filter(Boolean);
const lines = [];
const note = (value) => { lines.push(value); fs.writeFileSync(OUT, lines.join(String.fromCharCode(10)) + String.fromCharCode(10), "utf8"); };

const browser = await chromium.launch({ headless: true });
const ctx = await browser.newContext({ viewport: { width: 1024, height: 768 }, deviceScaleFactor: 1 });
const page = await ctx.newPage();
await page.goto(`${BASE}/revolution#pair=${encodeURIComponent(tickets[0])}`, { waitUntil: "networkidle", timeout: 60000 });
await page.waitForTimeout(5200);
const jump = page.getByRole("button", { name: /去课堂控制台/ }).first();
if (await jump.count()) { await jump.click().catch(() => {}); await page.waitForTimeout(1200); }
const start = page.getByRole("button", { name: /开演（模拟两日）/ }).first();
if (await start.count()) { await start.click().catch(() => {}); await page.waitForTimeout(3000); }
const next = page.locator('[data-testid="rev-clock-next"]').first();
note(`COUNT ${await next.count()}`);
if (await next.count()) {
  await next.scrollIntoViewIfNeeded().catch(() => {});
  await page.waitForTimeout(500);
  const probe = await next.evaluate((node) => {
    const box = node.getBoundingClientRect();
    const x = box.left + box.width / 2;
    const y = box.top + box.height / 2;
    const top = document.elementFromPoint(x, y);
    return {
      rect: { left: Math.round(box.left), top: Math.round(box.top), width: Math.round(box.width), height: Math.round(box.height) },
      disabled: node.disabled === true,
      text: (node.textContent || "").trim(),
      hitTag: top ? top.tagName : null,
      hitTestId: top ? (top.getAttribute("data-testid") || "") : null,
      hitText: top ? (top.textContent || "").trim().slice(0, 40) : null,
      hitSelf: Boolean(top) && (node === top || node.contains(top)),
      viewport: { w: window.innerWidth, h: window.innerHeight },
      dockRect: (() => {
        const dock = document.querySelector('[data-testid="rev-mobile-dock"]');
        if (!dock) return null;
        const b = dock.getBoundingClientRect();
        return { top: Math.round(b.top), height: Math.round(b.height) };
      })(),
    };
  });
  note(`PROBE ${JSON.stringify(probe)}`);
}
await page.screenshot({ path: "D:/moodle/_cmdr_rescue_v3_1022/trial/results/20261022_v3_human_chrome/clock-next-hit-122.png", fullPage: false });
await browser.close();
