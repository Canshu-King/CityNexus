import { chromium } from "file:///D:/moodle/_cmdr_rescue_v3_1022/frontend/node_modules/playwright/index.mjs";
import fs from "node:fs";

const BASE = process.env.PAIR_BASE || "http://127.0.0.1:14492";
const OUT = process.env.PAIR_OUT || "D:/moodle/_cmdr_rescue_v3_1022/trial/results/20261022_v3_human_chrome/guardian-live-78.txt";
const TICKET_FILE = "D:/moodle/_cmdr_v3_live_1022/.demo_pairing_ticket";
const SHOT_DIR = "D:/moodle/_cmdr_rescue_v3_1022/trial/results/20261022_v3_human_chrome";
const NL = String.fromCharCode(10);
const lines = [];
const note = (value) => { lines.push(value); fs.writeFileSync(OUT, lines.join(NL) + NL, "utf8"); };
const raw = JSON.parse(fs.readFileSync(TICKET_FILE, "utf8"));
const tickets = (raw.tickets && raw.tickets.length ? raw.tickets : [raw.ticket]).filter(Boolean);
const ticket = process.env.PAIR_TICKET || tickets[0];

const browser = await chromium.launch({ headless: true });
const ctx = await browser.newContext({ viewport: { width: 390, height: 844 }, deviceScaleFactor: 1 });
const page = await ctx.newPage();
const errors = [];
page.on("pageerror", (error) => errors.push(String(error).slice(0, 160)));
const shot = async (name) => {
  await page.screenshot({ path: `${SHOT_DIR}/${name}`, fullPage: false });
};

async function readRunText() {
  return page.evaluate(() => {
    const node = document.querySelector('[data-testid="rev-presenter-run"]');
    const acceptance = document.querySelector('[data-testid="rev-presenter-acceptance-note"]');
    const message = document.querySelector('[data-testid="rev-presenter-message"]');
    return {
      run: node ? node.textContent : null,
      acceptanceNote: Boolean(acceptance),
      message: message ? message.textContent : null,
    };
  });
}

async function readProgress() {
  return page.evaluate(async () => {
    const token = sessionStorage.getItem("citynexus.traveler.bearer");
    const jid = localStorage.getItem("citynexus.v8.journey_id");
    if (!token || !jid) return { error: "no_identity", hasToken: Boolean(token), jid };
    const headers = { Accept: "application/json", Authorization: `Bearer ${token}` };
    const current = await fetch(`/api/v1/journeys/${jid}/simulation/runs/current`, { headers, cache: "no-store" })
      .then((response) => response.json()).catch(() => null);
    const run = current && current.available ? current.run : null;
    if (!run) return { jid, run: null, current };
    const progress = await fetch(`/api/v1/journeys/${jid}/simulation/runs/${run.run_id}/progress`, { headers, cache: "no-store" })
      .then((response) => response.json()).catch(() => null);
    return {
      jid,
      run: { id: run.run_id, status: run.status, sequence: run.sequence },
      proposals: ((progress && progress.proposals) || []).map((item) => ({
        id: item.id, status: item.status, event: item.trigger_event_id || item.event_id,
      })),
      guardian_runs: ((progress && progress.guardian_runs) || []).map((item) => ({
        id: item.run_id, status: item.status, proposal_id: item.proposal_id, error: item.error_code,
      })),
      readiness: (progress && progress.readiness) || null,
      outcome: (progress && progress.guardian_outcome) || null,
    };
  });
}

