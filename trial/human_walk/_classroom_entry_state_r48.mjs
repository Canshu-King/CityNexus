import { chromium } from "file:///D:/moodle/_cmdr_rescue_v3_1022/frontend/node_modules/playwright/index.mjs";
import fs from "node:fs";
const BASE = "http://127.0.0.1:14492";
const OUT = "D:/moodle/_cmdr_rescue_v3_1022/trial/results/20261022_v3_human_chrome";
const NL = String.fromCharCode(10);
const lines = [];
const note = (v) => { lines.push(v); fs.writeFileSync(OUT + "/classroom-entry-state-48.txt", lines.join(NL) + NL, "utf8"); };

const browser = await chromium.launch({ headless: true });
const ctx = await browser.newContext({ viewport: { width: 430, height: 932 }, deviceScaleFactor: 1 });
const page = await ctx.newPage();
await page.goto(BASE + "/revolution", { waitUntil: "domcontentloaded", timeout: 60000 });
const state = await page.evaluate(async () => {
  const read = async (path, token) => {
    const answer = await fetch(path, { headers: token ? { Authorization: "Bearer " + token } : {} });
    let body = {};
    try { body = await answer.json(); } catch { /* keep empty */ }
    return { status: answer.status, body };
  };
  const session = await read("/api/v1/demo/session");
  const token = session.body?.access_token;
  const journeyId = session.body?.journey_id;
  const journey = journeyId ? await read("/api/v1/journeys/" + journeyId, token) : { status: 0 };
  const twin = journeyId ? await read("/api/v1/journeys/" + journeyId + "/twin", token) : { status: 0 };
  return {
    session: { status: session.status, traveler: session.body?.traveler_id, journey_id: journeyId },
    journey: { status: journey.status, journey_status: journey.body?.status, active_plan: journey.body?.active_plan_version_id },
    twin: { status: twin.status, active_plan: twin.body?.active_plan_version_id },
  };
});
note(`STATE ${JSON.stringify(state)}`);
await ctx.close();
await browser.close();
