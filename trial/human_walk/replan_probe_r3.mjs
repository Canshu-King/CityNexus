/**
 * Continue the 少走路 trip that is already running in its own tab, then press what the new door offers.
 *
 * Why a second instrument instead of re-running the first: `replan_walk_r1` settled too early -- its wait
 * loop returned as soon as the dock stopped matching 正在推进|正在研究, while the product's mid-round
 * sentence is 「Agent 正在处理，请稍后继续发消息」 (trial/results/20261022_v3_human_chrome/
 * replan-walk-1-log.txt:11-19), so it reached the card at `slots=0` and had nothing to tighten.
 * r29's own settle requires BOTH the quiet dock and the extra condition; this file copies that shape and
 * adds the answering arm r29 needed (a draft does not appear until the Agent's question is answered).
 *
 * Still nothing seeded: the goal was typed by walk r1, the reply here is a keystroke into the same dock
 * textarea, the hours are typed into the card's own inputs, and every reading is rendered text.
 */
import fs from "node:fs";
import path from "node:path";
import { createRequire } from "node:module";

const require = createRequire("D:/moodle/_cmdr_rescue_v3_1022/frontend/package.json");
const { chromium } = require("playwright");

const SHOTS = "D:/moodle/_cmdr_rescue_v3_1022/trial/results/20261022_v3_human_chrome";
const ORIGIN = process.env.RECOV_ORIGIN || "http://127.0.0.1:14472";
const LOG = path.join(SHOTS, process.env.LOG_NAME || "replan-probe-3-log.txt");
const lines = [];
const say = (text) => { lines.push(text); console.log(text); fs.writeFileSync(LOG, lines.join("\n") + "\n"); };
const flat = (value) => String(value || "").replace(/\s+/g, " ").trim();

const browser = await chromium.connectOverCDP("http://127.0.0.1:9335", { timeout: 30000 });
const context = browser.contexts()[0];

// Pick the page the way the product lets a traveller pick it: same origin, one cockpit, and the pointer
// in that page's own storage.  Two pages claiming the same journey would be a污染, so refuse.
const marks = [];
for (const candidate of context.pages()) {
  const url = candidate.url();
  if (!url.startsWith(ORIGIN)) continue;
  const mark = await candidate.evaluate(() => ({
    tabs: document.querySelectorAll(".cn-mission-layer-tabs [role=tab], .cn-mission-layer-tabs button").length,
    dock: Boolean(document.querySelector(".rev-mission-chat-dock")),
    slots: document.querySelectorAll(".rev-goal-draft-slot").length,
    departure: Boolean(document.querySelector(".rev-v3-departure")),
    pointer: (Object.entries(localStorage).filter(([key]) => /journey/i.test(key))
      .map(([, value]) => String(value).slice(0, 20))[0]) || "(none)",
    status: (document.querySelector('[data-testid="rev-dock-status"]')?.innerText || "").replace(/\s+/g, " ").trim().slice(0, 90),
  })).catch((error) => ({ evaluate_error: flat(error.message).slice(0, 120) }));
  marks.push({ url, mark });
}
marks.forEach((row, index) => say(`CANDIDATE_${index} ${JSON.stringify(row)}`));
const qualifying = marks.filter((row) => row.mark && row.mark.tabs > 0);
if (qualifying.length !== 1) {
  say(`REFUSE qualifying_tabs=${qualifying.length} -- 这一源必须恰好一枚驾驶舱，按错就是污染别人的走查`);
  process.exit(1);
}
const page = qualifying[0] && context.pages().find((row) => row.url() === qualifying[0].url);
await page.bringToFront();
await page.setViewportSize({ width: 390, height: 844 });

const body = (limit) => page.evaluate(() => document.body.innerText.replace(/\s+/g, " ").trim().slice(0, 500))
  .then((text) => flat(text).slice(0, limit)).catch(() => "(unreadable)");
const read = async (locator, limit) => flat(await locator.first().innerText({ timeout: 6000 }).catch(() => "(unreadable)")).slice(0, limit);
const shot = async (name) => {
  const buffer = await page.screenshot({ path: path.join(SHOTS, name), fullPage: false, timeout: 30000 }).catch(() => null);
  say(`SHOT ${name} bytes=${buffer ? buffer.length : 0}`);
};
const wire = [];
page.on("response", (response) => {
  const url = response.url();
  if (/travel-gaps|freeze-routes|prepare-plan/.test(url)) {
    wire.push({ at: new Date().toISOString(), method: response.request().method(), status: response.status(),
                what: url.replace(/^.*\/api\/v1/, "").replace(/[0-9a-f]{8}-[0-9a-f-]{27}/g, "<id>").slice(-58) });
  }
});

