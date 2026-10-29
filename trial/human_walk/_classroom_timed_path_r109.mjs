import { chromium } from "file:///D:/moodle/_cmdr_rescue_v3_1022/frontend/node_modules/playwright/index.mjs";
import fs from "node:fs";

const BASE = "http://127.0.0.1:14492";
const DIR = "D:/moodle/_cmdr_rescue_v3_1022/trial/results/20261022_v3_human_chrome";
const SUFFIX = process.env.RS || "109";
const WIDTH = Number(process.env.RW || 390);
const HEIGHT = Number(process.env.RH || 844);
const OUT = DIR + "/classroom-timed-path-" + SUFFIX + ".txt";
const SHOT = DIR + "/classroom-timed-path-" + SUFFIX + ".png";
const NL = String.fromCharCode(10);
const lines = [];
const note = (value) => { lines.push(value); fs.writeFileSync(OUT, lines.join(NL) + NL, "utf8"); };
const raw = JSON.parse(fs.readFileSync("D:/moodle/_cmdr_v3_live_1022/.demo_pairing_ticket", "utf8"));
const tickets = (raw.tickets && raw.tickets.length ? raw.tickets : [raw.ticket]).filter(Boolean);
const ticket = tickets[0];
const started = Date.now();
const elapsed = () => ((Date.now() - started) / 1000).toFixed(1);
const mark = (name, extra = "") => note(`STEP ${name} elapsed_s=${elapsed()} ${extra}`);

const browser = await chromium.launch({ headless: true });
const ctx = await browser.newContext({ viewport: { width: WIDTH, height: HEIGHT }, deviceScaleFactor: 1 });
const page = await ctx.newPage();
const errors = [];
page.on("pageerror", (error) => errors.push(String(error).slice(0, 160)));

async function progress() {
  return page.evaluate(async () => {
    const token = sessionStorage.getItem("citynexus.traveler.bearer");
    const jid = localStorage.getItem("citynexus.v8.journey_id");
    if (!token || !jid) return { error: "no_identity" };
    const headers = { Accept: "application/json", Authorization: `Bearer ${token}` };
    const current = await fetch(`/api/v1/journeys/${jid}/simulation/runs/current`, { headers, cache: "no-store" })
      .then((response) => response.json()).catch(() => null);
    const run = current && (current.run || current);
    if (!run || !run.run_id) return { error: "no_run", current };
    const body = await fetch(`/api/v1/journeys/${jid}/simulation/runs/${run.run_id}/progress`, { headers, cache: "no-store" })
      .then((response) => response.json()).catch(() => null);
    const pendingId = body && body.readiness && body.readiness.pending_event_id;
    const pending = ((body && body.events) || []).find((item) => item.id === pendingId);
    return {
      status: run.status, sequence: run.sequence,
      pending: pending ? { id: pending.id, status: pending.status } : null,
      proposals: ((body && body.proposals) || []).map((item) => ({ id: item.id, status: item.status })),
      outcome: (body && body.guardian_outcome) || null,
      readiness: (body && body.readiness) || null,
    };
  });
}

async function button(name, timeout) {
  const loc = page.getByRole("button", { name }).first();
  try {
    await loc.waitFor({ state: "visible", timeout });
    return loc;
  } catch {
    return null;
  }
}

async function press(name, timeout = 15000) {
  const target = await button(name, timeout);
  if (!target) { note(`MISS_BUTTON ${name}`); return false; }
  for (let attempt = 0; attempt < 3; attempt += 1) {
    await target.scrollIntoViewIfNeeded().catch(() => {});
    await page.waitForTimeout(attempt === 0 ? 200 : 700);
    const hit = await target.evaluate((node) => {
      const box = node.getBoundingClientRect();
      const top = document.elementFromPoint(box.left + box.width / 2, box.top + box.height / 2);
      return Boolean(top) && (node === top || node.contains(top)) && !node.disabled;
    });
    if (hit) {
      await target.click({ timeout: 8000 }).catch(() => {});
      return true;
    }
  }
  note(`BLOCKED_BUTTON ${name}`);
  return false;
}

