import { chromium } from "file:///D:/moodle/_cmdr_rescue_v3_1022/frontend/node_modules/playwright/index.mjs";
import fs from "node:fs";

const BASE = process.env.PAIR_BASE || "http://127.0.0.1:14492";
const OUT = process.env.PAIR_OUT || "D:/moodle/_cmdr_rescue_v3_1022/trial/results/20261022_v3_human_chrome/guardian-accept-79.txt";
const TICKET_FILE = "D:/moodle/_cmdr_v3_live_1022/.demo_pairing_ticket";
const SHOT_DIR = "D:/moodle/_cmdr_rescue_v3_1022/trial/results/20261022_v3_human_chrome";
const NL = String.fromCharCode(10);
const lines = [];
const note = (value) => { lines.push(value); fs.writeFileSync(OUT, lines.join(NL) + NL, "utf8"); };
const raw = JSON.parse(fs.readFileSync(TICKET_FILE, "utf8"));
const tickets = (raw.tickets && raw.tickets.length ? raw.tickets : [raw.ticket]).filter(Boolean);
const offset = Number(process.env.PAIR_TICKET_OFFSET || 1);
const ticket = process.env.PAIR_TICKET || tickets[offset] || tickets[0];

const browser = await chromium.launch({ headless: true });
const ctx = await browser.newContext({ viewport: { width: 390, height: 844 }, deviceScaleFactor: 1 });
const page = await ctx.newPage();
const errors = [];
const responses = [];
page.on("pageerror", (error) => errors.push(String(error).slice(0, 160)));
page.on("response", (response) => {
  const url = response.url();
  if (/replan|accept|simulation|plans\//.test(url)) {
    responses.push({ status: response.status(), url: url.replace(/^https?:\/\/[^/]+/, "").slice(0, 120) });
  }
});
const shot = async (name) => {
  await page.screenshot({ path: `${SHOT_DIR}/${name}`, fullPage: false });
};

async function readRunText() {
  return page.evaluate(() => {
    const node = document.querySelector('[data-testid="rev-presenter-run"]');
    const acceptance = document.querySelector('[data-testid="rev-presenter-acceptance-note"]');
    const message = document.querySelector('[data-testid="rev-presenter-message"]');
    const proposal = document.querySelector('[data-testid="rev-guardian-proposal-diff"]');
    const proposalNote = document.querySelector('[data-testid="rev-guardian-proposal-note"]');
    return {
      run: node ? node.textContent : null,
      acceptanceNote: Boolean(acceptance),
      message: message ? message.textContent : null,
      proposal: proposal ? proposal.textContent : null,
      proposalNote: proposalNote ? proposalNote.textContent : null,
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
      .then((response) => response.json()).catch((error) => ({ fetch_error: String(error).slice(0, 120) }));
    const run = current && (current.run || current);
    if (!run || !run.run_id) return { jid, current };
    const progress = await fetch(`/api/v1/journeys/${jid}/simulation/runs/${run.run_id}/progress`, { headers, cache: "no-store" })
      .then((response) => response.json()).catch(() => null);
    return {
      jid,
      run: { id: run.run_id, status: run.status, sequence: run.sequence, plan: run.state && run.state.plan_version_id, event: run.state && run.state.pending_event_id },
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
note(`ENTRY ${JSON.stringify(await readRunText())}`);
note(`ENTRY_PROGRESS ${JSON.stringify(await readProgress())}`);
await shot("guardian-accept-79-entry.png");

const guardianTab = page.getByRole("button", { name: "行程守护", exact: true }).first();
note(`GUARDIAN_TAB ${await guardianTab.count()}`);
if (await guardianTab.count()) {
  await guardianTab.scrollIntoViewIfNeeded().catch(() => {});
  await guardianTab.click().catch(() => {});
  await page.waitForTimeout(5000);
}
note(`BEFORE_ACCEPT ${JSON.stringify(await readRunText())}`);
const accept = page.locator('[data-testid="rev-guardian-accept-replan"]').first();
note(`ACCEPT_BUTTON ${await accept.count()} disabled=${await accept.isDisabled().catch(() => null)}`);
await shot("guardian-accept-79-before.png");
if (await accept.count()) {
  await accept.scrollIntoViewIfNeeded().catch(() => {});
  await accept.click().catch((error) => note(`ACCEPT_CLICK_ERROR ${String(error).slice(0, 120)}`));
  await page.waitForTimeout(10000);
  note(`AFTER_ACCEPT ${JSON.stringify(await readRunText())}`);
  note(`AFTER_ACCEPT_PROGRESS ${JSON.stringify(await readProgress())}`);
  await shot("guardian-accept-79-after.png");
}
const resume = page.getByRole("button", { name: /继续模拟/ }).first();
note(`RESUME_BUTTON ${await resume.count()}`);
if (await resume.count()) {
  await resume.scrollIntoViewIfNeeded().catch(() => {});
  await resume.click().catch(() => {});
  await page.waitForTimeout(7000);
  note(`AFTER_RESUME ${JSON.stringify(await readRunText())}`);
  note(`AFTER_RESUME_PROGRESS ${JSON.stringify(await readProgress())}`);
  await shot("guardian-accept-79-resumed.png");
}
note(`RESPONSES ${JSON.stringify(responses.slice(-14))}`);
note(`ERRORS ${JSON.stringify(errors.slice(0, 3))}`);
await browser.close();
