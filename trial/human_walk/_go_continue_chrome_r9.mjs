import { chromium } from "file:///D:/moodle/_cmdr_rescue_v3_1022/frontend/node_modules/playwright/index.mjs";
import fs from "node:fs";

const W = Number(process.env.RW || 390);
const H = Number(process.env.RH || 844);
const TAG = String(W) + "-cont";
const PROFILE = process.env.PROFILE || "D:/moodle/_cmdr_v3_live_1022/_chrome_gozero_1026";
const BASE = "http://127.0.0.1:14461";
const DIR = "D:/moodle/_cmdr_rescue_v3_1022/trial/results/20261026_gozero";
const OUT = `${DIR}/go-active-${TAG}-r9.txt`;
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
page.on("response", async (resp) => {
  const url = resp.url();
  const method = resp.request().method();
  if (!url.includes("/api/v1/") || (method !== "POST" && method !== "PUT")) return;
  if (!/goal-tasks|plans|journeys|departure/.test(url)) return;
  note(`HTTP ${method} ${resp.status()} ${url.replace(/^http:\/\/[^/]+/, "")}`);
});

async function shot(name) {
  await page.screenshot({ path: `${DIR}/${name}.png`, fullPage: false }).catch(() => {});
  note(`SHOT ${name} t=${elapsed()}`);
}
async function visible(locator) { try { return await locator.first().isVisible(); } catch { return false; } }
async function press(locator, label, timeout = 8000) {
  const target = locator.first();
  try { await target.waitFor({ state: "visible", timeout }); } catch { note(`MISS ${label}`); return false; }
  await target.scrollIntoViewIfNeeded().catch(() => {});
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

await page.goto(`${BASE}/revolution`, { waitUntil: "domcontentloaded", timeout: 60000 });
await page.waitForTimeout(6000);
note(`RESTORED_JOURNEY ${await page.evaluate(() => localStorage.getItem("citynexus.v8.journey_id")).catch(() => null)}`);
const head = await page.evaluate(() => (document.body.innerText || "").slice(0, 500)).catch(() => "");
note(`OPEN_BODY ${JSON.stringify(head)}`);
await shot(`${TAG}-open`);

if (await visible(page.getByRole("textbox", { name: /想怎么玩/ }))) {
  const journeyTab = page.getByRole("button", { name: /我的旅程/ });
  if (await journeyTab.count()) { await press(journeyTab, "journey-tab", 8000); await page.waitForTimeout(2500); }
  await shot(`${TAG}-journeys`);
  const body = await page.evaluate(() => (document.body.innerText || "").slice(0, 900)).catch(() => "");
  note(`JOURNEYS_BODY ${JSON.stringify(body)}`);
  const card = page.getByText(/北京 · 2日行程|北京 · 2 日行程/).first();
  if (await card.count()) { await press(card, "journey-card", 8000); await page.waitForTimeout(3000); await shot(`${TAG}-opened`); }
}

if (await visible(page.getByRole("button", { name: "对话", exact: true }))) {
  await press(page.getByRole("button", { name: "对话", exact: true }), "tab-chat");
  await page.waitForTimeout(1200);
}

const confirmBox = page.getByRole("checkbox", { name: /按以上时间准备方案/ }).first();
const idleDeadline = Date.now() + 15 * 60 * 1000;
let ready = false;
while (Date.now() < idleDeadline) {
  if (await visible(confirmBox)) { ready = true; break; }
  const body = await page.evaluate(() => document.body.innerText || "").catch(() => "");
  if (/正在研究|回复中|Agent 正在处理/.test(body) === false && /按讨论的方向开始研究/.test(body)) {
    // The task is idle and the draft is not rendered here; the departure card lives on the journey card.
    note(`IDLE_NO_DRAFT t=${elapsed()}`);
    break;
  }
  await page.waitForTimeout(6000);
}
note(`CONFIRM_VISIBLE ${ready} t=${elapsed()}`);
await shot(`${TAG}-ready`);

if (ready) {
  await confirmBox.scrollIntoViewIfNeeded().catch(() => {});
  await page.waitForTimeout(400);
  if (!(await confirmBox.isChecked())) await confirmBox.check().catch(() => {});
  note(`CONFIRM_CHECKED ${await confirmBox.isChecked().catch(() => null)}`);
  await press(page.getByRole("button", { name: /保存为正式候选方案/ }), "save-candidate", 60000);
  await page.waitForTimeout(5000);
  await shot(`${TAG}-saved`);
  const gen = page.locator('[data-testid="rev-v3-generate-plans"]');
  if (await visible(gen)) {
    await press(gen, "generate-plans", 60000);
    await page.waitForTimeout(8000);
    await shot(`${TAG}-generated`);
    const genMessage = await page.locator(".rev-v3-departure p[role='status']").allInnerTexts().catch(() => []);
    note(`GEN_MESSAGE ${JSON.stringify(genMessage.slice(-2))}`);
  } else {
    note("NO_GENERATE_BUTTON");
  }
  for (let step = 1; step <= 12; step += 1) {
    const start = page.locator('[data-testid="rev-plan-start"]');
    const select = page.locator('[data-testid="rev-plan-select"]');
    const freeze = page.locator('[data-testid="rev-v3-freeze-routes"]');
    if (await visible(start)) { note(`START_READY step=${step}`); break; }
    if (await visible(select)) {
      await press(select, `select-${step}`, 30000);
      await page.waitForTimeout(7000);
      await shot(`${TAG}-selected-${step}`);
      continue;
    }
    if (await visible(freeze)) {
      await press(freeze, `freeze-${step}`, 120000);
      await page.waitForTimeout(8000);
      const routeState = await page.locator('[data-testid="rev-v3-route-state"]').allInnerTexts().catch(() => []);
      note(`ROUTE_STATE ${JSON.stringify(routeState.slice(-1))}`);
      continue;
    }
    const gaps = await page.locator(".rev-plan-gap").allInnerTexts().catch(() => []);
    const gate = await page.locator('[data-testid="rev-v3-server-departure"]').allInnerTexts().catch(() => []);
    note(`GAP step=${step} ${JSON.stringify(gaps.slice(0, 2))} GATE ${JSON.stringify(gate.slice(0, 1))}`);
    await shot(`${TAG}-gap-${step}`);
    await page.waitForTimeout(6000);
  }
  const startButton = page.locator('[data-testid="rev-plan-start"]');
  if (await visible(startButton)) {
    await press(startButton, "start-journey", 30000);
    await page.waitForTimeout(10000);
    await shot(`${TAG}-started`);
  } else {
    note("NO_START_BUTTON");
  }
}

let last = "";
const deadline = Date.now() + 120000;
while (Date.now() < deadline) {
  const now = await page.evaluate(() => {
    const txt = document.body.innerText || "";
    return {
      inUse: /正在使用|旅程已开始/.test(txt),
      nextStop: (txt.match(/下一站[^\n]{0,60}/) || [null])[0],
      headline: (txt.match(/旅行研究 · [^\n]+/) || [null])[0],
    };
  });
  const mark = JSON.stringify(now);
  if (mark !== last) { note(`STATE t=${elapsed()} ${mark}`); last = mark; }
  if (now.inUse) break;
  await page.waitForTimeout(5000);
}
await shot(`${TAG}-final`);
const journeyTab = page.getByRole("button", { name: /我的旅程|今日行程/ });
if (await journeyTab.count()) {
  await press(journeyTab, "journey-tab", 8000);
  await page.waitForTimeout(3500);
  await shot(`${TAG}-journey`);
  const body = await page.evaluate(() => (document.body.innerText || "").slice(0, 1500)).catch(() => "");
  note(`JOURNEY_BODY ${JSON.stringify(body)}`);
}
note(`ERRORS ${JSON.stringify(errors.slice(0, 3))}`);
await ctx.close();
