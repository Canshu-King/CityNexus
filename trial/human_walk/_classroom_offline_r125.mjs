import { chromium } from "file:///D:/moodle/_cmdr_rescue_v3_1022/frontend/node_modules/playwright/index.mjs";
import fs from "node:fs";

const BASE = "http://localhost:14492";
const OUT = "D:/moodle/_cmdr_rescue_v3_1022/trial/results/20261022_v3_human_chrome/classroom-offline-125.txt";
const SHOT = "D:/moodle/_cmdr_rescue_v3_1022/trial/results/20261022_v3_human_chrome/classroom-offline-125.png";
const NL = String.fromCharCode(10);
const lines = [];
const note = (value) => { lines.push(value); fs.writeFileSync(OUT, lines.join(NL) + NL, "utf8"); };
const raw = JSON.parse(fs.readFileSync("D:/moodle/_cmdr_v3_live_1022/.demo_pairing_ticket", "utf8"));
const tickets = (raw.tickets && raw.tickets.length ? raw.tickets : [raw.ticket]).filter(Boolean);
const started = Date.now();
const elapsed = () => ((Date.now() - started) / 1000).toFixed(1);

const browser = await chromium.launch({ headless: true });
const ctx = await browser.newContext({ viewport: { width: 390, height: 844 }, deviceScaleFactor: 1 });
let blocked = 0;
await ctx.route("**/*", (route) => {
  const host = new URL(route.request().url()).hostname;
  if (host === "localhost" || host === "127.0.0.1" || host === "10.12.35.143") return route.continue();
  blocked += 1;
  return route.abort("internetdisconnected");
});
const page = await ctx.newPage();
const errors = [];
page.on("pageerror", (error) => errors.push(String(error).slice(0, 120)));

async function press(name, timeout = 15000) {
  const target = page.getByRole("button", { name }).first();
  try { await target.waitFor({ state: "visible", timeout }); } catch { note(`MISS_BUTTON ${name}`); return false; }
  await target.scrollIntoViewIfNeeded().catch(() => {});
  await page.waitForTimeout(250);
  await target.click({ timeout: 8000 }).catch(() => {});
  return true;
}

async function status() {
  return page.evaluate(async () => {
    const token = sessionStorage.getItem("citynexus.traveler.bearer");
    const jid = localStorage.getItem("citynexus.v8.journey_id");
    if (!token || !jid) return "no_identity";
    const headers = { Accept: "application/json", Authorization: `Bearer ${token}` };
    const current = await fetch(`/api/v1/journeys/${jid}/simulation/runs/current`, { headers, cache: "no-store" })
      .then((response) => response.json()).catch(() => null);
    const run = current && (current.run || current);
    return run && run.run_id ? `${run.status}#${run.sequence}` : "no_run";
  });
}

await page.goto(`${BASE}/revolution#pair=${encodeURIComponent(tickets[0])}`, { waitUntil: "domcontentloaded", timeout: 60000 });
await page.waitForTimeout(6000);
note(`PAIR status=${await status()} blocked_external=${blocked} elapsed_s=${elapsed()}`);
const identity = await page.evaluate(() => Boolean(sessionStorage.getItem("citynexus.traveler.bearer")));
note(`IDENTITY ${identity}`);
if (await press("去课堂控制台", 8000)) await page.waitForTimeout(1000);
if (await press("开演（模拟两日）")) { await page.waitForTimeout(2500); note(`START status=${await status()}`); }
if (await press("+30 分钟")) { await page.waitForTimeout(1500); note(`ADVANCE_30 status=${await status()}`); }
if (await press("+1 小时")) { await page.waitForTimeout(1500); note(`ADVANCE_60 status=${await status()}`); }
if (await press("到下一站")) { await page.waitForTimeout(3000); note(`NEXT status=${await status()}`); }
note(`BLOCKED_EXTERNAL_TOTAL ${blocked}`);
note(`ERRORS ${JSON.stringify(errors.slice(0, 4))}`);
await page.screenshot({ path: SHOT, fullPage: false });
await browser.close();
