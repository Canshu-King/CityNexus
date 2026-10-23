/**
 * Verify the uncommitted first-screen change by using it the way a traveller would: type one sentence that
 * names a party size and a per-person budget, then read back the two numeric fields -- no API call, no storage
 * write, no pre-filled state.  The tab is discarded afterwards; nothing is submitted.
 *
 * Why a fresh tab is legitimate here and not a fake: the fields under test are pure client state read out of the
 * textarea, so a cold welcome screen IS the scene.  A new tab carries no sessionStorage bearer, which is exactly
 * the condition that shows the form (P0-3 is the separate thing this does NOT prove).
 */
import fs from "node:fs";
import path from "node:path";
import { createRequire } from "node:module";

const require = createRequire("D:/moodle/_cmdr_rescue_v3_1022/frontend/package.json");
const { chromium } = require("playwright");

const OUT = "D:/moodle/_cmdr_rescue_v3_1022/trial/results/20261022_v3_human_chrome";
const stream = fs.openSync(path.join(OUT, process.env.GOAL_LOG || "goal-numbers-1.txt"), "a");
const flat = (v) => String(v ?? "").replace(/\s+/g, " ").trim();
const say = (t) => { fs.writeSync(stream, t + "\n"); process.stdout.write(t + "\n"); };
const WEB = process.env.WALK_BASE || "http://127.0.0.1:14436/revolution";
const CASES = [
  "带爸妈三人轻松逛两天，人均预算 400，少走路。",
  "两个人，人均 650，别太赶。",
  "帮我安排五天，人均 1200。",
  "随便逛逛。",
];

const browser = await chromium.connectOverCDP("http://127.0.0.1:9335", { timeout: 120000 });
const context = browser.contexts()[0] ?? await browser.newContext();
const page = await context.newPage();
await page.setViewportSize({ width: 390, height: 844 });
await page.goto(WEB, { waitUntil: "domcontentloaded", timeout: 40000 });
await page.waitForSelector('[data-testid="rev-trip-goal"]', { timeout: 25000 }).catch((e) => say(`NO_GOAL_FIELD ${flat(e.message).slice(0, 70)}`));

const readFields = () => page.evaluate(() => {
  const flat = (v) => String(v ?? "").replace(/\s+/g, " ").trim();
  const value = (sel) => { const n = document.querySelector(sel); return n ? String(n.value) : "(missing)"; };
  return {
    goal: (document.querySelector('[data-testid="rev-trip-goal"]')?.value || "").slice(0, 60),
    party: value('[data-testid="rev-trip-party-size"]'),
    budget: value('[data-testid="rev-trip-budget"]'),
    partyLabel: (() => { const n = document.querySelector('[data-testid="rev-trip-party-size"]');
      const label = n?.closest("label"); return flat(label?.textContent).slice(0, 40); })(),
    budgetLabel: (() => { const n = document.querySelector('[data-testid="rev-trip-budget"]');
      const label = n?.closest("label"); return flat(label?.textContent).slice(0, 40); })(),
  };
});

say(`START ${JSON.stringify(await readFields())}`);
for (const text of CASES) {
  await page.locator('[data-testid="rev-trip-goal"]').fill(text);
  await page.waitForTimeout(500);
  say(`TYPE "${text.slice(0, 24)}" fields=${JSON.stringify(await readFields())}`);
}
const shot = "goal-numbers-1.png";
await page.screenshot({ path: path.join(OUT, shot), type: "png" }).catch(() => undefined);
say(`SHOT ${shot}`);
await page.close().catch(() => undefined);
say("NOTE 只填了这一枚文本框并回读数显字段；没按「开始规划」、没提交、没建 Journey，新标签页用完即关");
await browser.close().catch(() => undefined);