const settle = async (minutes, extra) => {
  for (let poll = 1; poll <= minutes * 6; poll += 1) {
    await page.waitForTimeout(10000);
    const busy = /正在处理|正在推进|正在研究|回复中/.test(await body(300));
    if (!busy && poll >= 2 && (!extra || await extra())) { say(`SETTLED ticks=${poll} elapsed_s=${poll * 10}`); return true; }
    if (poll % 6 === 0) say(`WAIT_${poll * 10}s busy=${busy} dock=${await read(page.locator('[data-testid="rev-dock-status"]').first(), 140)}`);
  }
  say(`SETTLE_TIMEOUT minutes=${minutes} dock=${await read(page.locator('[data-testid="rev-dock-status"]').first(), 140)}`);
  return false;
};
const layerTo = async (testId) => {
  for (let attempt = 1; attempt <= 3; attempt += 1) {
    const button = page.locator(`[data-testid="${testId}"]`).first();
    await button.scrollIntoViewIfNeeded().catch(() => undefined);
    await page.waitForTimeout(500);
    const clicked = await button.click({ timeout: 6000 }).then(() => true).catch(() => false);
    say(`LAYER ${testId} attempt=${attempt} clicked=${clicked}`);
    if (clicked) return true;
    await page.waitForTimeout(2500);
  }
  return false;
};
const firstTap = async (testId) => {
  const handle = await page.locator(`[data-testid="${testId}"]`).first().elementHandle({ timeout: 8000 }).catch(() => null);
  if (!handle) return { testId, present: false };
  await handle.scrollIntoViewIfNeeded().catch(() => undefined);
  await page.waitForTimeout(600);
  const probe = await page.evaluate((id) => {
    const node = document.querySelector(`[data-testid="${id}"]`);
    if (!node) return null;
    const box = node.getBoundingClientRect();
    const cx = Math.round(box.left + box.width / 2);
    const cy = Math.round(box.top + box.height / 2);
    const cover = document.elementFromPoint(cx, cy);
    return { text: (node.innerText || "").replace(/\s+/g, " ").trim().slice(0, 40), centre: [cx, cy],
             disabled: Boolean(node.disabled), covers_it: cover !== node,
             topmost: cover ? (cover.tagName === "BUTTON" ? "BUTTON" : String(cover.className || cover.tagName)) : null,
             in_viewport: box.top >= 0 && box.bottom <= window.innerHeight };
  }, testId).catch((error) => ({ evaluate_error: flat(error.message).slice(0, 160) }));
  if (!probe) return { testId, present: false, note: "node gone" };
  if (probe.disabled) return { testId, present: true, probe, pressed: false };
  await page.mouse.click(probe.centre[0], probe.centre[1]);
  return { testId, present: true, probe, pressed: true, at: new Date().toISOString() };
};

say(`PROBE2_START ${new Date().toISOString()} ${ORIGIN} mark=${JSON.stringify(qualifying[0].mark)}`);

await layerTo("rev-mission-layer-agent");
for (let round = 1; round <= 4 && (await page.locator(".rev-goal-draft-slot").count()) === 0; round += 1) {
  const choices = page.locator(".rev-agent-choices button");
  if (await choices.count().catch(() => 0) > 0) {
    say(`ROUND_${round}_CHOICES ${await choices.count()} first=${flat(await choices.first().innerText().catch(() => "")).slice(0, 40)}`);
    await choices.first().click({ timeout: 6000 }).catch(() => undefined);
  } else {
    const replyBox = page.locator("#rev-mission-chat-input");
    await replyBox.scrollIntoViewIfNeeded().catch(() => undefined);
    await replyBox.fill("就按我说的城市和天数先排一版草案，缺的资料你按常识补上并标成待核实，不用再问我。")
      .catch((error) => say(`ROUND_${round}_FILL_ERR ${flat(error.message).slice(0, 60)}`));
    await page.locator(".rev-mission-chat-dock button[type=submit]").first().click({ timeout: 8000 })
      .catch((error) => say(`ROUND_${round}_SEND_ERR ${flat(error.message).slice(0, 60)}`));
    say(`ROUND_${round}_REPLIED at ${new Date().toISOString()}`);
  }
  await settle(14, async () => (await page.locator(".rev-goal-draft-slot").count()) > 0);
  say(`ROUND_${round} slots=${await page.locator(".rev-goal-draft-slot").count()} dock=${await read(page.locator('[data-testid="rev-dock-status"]').first(), 120)}`);
}
const slots = await page.locator(".rev-goal-draft-slot").count();
say(`DRAFT_SLOTS=${slots}`);
if (!slots) { say("ABORT no draft -- 不发明一版草案，交回现场读数"); process.exit(1); }