await page.goto(`${BASE}/revolution#pair=${encodeURIComponent(ticket)}`, { waitUntil: "networkidle", timeout: 60000 });
await page.waitForTimeout(5000);
note(`ENTRY jump=${await page.locator('[data-testid="rev-jump-clock"]').count()} clock=${await page.locator('[data-testid="rev-classroom-clock"]').count()}`);
const jump = page.locator('[data-testid="rev-jump-clock"]').first();
if (await jump.count()) { await jump.click().catch(() => {}); await page.waitForTimeout(1600); }
const start = page.getByRole("button", { name: /开演/ }).first();
if (await start.count()) { await start.scrollIntoViewIfNeeded().catch(() => {}); await start.click().catch(() => {}); }
await page.waitForTimeout(5200);
note(`STARTED ${JSON.stringify(await readRunText())}`);
note(`START_PROGRESS ${JSON.stringify(await readProgress())}`);
await shot("guardian-live-78-start.png");

const closure = page.getByRole("button", { name: "闭馆", exact: true }).first();
note(`CLOSURE_BUTTON ${await closure.count()}`);
if (await closure.count()) {
  await closure.scrollIntoViewIfNeeded().catch(() => {});
  await closure.click().catch(() => {});
  await page.waitForTimeout(4500);
  note(`AFTER_SCENE ${JSON.stringify(await readRunText())}`);
  note(`AFTER_SCENE_PROGRESS ${JSON.stringify(await readProgress())}`);
  await shot("guardian-live-78-scene.png");
}

const guardian = page.getByRole("button", { name: "交给守护助手" }).first();
note(`GUARDIAN_BUTTON ${await guardian.count()}`);
if (await guardian.count()) {
  await guardian.scrollIntoViewIfNeeded().catch(() => {});
  await guardian.click().catch(() => {});
  const began = Date.now();
  for (let tick = 0; tick < 64; tick += 1) {
    await page.waitForTimeout(5000);
    const progress = await readProgress();
    const state = progress.run ? progress.run.status : "NO_RUN";
    note(`POLL ${tick} elapsed_s=${Math.round((Date.now() - began) / 1000)} status=${state} seq=${progress.run ? progress.run.sequence : "-"} proposals=${JSON.stringify(progress.proposals || [])} runs=${JSON.stringify(progress.guardian_runs || [])} outcome=${JSON.stringify(progress.outcome || null)}`);
    if (state === "PAUSED_FOR_ACCEPTANCE" || state === "PAUSED_MODEL_UNAVAILABLE" || state === "SIMULATED_COMPLETED") break;
  }
  note(`AFTER_GUARDIAN ${JSON.stringify(await readRunText())}`);
  note(`AFTER_GUARDIAN_PROGRESS ${JSON.stringify(await readProgress())}`);
  await shot("guardian-live-78-after-guardian.png");
}

const guardianTab = page.getByRole("button", { name: "行程守护", exact: true }).first();
if (await guardianTab.count()) {
  await guardianTab.scrollIntoViewIfNeeded().catch(() => {});
  await guardianTab.click().catch(() => {});
  await page.waitForTimeout(2200);
}
const accept = page.locator('[data-testid="rev-guardian-accept-replan"]').first();
note(`ACCEPT_BUTTON ${await accept.count()}`);
if (await accept.count()) {
  await accept.scrollIntoViewIfNeeded().catch(() => {});
  await accept.click().catch(() => {});
  await page.waitForTimeout(5000);
  note(`AFTER_ACCEPT ${JSON.stringify(await readRunText())}`);
  note(`AFTER_ACCEPT_PROGRESS ${JSON.stringify(await readProgress())}`);
  await shot("guardian-live-78-accepted.png");
}

const resume = page.getByRole("button", { name: /继续模拟/ }).first();
note(`RESUME_BUTTON ${await resume.count()}`);
if (await resume.count()) {
  await resume.scrollIntoViewIfNeeded().catch(() => {});
  await resume.click().catch(() => {});
  await page.waitForTimeout(6000);
  note(`AFTER_RESUME ${JSON.stringify(await readRunText())}`);
  note(`AFTER_RESUME_PROGRESS ${JSON.stringify(await readProgress())}`);
  await shot("guardian-live-78-resumed.png");
}

note(`ERRORS ${JSON.stringify(errors.slice(0, 3))}`);
await browser.close();
