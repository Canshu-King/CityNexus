import { chromium } from "file:///D:/moodle/_cmdr_rescue_v3_1022/frontend/node_modules/playwright/index.mjs";
import fs from "node:fs";

const BASE = "http://127.0.0.1:14492";
const DIR = "D:/moodle/_cmdr_rescue_v3_1022/trial/results/20261022_v3_human_chrome";
const OUT = DIR + "/guardian-wait-110.txt";
const SHOT = DIR + "/classroom-guardian-wait-110.png";
const NL = String.fromCharCode(10);
const lines = [];
const note = (value) => { lines.push(value); fs.writeFileSync(OUT, lines.join(NL) + NL, "utf8"); };
const raw = JSON.parse(fs.readFileSync("D:/moodle/_cmdr_v3_live_1022/.demo_pairing_ticket", "utf8"));
const tickets = (raw.tickets && raw.tickets.length ? raw.tickets : [raw.ticket]).filter(Boolean);
const started = Date.now();
const elapsed = () => ((Date.now() - started) / 1000).toFixed(1);

const browser = await chromium.launch({ headless: true });
const ctx = await browser.newContext({ viewport: { width: 390, height: 844 }, deviceScaleFactor: 1 });
const page = await ctx.newPage();
const errors = [];
page.on("pageerror", (error) => errors.push(String(error).slice(0, 160)));

async function press(name, timeout = 15000) {
  const target = page.getByRole("button", { name }).first();
  try { await target.waitFor({ state: "visible", timeout }); } catch { note(`MISS_BUTTON ${name}`); return false; }
  await target.scrollIntoViewIfNeeded().catch(() => {});
  await page.waitForTimeout(200);
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
    return run && run.status ? run.status : "no_run";
  });
}

await page.goto(`${BASE}/revolution#pair=${encodeURIComponent(tickets[0])}`, { waitUntil: "networkidle", timeout: 60000 });
await page.waitForTimeout(5200);
if (await press("去课堂控制台")) await page.waitForTimeout(1000);
if (await press("开演（模拟两日）")) { await page.waitForTimeout(2500); note(`START status=${await status()} elapsed_s=${elapsed()}`); }
if (await press("闭馆")) { await page.waitForTimeout(3000); note(`CLOSURE status=${await status()} elapsed_s=${elapsed()}`); }
if (await press("交给守护助手")) {
  await page.waitForTimeout(12000);
  const state = await status();
  const wait = page.locator('[data-testid="rev-presenter-guardian-wait"]').first();
  const count = await wait.count();
  const detail = count ? await wait.evaluate((node) => {
    const box = node.getBoundingClientRect();
    return {
      text: (node.textContent || "").trim(),
      visible: box.width > 0 && box.height > 0,
      inViewport: box.top >= 0 && box.bottom <= window.innerHeight,
    };
  }) : null;
  note(`WAIT_NOTE ${count} ${JSON.stringify(detail)}`);
  note(`OLD_SENTENCE_COUNT ${await page.getByText("没接模型会一直停在等待").count()}`);
  note(`AFTER_12S status=${state} elapsed_s=${elapsed()}`);
  await page.screenshot({ path: SHOT, fullPage: false });
}
note(`ERRORS ${JSON.stringify(errors.slice(0, 3))}`);
await browser.close();