async function waitStatus(wanted, seconds) {
  const deadline = Date.now() + seconds * 1000;
  while (Date.now() < deadline) {
    const p = await progress();
    if (p.status && wanted.includes(p.status)) return p;
    await page.waitForTimeout(3000);
  }
  return await progress();
}

await page.goto(`${BASE}/revolution#pair=${encodeURIComponent(ticket)}`, { waitUntil: "networkidle", timeout: 60000 });
await page.waitForTimeout(5200);
mark("PAIR", JSON.stringify(await progress()));
if (await press("去课堂控制台")) await page.waitForTimeout(1200);

if (await press("开演（模拟两日）")) {
  const p = await waitStatus(["RUNNING"], 30);
  mark("START", JSON.stringify({ status: p.status, seq: p.sequence }));
}
if (await press("+30 分钟")) {
  await page.waitForTimeout(1500);
  mark("ADVANCE_30", JSON.stringify(await progress()));
}
if (await press("闭馆")) {
  await page.waitForTimeout(3500);
  mark("CLOSURE", JSON.stringify(await progress()));
}
if (await press("交给守护助手")) {
  note("GUARDIAN_REQUESTED");
  const p = await waitStatus(["PAUSED_FOR_ACCEPTANCE", "PAUSED_MODEL_UNAVAILABLE", "PAUSED_REQUIRES_MISSION"], 360);
  mark("GUARDIAN_RESULT", JSON.stringify(p));
  if (p.status === "GUARDIAN_RUNNING") {
    // A failed attempt can be recorded before the run state is written; the strip stays
    // disabled, so nothing after this point is a fair click.
    note("GUARDIAN_STOPPED_AT_TIMEOUT");
    note(`FINAL ${JSON.stringify(p)}`);
    note(`ERRORS ${JSON.stringify(errors.slice(0, 3))}`);
    await page.screenshot({ path: SHOT, fullPage: false });
    await browser.close();
    process.exit(0);
  }
  if (p.status === "PAUSED_MODEL_UNAVAILABLE") {
    if (await press("再请一次守护", 5000)) {
      note("GUARDIAN_RETRY");
      const again = await waitStatus(["PAUSED_FOR_ACCEPTANCE", "PAUSED_MODEL_UNAVAILABLE"], 360);
      mark("GUARDIAN_RETRY_RESULT", JSON.stringify(again));
    }
  }
}
let state = await progress();
if (state.status === "PAUSED_FOR_ACCEPTANCE") {
  if (await press("接受这次事件的调整")) {
    const deadline = Date.now() + 90000;
    while (Date.now() < deadline) {
      await page.waitForTimeout(3000);
      const p = await progress();
      if (p.status !== "PAUSED_FOR_ACCEPTANCE" || (p.pending && p.pending.status !== "DETECTED")) break;
    }
    mark("ACCEPTED", JSON.stringify(await progress()));
  }
}
if (await press("继续模拟", 8000)) {
  const p = await waitStatus(["RUNNING"], 40);
  await page.waitForTimeout(1200);
  mark("RESUMED", JSON.stringify({ status: p.status, seq: p.sequence }));
}
for (let hop = 1; hop <= 10; hop += 1) {
  if (!(await press("到下一站", 8000))) { note(`HOP_${hop}_NO_BUTTON`); break; }
  await page.waitForTimeout(2500);
  const p = await progress();
  mark(`HOP_${hop}`, JSON.stringify({ status: p.status, seq: p.sequence }));
  if (p.status === "SIMULATED_COMPLETED" || p.status === "COMPLETED") break;
}

note(`FINAL ${JSON.stringify(await progress())}`);
note(`ERRORS ${JSON.stringify(errors.slice(0, 3))}`);
await page.screenshot({ path: SHOT, fullPage: false });
await browser.close();
