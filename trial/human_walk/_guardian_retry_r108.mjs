import { chromium } from "file:///D:/moodle/_cmdr_rescue_v3_1022/frontend/node_modules/playwright/index.mjs";
import fs from "node:fs";

const BASE = "http://localhost:14495";
const OUT = "D:/moodle/_cmdr_rescue_v3_1022/trial/results/20261022_v3_human_chrome/guardian-retry-108.txt";
const SHOT_BEFORE = "D:/moodle/_cmdr_rescue_v3_1022/trial/results/20261022_v3_human_chrome/guardian-retry-108-before.png";
const SHOT_AFTER = "D:/moodle/_cmdr_rescue_v3_1022/trial/results/20261022_v3_human_chrome/guardian-retry-108-after.png";
const TICKET_FILE = "D:/moodle/_cmdr_v3_live_1022/.demo_pairing_ticket_108.json";
const NL = String.fromCharCode(10);
const lines = [];
const note = (value) => { lines.push(value); fs.writeFileSync(OUT, lines.join(NL) + NL, "utf8"); };
const { ticket } = JSON.parse(fs.readFileSync(TICKET_FILE, "utf8"));

const browser = await chromium.launch({ headless: true });
const ctx = await browser.newContext({ viewport: { width: 390, height: 844 }, deviceScaleFactor: 1 });
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
    if (!run || !run.run_id) return { jid, current };
    const body = await fetch(`/api/v1/journeys/${jid}/simulation/runs/${run.run_id}/progress`, { headers, cache: "no-store" })
      .then((response) => response.json()).catch(() => null);
    return {
      status: run.status, sequence: run.sequence,
      proposals: ((body && body.proposals) || []).map((item) => ({ id: item.id, status: item.status })),
      runs: ((body && body.guardian_runs) || []).map((item) => ({ status: item.status, action: item.action_status, error: item.error_code })),
      outcome: (body && body.guardian_outcome) || null,
      pending: (body && body.readiness && body.readiness.pending_event_id) || null,
    };
  });
}

await page.goto(`${BASE}/revolution#pair=${encodeURIComponent(ticket)}`, { waitUntil: "networkidle", timeout: 60000 });
await page.waitForTimeout(5200);
const jump = page.locator('[data-testid="rev-jump-clock"]').first();
if (await jump.count()) { await jump.click().catch(() => {}); await page.waitForTimeout(1200); }
const before = await progress();
note(`BEFORE ${JSON.stringify(before)}`);

const retry = page.locator('[data-testid="rev-presenter-guardian-retry"]').first();
note(`RETRY_BUTTON ${await retry.count()}`);
if (await retry.count()) {
  await retry.scrollIntoViewIfNeeded().catch(() => {});
  await page.waitForTimeout(400);
  const hit = await retry.evaluate((node) => {
    const box = node.getBoundingClientRect();
    const x = box.left + box.width / 2;
    const y = box.top + box.height / 2;
    const top = document.elementFromPoint(x, y);
    const style = window.getComputedStyle(node);
    return {
      visible: box.width > 0 && box.height > 0,
      inViewport: box.top >= 0 && box.bottom <= window.innerHeight,
      hitSelf: Boolean(top) && (node === top || node.contains(top)),
      disabled: node.disabled === true,
      text: (node.textContent || "").trim(),
      fontOpacity: style.opacity,
    };
  });
  note(`RETRY_HIT ${JSON.stringify(hit)}`);
  await page.screenshot({ path: SHOT_BEFORE, fullPage: false });
  if (hit.visible && hit.hitSelf && !hit.disabled) {
    await retry.click();
    note("CLICKED");
    const began = Date.now();
    let last = "";
    for (let tick = 0; tick < 70; tick += 1) {
      await page.waitForTimeout(6000);
      const p = await progress();
      const state = p.status || "NO_RUN";
      const line = `WATCH ${tick} elapsed_s=${Math.round((Date.now() - began) / 1000)} status=${state} seq=${p.sequence} outcome=${JSON.stringify(p.outcome)} runs=${JSON.stringify(p.runs)} proposals=${JSON.stringify(p.proposals)}`;
      if (state !== last || tick % 5 === 0) note(line);
      last = state;
      if (state === "PAUSED_FOR_ACCEPTANCE" || state === "SIMULATED_COMPLETED") break;
      if (state === "PAUSED_MODEL_UNAVAILABLE" && tick > 2) break;
    }
  }
} else {
  await page.screenshot({ path: SHOT_BEFORE, fullPage: false });
}
note(`FINAL ${JSON.stringify(await progress())}`);
const afterPanel = await page.locator('[data-testid="rev-presenter-acceptance-step"]').count();
note(`ACCEPTANCE_STEP ${afterPanel}`);
note(`ERRORS ${JSON.stringify(errors.slice(0, 3))}`);
await page.screenshot({ path: SHOT_AFTER, fullPage: false });
await browser.close();