// The plan the traveller picks: r29 learned that the version without a long intercity hop never exercises
// the transit arm, so pick the card that keeps 长城/颐和园 in it -- here, any card whose own text names a
// place far from the city centre, else the first one.
const cards = page.locator(".rev-goal-variant-card");
const cardCount = await cards.count().catch(() => 0);
say(`VARIANT_CARDS=${cardCount}`);
if (cardCount > 0) {
  let pick = 0;
  for (let index = 0; index < cardCount; index += 1) {
    const text = flat(await cards.nth(index).innerText().catch(() => ""));
    say(`CARD_${index} ${text.slice(0, 70)}`);
    if (/八达岭|长城|颐和园|香山/.test(text)) { pick = index; break; }
  }
  const choose = cards.nth(pick).getByRole("button", { name: /选用这份安排/ }).first();
  if (await choose.isVisible().catch(() => false)) {
    await choose.click({ timeout: 8000 }).catch((error) => say(`CHOOSE_ERR ${flat(error.message).slice(0, 60)}`));
    say(`CHOSEN_CARD=${pick} at ${new Date().toISOString()}`);
    await page.waitForTimeout(9000);
  } else say(`CHOOSE_INVISIBLE card=${pick}`);
}

await layerTo("rev-mission-layer-timeline");
const departure = page.locator(".rev-v3-departure");
if (!(await departure.isVisible().catch(() => false))) {
  await page.getByRole("button", { name: /准备出发/ }).first().click({ timeout: 6000 }).catch(() => undefined);
  await page.waitForTimeout(3500);
}
say(`DEPARTURE_VISIBLE=${await departure.isVisible().catch(() => false)}`);
if (!(await departure.isVisible().catch(() => false))) { say("ABORT no departure card"); process.exit(1); }
// A closed <details> renders no inputs, so open the time block before reading it.
await page.locator(".rev-v3-departure details").first().evaluate((node) => { node.open = true; })
  .catch(() => say("DETAILS_OPEN_ERR"));
await page.waitForTimeout(1200);

const timeFields = page.locator('.rev-v3-departure input[type="time"]');
const values = await timeFields.evaluateAll((nodes) => nodes.map((node) => node.value)).catch(() => []);
say(`WINDOWS_BEFORE ${JSON.stringify(values)}`);
const addMinutes = (hhmm, delta) => {
  const [hh, mm] = String(hhmm || "09:00").split(":").map(Number);
  const total = Math.min(22 * 60, (hh * 60 + mm) + delta);
  return String(Math.floor(total / 60)).padStart(2, "0") + ":" + String(total % 60).padStart(2, "0");
};
for (let index = 2; index < Math.min(values.length, 8); index += 2) {
  const start = values[index - 1] || "10:00";
  const end = addMinutes(start, 45);
  await timeFields.nth(index).fill(start).catch((error) => say(`FILL_START_ERR ${flat(error.message).slice(0, 60)}`));
  await timeFields.nth(index + 1).fill(end).catch((error) => say(`FILL_END_ERR ${flat(error.message).slice(0, 60)}`));
  values[index] = start; values[index + 1] = end;
  say(`TIGHTENED row=${index / 2 + 1} window=${start}-${end}`);
}
const afterTighten = await timeFields.evaluateAll((nodes) => nodes.map((node) => node.value)).catch(() => []);
say(`WINDOWS_AFTER ${JSON.stringify(afterTighten)}`);
await page.locator('.rev-v3-departure input[type="checkbox"]').first().check({ timeout: 5000 }).catch(() => undefined);
await page.getByRole("button", { name: /保存为正式候选方案/ }).first().click({ timeout: 8000 })
  .catch((error) => say(`SAVE_ERR ${flat(error.message).slice(0, 60)}`));
await page.waitForTimeout(10000);
say(`AFTER_SAVE_STATUS ${await read(page.locator(".rev-v3-departure p[role=status]"), 260)}`);
await shot("replan-probe3-01-saved.png");

