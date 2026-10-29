import { chromium } from "file:///D:/moodle/_cmdr_rescue_v3_1022/frontend/node_modules/playwright/index.mjs";
import fs from "node:fs";

const BASE = "http://127.0.0.1:14492";
const OUT = process.env.PAIR_OUT || "D:/moodle/_cmdr_rescue_v3_1022/trial/results/20261022_v3_human_chrome/guardian-plan-applied-92.txt";
const SHOT = process.env.PAIR_SHOT || "D:/moodle/_cmdr_rescue_v3_1022/trial/results/20261022_v3_human_chrome/classroom-plan-applied-92.png";
const TICKET_FILE = "D:/moodle/_cmdr_v3_live_1022/.demo_pairing_ticket";
const NL = String.fromCharCode(10);
const lines = [];
const note = (value) => { lines.push(value); fs.writeFileSync(OUT, lines.join(NL) + NL, "utf8"); };
const raw = JSON.parse(fs.readFileSync(TICKET_FILE, "utf8"));
const tickets = (raw.tickets && raw.tickets.length ? raw.tickets : [raw.ticket]).filter(Boolean);
const ticket = process.env.PAIR_TICKET || tickets[0];

const browser = await chromium.launch({ headless: true });
const W = Number(process.env.PAIR_W || 390);
const H = Number(process.env.PAIR_H || 844);
const ctx = await browser.newContext({ viewport: { width: W, height: H }, deviceScaleFactor: 1 });
const page = await ctx.newPage();
const errors = [];
page.on("pageerror", (error) => errors.push(String(error).slice(0, 160)));
const shot = async (name) => { await page.screenshot({ path: name, fullPage: false }); };

async function screen() {
  return page.evaluate(() => {
    const pick = (id) => {
      const node = document.querySelector(`[data-testid="${id}"]`);
      return node ? node.textContent : null;
    };
    return {
      virtual: pick("rev-clock-virtual"),
      run: pick("rev-presenter-run"),
      message: pick("rev-presenter-message"),
      history: pick("rev-presenter-history"),
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
      jid,
      status: run.status,
      sequence: run.sequence,
      plan_id: body && body.current_active_plan_version_id,
      activity_id: body && body.current_activity_id,
      pending: ((body && body.events) || []).find((item) => item.id === pendingId) || null,
      proposals: ((body && body.proposals) || []).map((item) => ({ id: item.id, status: item.status })),
    };
  });
}

async function planTitles(planId) {
  if (!planId) return null;
  return page.evaluate(async (id) => {
    const token = sessionStorage.getItem("citynexus.traveler.bearer");
    const headers = { Accept: "application/json", Authorization: `Bearer ${token}` };
    const plan = await fetch(`/api/v1/plans/${id}`, { headers, cache: "no-store" })
      .then((response) => (response.ok ? response.json() : null)).catch(() => null);
    return ((plan && plan.activities) || []).map((item) => ({ id: item.id, title: item.title, start: item.start_at, status: item.status }));
  }, planId);
}

const started = Date.now();
await page.goto(`${BASE}/revolution#pair=${encodeURIComponent(ticket)}`, { waitUntil: "networkidle", timeout: 60000 });
await page.waitForTimeout(5200);
const jump = page.locator('[data-testid="rev-jump-clock"]').first();
if (await jump.count()) { await jump.click().catch(() => {}); await page.waitForTimeout(1600); }
const start = page.getByRole("button", { name: /开演/ }).first();
if (await start.count()) { await start.scrollIntoViewIfNeeded().catch(() => {}); await start.click().catch(() => {}); }
await page.waitForTimeout(5200);
note(`START ${JSON.stringify(await progress())}`);

const closure = page.getByRole("button", { name: "闭馆", exact: true }).first();
if (await closure.count()) {
  await closure.scrollIntoViewIfNeeded().catch(() => {});
  await closure.click().catch(() => {});
  await page.waitForTimeout(4200);
}
note(`SCENE ${JSON.stringify(await progress())}`);

const guardian = page.getByRole("button", { name: "交给守护助手" }).first();
note(`GUARDIAN_BUTTON ${await guardian.count()}`);
if (await guardian.count()) {
  await guardian.scrollIntoViewIfNeeded().catch(() => {});
  await guardian.click().catch(() => {});
  const began = Date.now();
  for (let tick = 0; tick < 56; tick += 1) {
    await page.waitForTimeout(6000);
    const p = await progress();
    if (tick % 5 === 0 || (p.status && p.status !== "GUARDIAN_RUNNING")) {
      note(`POLL ${tick} elapsed_s=${Math.round((Date.now() - began) / 1000)} status=${p.status} seq=${p.sequence} proposals=${JSON.stringify(p.proposals || [])}`);
    }
    if (p.status === "PAUSED_FOR_ACCEPTANCE" || p.status === "PAUSED_MODEL_UNAVAILABLE" || p.status === "SIMULATED_COMPLETED") break;
  }
}
note(`BEFORE_ACCEPT ${JSON.stringify(await progress())}`);
const accept = page.getByRole("button", { name: "接受这次事件的调整" }).first();
note(`EVENT_ACCEPT_BUTTON ${await accept.count()}`);
if (await accept.count()) {
  await accept.scrollIntoViewIfNeeded().catch(() => {});
  await accept.click().catch(() => {});
  for (let tick = 0; tick < 18; tick += 1) {
    await page.waitForTimeout(5000);
    const p = await progress();
    note(`ACCEPT_POLL ${tick} status=${p.status} pending=${p.pending ? p.pending.status : "-"} plan=${p.plan_id}`);
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
const before = await progress();
note(`PLAN_BEFORE_NEXT ${JSON.stringify(await planTitles(before.plan_id))}`);
note(`SCREEN_BEFORE_NEXT ${JSON.stringify(await screen())}`);
await shot(SHOT.replace(".png", "-before.png"));

const next = page.locator('[data-testid="rev-clock-next"]').first();
note(`NEXT_BUTTON ${await next.count()} disabled=${await next.isDisabled().catch(() => null)}`);
if (await next.count()) {
  await next.scrollIntoViewIfNeeded().catch(() => {});
  await next.click().catch(() => {});
  await page.waitForTimeout(8000);
}
const after = await progress();
note(`AFTER_NEXT ${JSON.stringify(after)}`);
note(`SCREEN_AFTER_NEXT ${JSON.stringify(await screen())}`);
note(`PLAN_AFTER_NEXT ${JSON.stringify(await planTitles(after.plan_id))}`);
await shot(SHOT);
note(`ELAPSED_S ${Math.round((Date.now() - started) / 1000)}`);
note(`ERRORS ${JSON.stringify(errors.slice(0, 3))}`);
await browser.close();
