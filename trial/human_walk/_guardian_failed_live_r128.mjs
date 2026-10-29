import { chromium } from "file:///D:/moodle/_cmdr_rescue_v3_1022/frontend/node_modules/playwright/index.mjs";
import fs from "node:fs";

const BASE = "http://127.0.0.1:14492";
const DIR = "D:/moodle/_cmdr_rescue_v3_1022/trial/results/20261022_v3_human_chrome";
const OUT = DIR + "/guardian-failed-live-128.txt";
const SHOT = DIR + "/classroom-guardian-failed-128.png";
const NL = String.fromCharCode(10);
const lines = [];
const note = (value) => { lines.push(value); fs.writeFileSync(OUT, lines.join(NL) + NL, "utf8"); };
const raw = JSON.parse(fs.readFileSync("D:/moodle/_cmdr_v3_live_1022/.demo_pairing_ticket", "utf8"));
const tickets = (raw.tickets && raw.tickets.length ? raw.tickets : [raw.ticket]).filter(Boolean);
const started = Date.now();
const elapsed = () => ((Date.now() - started) / 1000).toFixed(1);
note(`RUN_AT ${new Date().toISOString()}`);

const browser = await chromium.launch({ headless: true });
const ctx = await browser.newContext({ viewport: { width: 390, height: 844 }, deviceScaleFactor: 1 });
const page = await ctx.newPage();
const errors = [];
page.on("pageerror", (error) => errors.push(String(error).slice(0, 140)));

async function press(name, timeout = 15000) {
  const target = page.getByRole("button", { name }).first();
  try { await target.waitFor({ state: "visible", timeout }); } catch { note(`MISS_BUTTON ${name}`); return false; }
  await target.scrollIntoViewIfNeeded().catch(() => {});
  await page.waitForTimeout(250);
  const hit = await target.evaluate((node) => {
    const box = node.getBoundingClientRect();
    const top = document.elementFromPoint(box.left + box.width / 2, box.top + box.height / 2);
    return Boolean(top) && (node === top || node.contains(top)) && !node.disabled;
  });
  if (!hit) { note(`BLOCKED_BUTTON ${name}`); return false; }
  await target.click({ timeout: 8000 }).catch(() => {});
  return true;
}

async function progress() {
  return page.evaluate(async () => {
    const token = sessionStorage.getItem("citynexus.traveler.bearer");
    const jid = localStorage.getItem("citynexus.v8.journey_id");
    if (!token || !jid) return { error: "no_identity" };
    const headers = { Accept: "application/json", Authorization: `Bearer ${token}` };
    const current = await fetch(`/api/v1/journeys/${jid}/simulation/runs/current`, { headers, cache: "no-store" })
      .then((response) => response.json()).catch(() => null);
    const run = current && (current.run || current);
    if (!run || !run.run_id) return { error: "no_run" };
    const body = await fetch(`/api/v1/journeys/${jid}/simulation/runs/${run.run_id}/progress`, { headers, cache: "no-store" })
      .then((response) => response.json()).catch(() => null);
    return {
      status: run.status, sequence: run.sequence,
      outcome: (body && body.guardian_outcome) || null,
      proposals: ((body && body.proposals) || []).map((item) => ({ id: item.id, status: item.status })),
      pending: (body && body.readiness && body.readiness.pending_event_id) || null,
    };
  });
}

await page.goto(`${BASE}/revolution#pair=${encodeURIComponent(tickets[0])}`, { waitUntil: "networkidle", timeout: 60000 });
await page.waitForTimeout(5200);
if (await press("去课堂控制台")) await page.waitForTimeout(1000);
if (await press("开演（模拟两日）")) { await page.waitForTimeout(2500); note(`START ${JSON.stringify(await progress())}`); }
if (await press("闭馆")) { await page.waitForTimeout(3000); note(`CLOSURE ${JSON.stringify(await progress())}`); }
if (await press("交给守护助手")) {
  note("GUARDIAN_REQUESTED");
  const deadline = Date.now() + 420 * 1000;
  let last = null;
  while (Date.now() < deadline) {
    await page.waitForTimeout(6000);
    last = await progress();
    if (last.status && last.status !== "GUARDIAN_RUNNING") break;
  }
  note(`GUARDIAN_RESULT elapsed_s=${elapsed()} ${JSON.stringify(last)}`);
  if (last && last.status === "PAUSED_MODEL_UNAVAILABLE") {
    const retry = page.locator('[data-testid="rev-presenter-guardian-retry"]').first();
    const count = await retry.count();
    const detail = count ? await retry.evaluate((node) => {
      const box = node.getBoundingClientRect();
      const top = document.elementFromPoint(box.left + box.width / 2, box.top + box.height / 2);
      return {
        text: (node.textContent || "").trim(),
        visible: box.width > 0 && box.height > 0,
        hitSelf: Boolean(top) && (node === top || node.contains(top)),
        disabled: node.disabled === true,
      };
    }) : null;
    const noteText = await page.locator('[data-testid="rev-presenter-model-note"]').first().textContent().catch(() => null);
    note(`RETRY_UI ${count} ${JSON.stringify(detail)}`);
    note(`MODEL_NOTE ${JSON.stringify((noteText || "").trim())}`);
    await page.screenshot({ path: SHOT, fullPage: false });
    if (count && detail && detail.hitSelf && !detail.disabled) {
      await retry.click().catch(() => {});
      await page.waitForTimeout(8000);
      note(`AFTER_RETRY ${JSON.stringify(await progress())}`);
    }
  } else {
    await page.screenshot({ path: SHOT, fullPage: false });
  }
}
note(`FINAL ${JSON.stringify(await progress())}`);
note(`ERRORS ${JSON.stringify(errors.slice(0, 3))}`);
await browser.close();
