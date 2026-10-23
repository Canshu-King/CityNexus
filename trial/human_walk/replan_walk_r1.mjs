/**
 * Walk the traveller's own 少走路 trip to the departure card, then press what the new door offers.
 *
 * Nothing is seeded and no API shortcut is used: the goal is typed, the consent chips are tapped, the
 * send key is pressed, research is started by its own button, the hours are tightened by typing into the
 * card's own time inputs, and every reading below is rendered text.  The point being proven is that the
 * shortfall the 422 gate already refuses (backend/app/replanning/feasibility.py:1013) now has something
 * to press: 根据路线重新安排 shows a per-row diff, and 按这一版安排 writes a NEW CANDIDATE version.
 *
 * Run it on a stack started from the current tip: this instrument is the acceptance for code that did
 * not exist on the older stack, and a stale backend answers the new door with 404 (see the walkthrough's
 * section 31, where a stale process produced three 500s I first blamed on the product).
 */
import fs from "node:fs";
import path from "node:path";
import { createRequire } from "node:module";

const require = createRequire("D:/moodle/_cmdr_rescue_v3_1022/frontend/package.json");
const { chromium } = require("playwright");

const SHOTS = "D:/moodle/_cmdr_rescue_v3_1022/trial/results/20261022_v3_human_chrome";
const WEB = process.env.WALK_BASE || "http://127.0.0.1:14472/revolution";
const START = process.env.WALK_START_DATE || "2026-12-03";
const STORY = process.env.WALK_STORY || "12 月 3 日到 12 月 4 日在北京玩两天，人均预算 600。带爸妈，少走路，一天别排太满。第一天上午故宫，下午天坛公园，晚上南锣鼓巷；第二天上午颐和园，下午什刹海。";
const LOG = path.join(SHOTS, "replan-walk-1-log.txt");
const lines = [];
const say = (text) => { lines.push(text); console.log(text); fs.writeFileSync(LOG, lines.join("\n") + "\n"); };
const flat = (value) => String(value || "").replace(/\s+/g, " ").trim();
const read = async (locator, limit) => flat(await locator.first().innerText({ timeout: 6000 }).catch(() => "(unreadable)")).slice(0, limit);
const shot = async (name) => {
  const buffer = await page.screenshot({ path: path.join(SHOTS, name), fullPage: false, timeout: 30000 }).catch(() => null);
  say(`SHOT ${name} bytes=${buffer ? buffer.length : 0}`);
};

const browser = await chromium.connectOverCDP("http://127.0.0.1:9335", { timeout: 30000 });
const context = browser.contexts()[0];
const page = await context.newPage();
await page.setViewportSize({ width: 390, height: 844 });

const wire = [];
page.on("response", (response) => {
  const url = response.url();
  if (/travel-gaps|freeze-routes|prepare-plan/.test(url)) {
    wire.push({ at: new Date().toISOString(), method: response.request().method(),
                what: url.replace(/^.*\/api\/v1/, "").replace(/[0-9a-f]{8}-[0-9a-f-]{27}/g, "<id>").slice(-58),
                status: response.status() });
  }
});

// Press a control the way a finger does: scroll it in, read its own centre, check nothing else is on
// top of it, then click that point.  Returns what the hit test saw, so a miss is a reading, not a guess.
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
             topmost: cover ? (cover.tagName === "BUTTON" ? "BUTTON" : cover.className || cover.tagName) : null,
             in_viewport: box.top >= 0 && box.bottom <= window.innerHeight };
  }, testId).catch((error) => ({ evaluate_error: String(error).slice(0, 160) }));
  if (!probe) return { testId, present: false, note: "node gone" };
  if (probe.disabled) return { testId, present: true, probe, pressed: false, note: "disabled" };
  await page.mouse.click(probe.centre[0], probe.centre[1]);
  return { testId, present: true, probe, pressed: true, at: new Date().toISOString() };
};

const settle = async (ticks, pattern, done) => {
  for (let tick = 1; tick <= ticks; tick += 1) {
    await page.waitForTimeout(15000);
    if (done && await done()) { say(`SETTLED ticks=${tick} by_done`); return; }
    const dock = await read(page.getByTestId("rev-dock-status"), 160);
    if (dock !== "(unreadable)" && !new RegExp(pattern).test(dock)) { say(`SETTLED ticks=${tick} dock=${dock.slice(0, 90)}`); return; }
    say(`WAIT tick=${tick} dock=${dock.slice(0, 90)}`);
  }
};

