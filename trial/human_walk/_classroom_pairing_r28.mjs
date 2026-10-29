import { chromium } from "file:///D:/moodle/_cmdr_rescue_v3_1022/frontend/node_modules/playwright/index.mjs";
import fs from "node:fs";
const BASE = process.env.SIM_BASE || "http://127.0.0.1:14493";
const TICKET = process.env.PAIR_TICKET || "";
const OUT = "D:/moodle/_cmdr_rescue_v3_1022/trial/results/20261022_v3_human_chrome";
const NL = String.fromCharCode(10);
const lines = [];
const note = (v) => { lines.push(v); fs.writeFileSync(OUT + "/classroom-pairing-28.txt", lines.join(NL) + NL, "utf8"); };

const browser = await chromium.launch({ headless: true });
const ctx = await browser.newContext({ viewport: { width: 430, height: 932 }, deviceScaleFactor: 1 });
await ctx.addInitScript(() => {
  if (!sessionStorage.getItem("__probe_booted")) { localStorage.clear(); sessionStorage.clear(); sessionStorage.setItem("__probe_booted", "1"); }
});
const page = await ctx.newPage();
const errors = [];
const pairing = [];
page.on("pageerror", (e) => errors.push(String(e).slice(0, 160)));
page.on("response", (r) => {
  const url = r.url();
  if (url.includes("/demo/pairing/")) pairing.push(`${r.request().method()} ${r.status()}`);
});
note(`BASE ${BASE} TICKET_LEN ${TICKET.length}`);
const target = TICKET ? `${BASE}/revolution#pair=${encodeURIComponent(TICKET)}` : `${BASE}/revolution`;
await page.goto(target, { waitUntil: "networkidle", timeout: 60000 });
await page.waitForTimeout(4200);
const clock = page.locator('[data-testid="rev-classroom-clock"]');
note(`CLOCK_VISIBLE ${await clock.isVisible().catch(() => false)}`);
note(`HASH_AFTER ${JSON.stringify(await page.evaluate(() => window.location.hash))}`);
const bearer = await page.evaluate(() => {
  for (let i = 0; i < localStorage.length; i += 1) {
    const key = localStorage.key(i) || "";
    const value = localStorage.getItem(key) || "";
    if (/token|bearer/i.test(key) && value.length > 80) return { key, len: value.length };
  }
  return null;
});
note(`BEARER_STORED ${JSON.stringify(bearer ? { key: bearer.key, len: bearer.len } : null)}`);
if (!(await clock.isVisible().catch(() => false))) {
  await page.locator('[data-testid="rev-mobile-tab-trips"]').click().catch(() => {});
  await page.waitForTimeout(900);
  await page.locator('[data-testid="rev-demo-session"]').click().catch(() => {});
  await page.waitForTimeout(3600);
  note(`CLOCK_AFTER_MANUAL ${await clock.isVisible().catch(() => false)}`);
  const err = page.locator('[data-testid="rev-demo-error"]');
  note(`DEMO_ERROR ${JSON.stringify(await err.count() ? (await err.innerText()).replace(/\\s+/g, " ").trim() : "")}`);
}
note(`CLOCK_TEXT ${JSON.stringify((await clock.innerText().catch(() => "")).replace(/\\s+/g, " ").slice(0, 180))}`);
note(`PAIRING_HTTP ${JSON.stringify(pairing)}`);
note(`ERRORS ${JSON.stringify(errors.slice(0, 3))}`);
await page.screenshot({ path: OUT + "/classroom-pairing-28-phone.png", fullPage: false });
await ctx.close();
await browser.close();
