/**
 * Press the last door on the journey that is already on the screen.
 *
 * walk-99's tab still holds a live draft (eight rows, its own signed session in that tab's sessionStorage),
 * and the model needed ~eight minutes to get there -- longer than any walk budget I want to burn again.
 * A traveller who came back to their own tab would not start a new trip; they would finish this one.  So this
 * continues in that tab with the same buttons: move one row to a time no opening can contain, save, press
 * 选用这份方案, and write down the sentence the screen answers with.
 *
 * Nothing is seeded: no API call, no localStorage write, no pre-built state. Reads of storage are only to
 * identify the tab.
 */
import fs from "node:fs";
import path from "node:path";
import { createRequire } from "node:module";

const require = createRequire("D:/moodle/_cmdr_rescue_v3_1022/frontend/package.json");
const { chromium } = require("playwright");

const OUT = "D:/moodle/_cmdr_rescue_v3_1022/trial/results/20261022_v3_human_chrome";
const stream = fs.openSync(path.join(OUT, process.env.PROBE_LOG || "press-the-door-1.txt"), "a");
const flat = (v) => String(v ?? "").replace(/\s+/g, " ").trim();
const say = (t) => { fs.writeSync(stream, t + "\n"); process.stdout.write(t + "\n"); };

const browser = await chromium.connectOverCDP("http://127.0.0.1:9335", { timeout: 120000 });
const context = browser.contexts()[0] ?? await browser.newContext();
let page = null;
for (const candidate of context.pages()) {
  const slots = await candidate.locator(".rev-goal-draft-slot").count().catch(() => 0);
  const url = candidate.url() || "";
  say(`CANDIDATE ${url.slice(19, 25)} slots=${slots}`);
  if (slots > 0 && url.includes("14496")) page = candidate;
}
if (!page) { say("NO_TAB_WITH_DRAFT"); process.exit(0); }
await page.bringToFront().catch(() => undefined);
await page.waitForTimeout(2000);
const read = async (locator, limit = 400) => flat(await locator.innerText({ timeout: 5000 }).catch(() => "(unreadable)")).slice(0, limit);

const layerTo = async (testId) => {
  const node = page.getByTestId(testId).first();
  await node.scrollIntoViewIfNeeded().catch(() => undefined);
  await node.click({ timeout: 6000 }).catch((e) => say(`LAYER_ERR ${testId} ${flat(e.message).slice(0, 50)}`));
  await page.waitForTimeout(2200);
};

await layerTo("rev-mission-layer-timeline");
const departure = page.locator(".rev-v3-departure");
say(`STEP_A_DEPARTURE_VISIBLE=${await departure.first().isVisible().catch(() => false)}`);
say(`STEP_A_CARD ${await read(departure, 500)}`);
const continueButton = departure.getByRole("button", { name: /从这份安排继续/ }).first();
if (await continueButton.isVisible().catch(() => false)) {
  await continueButton.click({ timeout: 6000 }).catch((e) => say(`STEP_B_CONTINUE_ERR ${flat(e.message).slice(0, 50)}`));
  await page.waitForTimeout(4000);
  say(`STEP_B_AFTER_CONTINUE ${await read(departure, 500)}`);
}
const timeFields = departure.locator('input[type="time"]');
const before = await timeFields.evaluateAll((nodes) => nodes.slice(0, 4).map((n) => n.value)).catch(() => []);
say(`STEP_C_TIME_FIELDS=${before.length} first_four=${JSON.stringify(before)}`);
await timeFields.first().fill("03:00").catch((e) => say(`STEP_C_FILL_START_ERR ${flat(e.message).slice(0, 50)}`));
await timeFields.nth(1).fill("04:00").catch((e) => say(`STEP_C_FILL_END_ERR ${flat(e.message).slice(0, 50)}`));
const after = await timeFields.evaluateAll((nodes) => nodes.slice(0, 2).map((n) => n.value)).catch(() => []);
say(`STEP_C_WRITTEN first_two=${JSON.stringify(after)}`);
await departure.locator("input[type=checkbox]").first().click({ timeout: 6000 }).catch((e) => say(`STEP_C_TICK_ERR ${flat(e.message).slice(0, 50)}`));
await page.waitForTimeout(1500);
await departure.getByRole("button", { name: /保存为正式候选方案/ }).first().click({ timeout: 8000 })
  .catch((e) => say(`STEP_D_SAVE_ERR ${flat(e.message).slice(0, 60)}`));
for (let poll = 1; poll <= 12; poll += 1) {
  await page.waitForTimeout(5000);
  const status = await read(page.locator(".rev-v3-departure p[role=status]").first(), 200);
  if (status && status !== "(unreadable)") { say(`STEP_D_SAVE_STATUS ${status}`); break; }
  if (poll === 12) say("STEP_D_SAVE_STATUS (none after 60s)");
}
await layerTo("rev-mission-layer-timeline");
const workbench = page.locator('[data-testid="rev-plan-workbench"]').first();
say(`STEP_E_WORKBENCH ${await read(workbench, 500)}`);
const select = page.getByTestId("rev-plan-select");
say(`STEP_E_SELECT_BUTTONS=${await select.count().catch(() => -1)} VISIBLE=${await select.first().isVisible().catch(() => false)}`);
if (await select.first().isVisible().catch(() => false)) {
  await select.first().click({ timeout: 8000 }).catch((e) => say(`STEP_F_SELECT_ERR ${flat(e.message).slice(0, 60)}`));
  for (let poll = 1; poll <= 10; poll += 1) {
    await page.waitForTimeout(4000);
    const text = await read(workbench, 400);
    if (/排不下|已开始|等待正式计划/.test(text)) { say(`STEP_F_AFTER_SELECT ${text}`); break; }
    if (poll === 10) say(`STEP_F_AFTER_SELECT (no change) ${text.slice(0, 200)}`);
  }
}
await page.screenshot({ path: path.join(OUT, "door-pressed-01.png"), fullPage: false }).catch((e) => say(`SHOT_ERR ${flat(e.message).slice(0, 50)}`));
say(`SHOT door-pressed-01.png bytes=${fs.statSync(path.join(OUT, "door-pressed-01.png")).size}`);
say(`DONE ${new Date().toISOString()}`);
await browser.close().catch(() => undefined);