say(`REPLAN_WALK_START ${new Date().toISOString()} ${WEB}`);
await page.goto(WEB, { waitUntil: "domcontentloaded", timeout: 60000 });
await page.waitForTimeout(3500);
await page.evaluate(() => { localStorage.clear(); sessionStorage.clear(); });
await page.reload({ waitUntil: "domcontentloaded" });
await page.waitForTimeout(3500);
say(`STEP_01 ${await read(page.locator("body"), 160)}`);

await page.getByTestId("rev-trip-goal").fill(STORY);
await page.getByLabel(/目的地/).first().fill("北京");
await page.getByText("日期与天数", { exact: false }).first().click();
await page.getByTestId("rev-trip-start-date").fill(START);
say(`STEP_02 days=${await page.getByTestId("rev-trip-duration").inputValue().catch(() => "(unreadable)")}`);
await page.getByRole("button", { name: /继续规划/ }).first().click();
await page.waitForTimeout(6000);
const strip = page.locator(".rev-mission-chat-dock > .rev-mission-chat-consent");
await strip.locator("label").nth(0).click({ timeout: 5000 }).catch(() => say("CONSENT_STRIP_ABSENT"));
await strip.locator("label").nth(1).click({ timeout: 5000 }).catch(() => undefined);
await page.waitForTimeout(700);
await page.locator("#rev-mission-chat-input").fill("先别问太多，按我说的直接安排，少走路这条记住。");
await page.locator(".rev-mission-chat-dock button[type=submit]").click({ timeout: 6000 }).catch(() => undefined);
say(`STEP_03 sent_at ${new Date().toISOString()}`);
await settle(5, "回复中|Agent 正在处理|正在推进|正在研究");
const choices = page.locator(".rev-agent-choices button");
if (await choices.count().catch(() => 0) > 0) {
  say(`STEP_04 choices=${await choices.count()} first=${flat(await choices.first().innerText().catch(() => "")).slice(0, 40)}`);
  await choices.first().click({ timeout: 6000 }).catch(() => undefined);
  await settle(4, "回复中|Agent 正在处理|正在推进");
}
let researchPressed = false;
for (let attempt = 1; attempt <= 3 && !researchPressed; attempt += 1) {
  const startButton = page.locator(".rev-agent-start-research").first();
  await startButton.scrollIntoViewIfNeeded().catch(() => undefined);
  await page.waitForTimeout(700);
  await startButton.click({ timeout: 8000 }).then(() => { researchPressed = true; })
    .catch((error) => say(`START_RESEARCH_RETRY attempt=${attempt} ${flat(error.message).slice(0, 60)}`));
}
say(`STEP_04B_START_RESEARCH pressed=${researchPressed}`);
await settle(18, "正在推进|正在研究", async () => (await page.locator(".rev-goal-draft-slot").count()) > 0);
say(`STEP_05_DRAFT slots=${await page.locator(".rev-goal-draft-slot").count()}`);

const departure = page.locator(".rev-v3-departure");
await page.locator('[data-testid="rev-mission-layer-timeline"]').first().click({ timeout: 6000 }).catch(() => undefined);
await page.waitForTimeout(2500);
if (!(await departure.isVisible().catch(() => false))) {
  await page.getByRole("button", { name: /准备出发/ }).first().click({ timeout: 6000 }).catch(() => undefined);
  await page.waitForTimeout(3500);
}
say(`STEP_06_DEPARTURE_VISIBLE=${await departure.isVisible().catch(() => false)}`);

// Tighten the same-day hours: a traveller who wants to see everything starts squeezing the gaps.
const timeFields = page.locator('.rev-v3-departure input[type="time"]');
const values = await timeFields.evaluateAll((nodes) => nodes.map((node) => node.value)).catch(() => []);
say(`STEP_07_WINDOWS ${JSON.stringify(values)}`);
const nextHour = (hhmm) => {
  const [hh, mm] = String(hhmm || "09:00").split(":").map(Number);
  const total = Math.min(21 * 60, hh * 60 + mm);
  return String(Math.floor(total / 60)).padStart(2, "0") + ":" + String(total % 60).padStart(2, "0");
};
for (let index = 2; index < Math.min(values.length, 6); index += 2) {
  const previousEnd = values[index - 1] || "10:00";
  const start = nextHour(previousEnd);
  const end = nextHour(`${start.slice(0, 2)}:${String(Number(start.slice(3)) + 45).padStart(2, "0")}`);
  await timeFields.nth(index).fill(start).catch((error) => say(`STEP_07_FILL_START_ERR ${flat(error.message).slice(0, 50)}`));
  await timeFields.nth(index + 1).fill(end).catch((error) => say(`STEP_07_FILL_END_ERR ${flat(error.message).slice(0, 50)}`));
  values[index] = start; values[index + 1] = end;
  say(`STEP_07_TIGHTENED row=${index / 2 + 1} window=${start}-${end}`);
}
await page.locator('.rev-v3-departure input[type="checkbox"]').first().check({ timeout: 5000 }).catch(() => undefined);
await page.getByRole("button", { name: /保存为正式候选方案/ }).first().click({ timeout: 8000 }).catch(() => undefined);
await page.waitForTimeout(9000);
const savedStatus = await read(page.locator(".rev-v3-departure p[role=status]"), 240);
say(`STEP_08_AFTER_SAVE status=${savedStatus}`);
await shot("replan-walk-08-after-save.png");

