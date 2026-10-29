import { chromium } from "file:///D:/moodle/_cmdr_rescue_v3_1022/frontend/node_modules/playwright/index.mjs";
import fs from "node:fs";

const BASE = "http://127.0.0.1:14492";
const OUT = "D:/moodle/_cmdr_rescue_v3_1022/trial/results/20261022_v3_human_chrome/guardian-panel-accept-100.txt";
const SHOT = "D:/moodle/_cmdr_rescue_v3_1022/trial/results/20261022_v3_human_chrome/classroom-guardian-panel-accept-100.png";
const TICKET_FILE = "D:/moodle/_cmdr_v3_live_1022/.demo_pairing_ticket";
const NL = String.fromCharCode(10);
const lines = [];
const note = (value) => { lines.push(value); fs.writeFileSync(OUT, lines.join(NL) + NL, "utf8"); };
const raw = JSON.parse(fs.readFileSync(TICKET_FILE, "utf8"));
const tickets = (raw.tickets && raw.tickets.length ? raw.tickets : [raw.ticket]).filter(Boolean);

const browser = await chromium.launch({ headless: true });
const ctx = await browser.newContext({ viewport: { width: 390, height: 844 }, deviceScaleFactor: 1 });
const page = await ctx.newPage();
const errors = [];
const responses = [];
page.on("pageerror", (error) => errors.push(String(error).slice(0, 160)));
page.on("response", (response) => {
  const url = response.url();
  if (/replan|accept|simulation\/runs\/.*\/(resume|guardian)/.test(url)) {
    responses.push(`${response.status()} ${url.replace(/^https?:\/\/[^/]+/, "").slice(0, 110)}`);
  }
});
const shot = async (name) => { await page.screenshot({ path: name, fullPage: false }); };

async function screen() {
  return page.evaluate(() => {
    const pick = (id) => {
      const node = document.querySelector(`[data-testid="${id}"]`);
      return node ? node.textContent : null;
    };
    return {
      run: pick("rev-presenter-run"),
      message: pick("rev-presenter-message"),
      proposal: pick("rev-guardian-proposal-diff"),
      origin: pick("rev-guardian-proposal-origin"),
      note: pick("rev-guardian-proposal-note"),
    };
  });
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
    if (!run || !run.run_id) return { jid, current };
    const body = await fetch(`/api/v1/journeys/${jid}/simulation/runs/${run.run_id}/progress`, { headers, cache: "no-store" })
      .then((response) => response.json()).catch(() => null);
    const pendingId = body && body.readiness && body.readiness.pending_event_id;
    return {
      status: run.status, sequence: run.sequence, plan: run.state && run.state.plan_version_id,
      pending: ((body && body.events) || []).find((item) => item.id === pendingId) || null,
      proposals: ((body && body.proposals) || []).map((item) => ({ id: item.id, status: item.status })),
    };
  });
}

await page.goto(`${BASE}/revolution#pair=${encodeURIComponent(tickets[0])}`, { waitUntil: "networkidle", timeout: 60000 });
await page.waitForTimeout(5200);
const jump = page.locator('[data-testid="rev-jump-clock"]').first();
if (await jump.count()) { await jump.click().catch(() => {}); await page.waitForTimeout(1500); }
const start = page.getByRole("button", { name: /开演/ }).first();
if (await start.count()) { await start.scrollIntoViewIfNeeded().catch(() => {}); await start.click().catch(() => {}); }
await page.waitForTimeout(5000);
const closure = page.getByRole("button", { name: "闭馆", exact: true }).first();
if (await closure.count()) { await closure.scrollIntoViewIfNeeded().catch(() => {}); await closure.click().catch(() => {}); await page.waitForTimeout(4200); }
const guardian = page.getByRole("button", { name: "交给守护助手" }).first();
note(`GUARDIAN_BUTTON ${await guardian.count()}`);
if (await guardian.count()) {
  await guardian.scrollIntoViewIfNeeded().catch(() => {});
  await guardian.click().catch(() => {});
  for (let tick = 0; tick < 56; tick += 1) {
    await page.waitForTimeout(6000);
    const p = await progress();
    if (tick % 5 === 0 || (p.status && p.status !== "GUARDIAN_RUNNING")) {
      note(`POLL ${tick} status=${p.status} seq=${p.sequence} proposals=${JSON.stringify(p.proposals || [])}`);
    }
    if (p.status === "PAUSED_FOR_ACCEPTANCE" || p.status === "PAUSED_MODEL_UNAVAILABLE" || p.status === "SIMULATED_COMPLETED") break;
  }
}
note(`BEFORE ${JSON.stringify(await progress())}`);

const guardianTab = page.getByRole("button", { name: "行程守护", exact: true }).first();
if (await guardianTab.count()) {
  await guardianTab.scrollIntoViewIfNeeded().catch(() => {});
  await guardianTab.click().catch(() => {});
  await page.waitForTimeout(6500);
}
note(`PANEL ${JSON.stringify(await screen())}`);
await shot(SHOT.replace(".png", "-panel.png"));

const accept = page.locator('[data-testid="rev-guardian-accept-replan"]').first();
note(`PANEL_ACCEPT ${await accept.count()} disabled=${await accept.isDisabled().catch(() => null)}`);
if (await accept.count()) {
  await accept.scrollIntoViewIfNeeded().catch(() => {});
  await accept.click().catch(() => {});
  for (let tick = 0; tick < 12; tick += 1) {
    await page.waitForTimeout(4000);
    const p = await progress();
    note(`AFTER_ACCEPT_POLL ${tick} status=${p.status} pending=${p.pending ? p.pending.status : "-"} plan=${p.plan}`);
    if (p.pending && (p.pending.status === "RESOLVED" || p.pending.status === "IGNORED")) break;
  }
}
note(`AFTER_ACCEPT ${JSON.stringify(await progress())}`);
const resume = page.getByRole("button", { name: /继续模拟/ }).first();
note(`RESUME_BUTTON ${await resume.count()}`);
if (await resume.count()) {
  await resume.scrollIntoViewIfNeeded().catch(() => {});
  await resume.click().catch(() => {});
  await page.waitForTimeout(7000);
}
note(`AFTER_RESUME ${JSON.stringify(await progress())}`);
note(`RESPONSES ${JSON.stringify(responses.slice(-12))}`);
note(`ERRORS ${JSON.stringify(errors.slice(0, 3))}`);
await shot(SHOT);
await browser.close();