const routeState = page.getByTestId("rev-v3-route-state");
say(`ROUTE_BEFORE ${await read(routeState, 220)}`);
let band = "";
for (let round = 1; round <= 3; round += 1) {
  const press = await firstTap("rev-v3-freeze-routes");
  say(`FREEZE_PRESS round=${round} ${JSON.stringify(press)}`);
  for (let poll = 1; poll <= 14; poll += 1) {
    await page.waitForTimeout(5000);
    band = await read(routeState, 220);
    if (band && !/还没有向高德核实/.test(band) && poll > 2) break;
  }
  const cardNow = await read(departure, 1400);
  say(`FREEZE_ROUND_${round} BAND ${band} TODO_ROUTE_LINES=${(cardNow.match(/转场路线/g) || []).length}`);
  if (/已冻结进这版方案/.test(band)) { say(`FROZEN_ON_ROUND=${round}`); break; }
}
await shot("replan-probe3-02-frozen.png");
// The door now distinguishes the two empty answers; if this journey is the unbound one, say so and stop
// rather than reporting a travel-gaps result that was never reachable.
if (/还没有被认成正式地点/.test(band)) {
  say("UNBOUND_STATE=true -- 这几处没有一处被认成正式地点，转场没有可量的两站；这一趟不能当作 travel-gaps 的证据");
  say(`WIRE ${JSON.stringify(wire)}`);
  process.exit(1);
}
say(`HOP_REFUSALS ${JSON.stringify(await page.getByTestId("rev-v3-hop-refusal").allInnerTexts().catch(() => []))}`);

const gapsBlock = page.getByTestId("rev-v3-travel-gaps");
const shortfalls = await page.getByTestId("rev-v3-gap-shortfall").allInnerTexts().catch(() => []);
say(`GAPS_PRESENT=${await gapsBlock.isVisible().catch(() => false)}`);
say(`GAPS_BLOCK_TEXT ${flat(await gapsBlock.innerText().catch(() => "(none)")).slice(0, 300)}`);
say(`SHORTFALL_LINES ${JSON.stringify(shortfalls.map((line) => flat(line).slice(0, 110)))}`);
say(`REPLAN_REFUSAL ${await read(page.getByTestId("rev-v3-replan-refusal"), 200)}`);
await shot("replan-probe3-03-gaps.png");

const tapReplan = await firstTap("rev-v3-replan");
say(`REPLAN_TAP ${JSON.stringify(tapReplan)}`);
await page.waitForTimeout(2000);
const diff = await page.getByTestId("rev-v3-replan-diff").allInnerTexts().catch(() => []);
say(`DIFF_LINES ${JSON.stringify(diff.map((line) => flat(line).slice(0, 130)))}`);
await shot("replan-probe3-04-diff.png");

const beforeWindows = await timeFields.evaluateAll((nodes) => nodes.map((node) => node.value)).catch(() => []);
const tapApply = await firstTap("rev-v3-replan-apply");
say(`APPLY_TAP ${JSON.stringify(tapApply)}`);
await page.waitForTimeout(12000);
say(`AFTER_APPLY_STATUS ${await read(page.locator(".rev-v3-departure p[role=status]"), 320)}`);
say(`AFTER_APPLY_WINDOWS ${JSON.stringify(await timeFields.evaluateAll((nodes) => nodes.map((node) => node.value)).catch(() => []))}`);
say(`WINDOWS_BEFORE_APPLY ${JSON.stringify(beforeWindows)}`);
await shot("replan-probe3-05-after-apply.png");

await page.reload({ waitUntil: "domcontentloaded", timeout: 60000 });
await page.waitForTimeout(15000);
await layerTo("rev-mission-layer-timeline");
if (!(await departure.isVisible().catch(() => false))) {
  await page.getByRole("button", { name: /准备出发/ }).first().click({ timeout: 6000 }).catch(() => undefined);
  await page.waitForTimeout(3500);
}
say(`RELOAD_DEPARTURE_VISIBLE=${await departure.isVisible().catch(() => false)}`);
say(`RELOAD_ROUTE ${await read(routeState, 220)}`);
say(`RELOAD_GAPS_PRESENT=${await page.getByTestId("rev-v3-travel-gaps").isVisible().catch(() => false)}`);
await shot("replan-probe3-06-after-reload.png");
say(`WIRE ${JSON.stringify(wire)}`);
say("NOTE writes are the traveller's own: answering the Agent, typing hours, 保存为正式候选方案, 核实并冻结, and the two presses 根据路线重新安排 / 按这一版安排");
say("DONE tab left open");