const routeState = page.getByTestId("rev-v3-route-state");
say(`STEP_09_ROUTE_BEFORE ${await read(routeState, 220)}`);
let band = "";
for (let round = 1; round <= 3; round += 1) {
  const press = await firstTap("rev-v3-freeze-routes");
  say(`STEP_09_FREEZE_PRESS round=${round} ${JSON.stringify(press)}`);
  for (let poll = 1; poll <= 12; poll += 1) {
    await page.waitForTimeout(5000);
    band = await read(routeState, 220);
    if (band && !/还没有向高德核实/.test(band) && poll > 1) break;
  }
  say(`STEP_09_ROUND_${round} BAND ${band}`);
  if (/已冻结进这版方案/.test(band)) { say(`STEP_09_FROZEN_ON_ROUND=${round}`); break; }
}
const shortfalls = () => page.getByTestId("rev-v3-gap-shortfall").allInnerTexts()
  .catch(() => []);
say(`STEP_10_GAPS_PRESENT=${await page.getByTestId("rev-v3-travel-gaps").isVisible().catch(() => false)}`);
say(`STEP_10_SHORTFALLS ${JSON.stringify(await shortfalls())}`);
say(`STEP_10_REFUSAL ${await read(page.getByTestId("rev-v3-replan-refusal"), 200)}`);
await shot("replan-walk-10-gaps.png");

const firstReplan = await firstTap("rev-v3-replan");
say(`STEP_11_REPLAN_TAP ${JSON.stringify(firstReplan)}`);
await page.waitForTimeout(1500);
const diff = await page.getByTestId("rev-v3-replan-diff").allInnerTexts().catch(() => []);
say(`STEP_11_DIFF ${JSON.stringify(diff.map((line) => flat(line).slice(0, 120)))}`);
await shot("replan-walk-11-diff.png");

const apply = await firstTap("rev-v3-replan-apply");
say(`STEP_12_APPLY_TAP ${JSON.stringify(apply)}`);
await page.waitForTimeout(9000);
const appliedStatus = await read(page.locator(".rev-v3-departure p[role=status]"), 320);
say(`STEP_12_AFTER_APPLY status=${appliedStatus}`);
await shot("replan-walk-12-after-apply.png");

// The traveller's own refresh: does the new version still tell the truth about its hours?
await page.reload({ waitUntil: "domcontentloaded", timeout: 60000 });
await page.waitForTimeout(14000);
await page.locator('[data-testid="rev-mission-layer-timeline"]').first().click({ timeout: 6000 }).catch(() => undefined);
await page.waitForTimeout(2500);
if (!(await departure.isVisible().catch(() => false))) {
  await page.getByRole("button", { name: /准备出发/ }).first().click({ timeout: 6000 }).catch(() => undefined);
  await page.waitForTimeout(3500);
}
say(`STEP_13_AFTER_RELOAD_DEPARTURE_VISIBLE=${await departure.isVisible().catch(() => false)}`);
say(`STEP_13_AFTER_RELOAD_ROUTE ${await read(routeState, 220)}`);
say(`STEP_13_AFTER_RELOAD_GAPS_PRESENT=${await page.getByTestId("rev-v3-travel-gaps").isVisible().catch(() => false)}`);
say(`STEP_13_WIRE ${JSON.stringify(wire)}`);
say("NOTE the only writes are the traveller's own saves and the two presses named above; nothing was seeded into storage and no endpoint was called by hand");
say("DONE -- the tab is left open on purpose so the next probe reads the same page state");
fs.writeFileSync(LOG, lines.join("\n") + "\n");
