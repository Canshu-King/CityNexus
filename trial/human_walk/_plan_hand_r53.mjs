import { chromium } from "file:///D:/moodle/_cmdr_rescue_v3_1022/frontend/node_modules/playwright/index.mjs";
import fs from "node:fs";

const W = Number(process.env.RW || 390);
const H = Number(process.env.RH || 844);
const TAG = String(W);
const PROFILE = process.env.PROFILE || "D:/moodle/_cmdr_v3_live_1022/_chrome_gozero_r52";
const BASE = "http://127.0.0.1:14461";
const DIR = "D:/moodle/_cmdr_rescue_v3_1022/trial/results/20261026_gozero";
const OUT = `${DIR}/plan-open-hand-${TAG}-r53.txt`;
const NL = String.fromCharCode(10);
const lines = [];
const note = (value) => { lines.push(value); fs.writeFileSync(OUT, lines.join(NL) + NL, "utf8"); };
const started = Date.now();
const elapsed = () => ((Date.now() - started) / 1000).toFixed(1);

const ctx = await chromium.launchPersistentContext(PROFILE, {
  channel: "chrome", headless: false, viewport: { width: W, height: H }, deviceScaleFactor: 1,
});
const page = ctx.pages()[0] ?? await ctx.newPage();
const errors = [];
page.on("pageerror", (error) => errors.push(String(error).slice(0, 160)));

async function shot(name) {
  await page.screenshot({ path: `${DIR}/${TAG}-r53-${name}.png`, fullPage: false }).catch(() => {});
  note(`SHOT ${name} t=${elapsed()}`);
}
async function visible(locator) { try { return await locator.first().isVisible(); } catch { return false; } }
async function press(locator, label, timeout = 8000) {
  const target = locator.first();
  try { await target.waitFor({ state: "visible", timeout }); } catch { note(`MISS ${label}`); return false; }
  await target.evaluate((node) => node.scrollIntoView({ block: "center" })).catch(() => {});
  await page.waitForTimeout(300);
  const ok = await target.evaluate((node) => {
    const box = node.getBoundingClientRect();
    if (box.width === 0 || box.height === 0) return false;
    const top = document.elementFromPoint(box.left + box.width / 2, box.top + box.height / 2);
    return Boolean(top) && (node === top || node.contains(top)) && !node.disabled;
  });
  note(`HIT ${label} ${ok} t=${elapsed()}`);
  if (!ok) return false;
  await target.click({ timeout: 15000 }).catch(() => {});
  await page.waitForTimeout(700);
  return true;
}
const bodyText = () => page.evaluate(() => document.body.innerText || "").catch(() => "");

// Arm K reads the plan screen as it now stands in the gozero canary: a DRAFT journey whose one
// candidate is refused by the server's own authority gate (backend/app/services.py:742).  Arm J proved
// the reason reaches the screen; what it could not prove is whether the traveller has anything to press.
await page.goto(`${BASE}/revolution`, { waitUntil: "domcontentloaded", timeout: 60000 });
await page.waitForTimeout(5000);
await shot("cold");
note(`COLD_HAS_JOURNEY_TAB ${await page.getByRole("button", { name: /我的旅程/ }).count()} t=${elapsed()}`);

if (!(await press(page.getByRole("button", { name: /我的旅程/ }), "journey-tab", 12000))) {
  note("NO_JOURNEY_TAB -- this profile no longer carries the traveller that owns the canary journey");
  await ctx.close();
  process.exit(0);
}
await page.waitForTimeout(2500);
note(`JOURNEY_LIST ${JSON.stringify((await bodyText()).replace(/\s+/g, " ").slice(0, 900))}`);
const opened = await press(page.getByRole("button", { name: /北京/ }).or(page.getByText(/北京 · 2日行程/)), "open-journey", 12000);
note(`OPEN_JOURNEY ${opened} t=${elapsed()}`);
await page.waitForTimeout(4000);

// Find the workbench: it lives behind one of the layer tabs, so each is tried until it renders.
for (const layer of [/^日程$/, /^对话$/, /^地图$/]) {
  if (await page.locator('[data-testid="rev-plan-workbench"]').count()) break;
  const tab = page.getByRole("button", { name: layer });
  if (await visible(tab)) {
    await press(tab, `layer-${String(layer)}`, 10000);
    await page.waitForTimeout(3000);
  }
  note(`LAYER_PROBE ${String(layer)} workbench=${await page.locator('[data-testid="rev-plan-workbench"]').count()} t=${elapsed()}`);
}

const wb = page.locator('[data-testid="rev-plan-workbench"]');
note(`WORKBENCH_COUNT ${await wb.count()} t=${elapsed()}`);
if (!(await wb.count())) {
  note("NO_WORKBENCH_ON_SCREEN " + JSON.stringify((await bodyText()).replace(/\s+/g, " ").slice(0, 600)));
  await shot("no-workbench");
  await ctx.close();
  process.exit(0);
}

// Every gap paragraph, not the first two: arm J cut its own reading short and lost the blocker sentence.
const gaps = await page.locator(".rev-plan-gap").allInnerTexts().catch(() => []);
note(`GAPS_ALL ${JSON.stringify(gaps)}`);
note(`SELECT_KEY ${await page.locator('[data-testid="rev-plan-select"]').count()} t=${elapsed()}`);
const hand = page.locator('[data-testid="rev-plan-open-place-explore"]');
note(`OPEN_PLACE_HAND ${await hand.count()} t=${elapsed()}`);
await shot("plan-blocked");
if (await hand.count()) {
  const before = (await bodyText()).length;
  const pressed = await press(hand, "open-place-hand", 12000);
  await page.waitForTimeout(3500);
  const after = await bodyText();
  note(`HAND_PRESSED ${pressed} t=${elapsed()}`);
  note(`AFTER_HAND_HAS_EXPLORE ${/探索|查找地点|候选地点/.test(after)} body_delta=${after.length - before}`);
  note(`AFTER_HAND_HEAD ${JSON.stringify(after.replace(/\s+/g, " ").slice(0, 320))}`);
  await shot("after-hand");
}
note(`ERRORS ${JSON.stringify(errors.slice(0, 3))}`);
await ctx.close();
