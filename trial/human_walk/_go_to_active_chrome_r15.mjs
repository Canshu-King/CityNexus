import { chromium } from "file:///D:/moodle/_cmdr_rescue_v3_1022/frontend/node_modules/playwright/index.mjs";
import fs from "node:fs";

const W = Number(process.env.RW || 390);
const H = Number(process.env.RH || 844);
const TAG = String(W);
const PROFILE = process.env.PROFILE || "D:/moodle/_cmdr_v3_live_1022/_chrome_gozero_1026k";
const BASE = "http://127.0.0.1:14461";
const DIR = "D:/moodle/_cmdr_rescue_v3_1022/trial/results/20261026_gozero";
const OUT = `${DIR}/go-active-${TAG}-go4.txt`;
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
const busy = (body) => /正在研究|回复中|Agent 正在处理/.test(body);
async function waitIdle(minutes, minSeconds) {
  const begin = Date.now();
  const end = begin + minutes * 60 * 1000;
  let sawBusy = false;
  while (Date.now() < end) {
    const body = await bodyText();
    if (busy(body)) sawBusy = true;
    if (!busy(body) && (sawBusy || Date.now() - begin > minSeconds * 1000)) return true;
    await page.waitForTimeout(5000);
  }
  return false;
}
async function openJourney() {
  await press(page.getByRole("button", { name: /我的旅程/ }), "journey-tab", 10000);
  await page.waitForTimeout(2200);
}
async function openChat() {
  await press(page.getByRole("button", { name: "对话", exact: true }), "tab-chat", 10000);
  await page.waitForTimeout(1200);
}

await page.goto(`${BASE}/revolution`, { waitUntil: "domcontentloaded", timeout: 60000 });
await page.waitForTimeout(4000);
await shot(`${TAG}-g4-cold`);
await page.getByRole("textbox", { name: /想怎么玩/ }).first()
  .fill("2026 年 12 月 3 日到 4 日在北京玩两天，两个人，每段步行不超过 1 公里，太远坐地铁");
await page.waitForTimeout(500);
await press(page.getByRole("button", { name: /继续规划/ }), "continue");
await page.waitForTimeout(2500);
await openChat();
await press(page.getByRole("button", { name: /对话设置/ }), "open-settings");
await page.waitForTimeout(700);
for (const label of [/本次允许 AI 处理旅行目标/, /本次允许查询公开地图和地点来源/]) {
  const box = page.getByRole("checkbox", { name: label }).first();
  if (await box.count() && !(await box.isChecked())) await box.check().catch(() => {});
  note(`CONSENT ${label} ${await box.isChecked().catch(() => null)}`);
}
await press(page.getByRole("button", { name: /关闭对话设置/ }), "close-settings");
await page.waitForTimeout(400);
await press(page.getByRole("button", { name: /发送/ }), "send");
note("SENT");

const skip = page.locator('[data-testid="rev-agent-skip-questions"]');
let skipped = false;
let retries = 0;
const recover = async (tag) => {
  const body = await bodyText();
  if (!/这次有一部分还没完成|这一轮没有完成|请求失败|被限流|超时/.test(body)) return false;
  if (retries >= 2) return false;
  if (!(await press(page.getByRole("button", { name: /按讨论的方向开始研究/ }), `recover-${tag}`, 15000))) return false;
  retries += 1; note(`RECOVERY ${retries}`); await page.waitForTimeout(4000);
  return true;
};
const skipEnd = Date.now() + 6 * 60 * 1000;
while (Date.now() < skipEnd) {
  if (await visible(skip) && await press(skip, "skip-questions", 15000)) { skipped = true; note(`SKIP t=${elapsed()}`); break; }
  if (await recover("ask")) continue;
  await page.waitForTimeout(3000);
}
note(`SKIPPED ${skipped}`);

let draftSeen = false;
const researchEnd = Date.now() + 20 * 60 * 1000;
while (Date.now() < researchEnd) {
  const body = await bodyText();
  if (/已整理\s*\d+\s*天/.test(body) || /行程草案/.test(body)) { draftSeen = true; note(`DRAFT t=${elapsed()}`); break; }
  if (await recover("research")) continue;
  if (skipped && !busy(body)) { note(`IDLE_NO_DRAFT t=${elapsed()}`); break; }
  await page.waitForTimeout(6000);
}
note(`DRAFT_SEEN ${draftSeen}`);
await shot(`${TAG}-g4-after-research`);

// The Agent's own draft often carries meal slots with no place ("晚餐现场挑"), which the formal
// departure gate refuses; the traveller's sentence is the one the product offers on the card.
await openChat();
const composer = page.locator("#rev-mission-chat-input");
if (await visible(composer)) {
  // "已整理 N 天" shows up while the research POST is still in flight; the dock stays disabled
  // until that round returns, and filling a disabled textarea aborts the whole walk.
  for (let k = 0; k < 150 && !(await composer.isEnabled().catch(() => false)); k += 1) await page.waitForTimeout(4000);
  note(`COMPOSER_ENABLED ${await composer.isEnabled().catch(() => false)} t=${elapsed()}`);
  await composer.fill("没有具体地点的那两处用餐安排，请用你查到的来源换成附近真实的餐馆，其余日期和安排都别动。");
  await press(page.getByRole("button", { name: /^发送/ }), "send-fix", 15000);
  note(`FIX_SENT t=${elapsed()}`);
  const idle = await waitIdle(10, 45);
  note(`FIX_IDLE ${idle} t=${elapsed()}`);
  await shot(`${TAG}-g4-after-fix`);
}

await openJourney();
const confirmBox = page.getByRole("checkbox", { name: /按以上时间准备方案/ }).first();
const saveButton = page.getByRole("button", { name: /保存为正式候选方案/ }).first();
const acceptPrice = page.locator('[data-testid="rev-v3-accept-price"]');
const freeze = page.locator('[data-testid="rev-v3-freeze-routes"]');
const select = page.locator('[data-testid="rev-plan-select"]');
const startButton = page.locator('[data-testid="rev-plan-start"]');
const refreshPlan = page.getByRole("button", { name: /刷新方案/ });

let startedJourney = false;
for (let round = 1; round <= 3 && !startedJourney; round += 1) {
  for (let i = 0; i < 24; i += 1) {
    if (!(await confirmBox.count())) await openJourney();
    if (await visible(confirmBox) && !(await confirmBox.isChecked())) await confirmBox.check().catch(() => {});
    if (await visible(saveButton) && /保存为正式候选方案/.test(await saveButton.innerText().catch(() => ""))) {
      if (await press(saveButton, `save-${round}-${i}`, 30000)) { await page.waitForTimeout(6000); continue; }
    }
    if (await visible(acceptPrice) && await press(acceptPrice, `price-${round}-${i}`, 15000)) {
      await page.waitForTimeout(4000);
      if (await visible(refreshPlan)) { await press(refreshPlan, `refresh-after-price-${round}`, 10000); await page.waitForTimeout(4000); }
      continue;
    }
    if (await visible(freeze)) {
      const label = (await freeze.innerText().catch(() => "")) || "";
      if (!/重新核实/.test(label) && await press(freeze, `freeze-${round}-${i}`, 120000)) {
        await page.waitForTimeout(6000);
        if (await visible(refreshPlan)) { await press(refreshPlan, `refresh-after-freeze-${round}`, 10000); await page.waitForTimeout(4000); }
        continue;
      }
    }
    if (await visible(refreshPlan) && i === 0) { await press(refreshPlan, `refresh-start-${round}`, 10000); await page.waitForTimeout(3500); }
    if (await visible(select) && await select.isEnabled().catch(() => false)) {
      await shot(`${TAG}-g4-plans-${round}`);
      if (await press(select, `select-${round}`, 30000)) {
        await page.waitForTimeout(5000);
        const refusal = await page.locator(".rev-plan-message, [role='alert']").allInnerTexts().catch(() => []);
        note(`SELECT_REFUSAL ${JSON.stringify(refusal.slice(0, 2))}`);
        await shot(`${TAG}-g4-selected-${round}`);
        if (await visible(startButton) && await press(startButton, "start-journey", 30000)) {
          startedJourney = true;
          await page.waitForTimeout(10000);
          await shot(`${TAG}-g4-started`);
          break;
        }
        if (await visible(refreshPlan)) { await press(refreshPlan, `refresh-after-select-${round}`, 10000); await page.waitForTimeout(4000); }
        const replan = page.locator('[data-testid="rev-plan-replan"]');
        if (await visible(replan)) {
          await press(replan, `replan-${round}`, 15000);
          await page.waitForTimeout(2500);
          const apply = page.locator('[data-testid="rev-v3-replan-apply"]');
          if (await visible(apply) && await press(apply, `replan-apply-${round}`, 30000)) {
            note(`REPLAN_APPLIED ${round}`);
            await waitIdle(10, 30);
            await page.waitForTimeout(3000);
            await openJourney();
          }
        }
        break;
      }
    }
    const gate = await page.locator('[data-testid="rev-v3-server-departure"]').allInnerTexts().catch(() => []);
    const gaps = await page.locator(".rev-plan-gap").allInnerTexts().catch(() => []);
    const alerts = await page.locator(".rev-plan-message, [role='alert']").allInnerTexts().catch(() => []);
    note(`LOOP ${round}/${i} GATE ${JSON.stringify(gate.slice(0, 1))} BLOCK ${JSON.stringify(gaps.slice(0, 2))} ALERT ${JSON.stringify(alerts.slice(0, 1))}`);
    await page.waitForTimeout(5000);
  }
}

let last = "";
const end = Date.now() + 90000;
while (Date.now() < end) {
  const now = await page.evaluate(() => {
    const txt = document.body.innerText || "";
    return { inUse: /正在使用|旅程已开始/.test(txt), next: (txt.match(/下一站[^\n]{0,60}/) || [null])[0] };
  });
  const mark = JSON.stringify(now);
  if (mark !== last) { note(`STATE t=${elapsed()} ${mark}`); last = mark; }
  if (now.inUse) break;
  await page.waitForTimeout(5000);
}
await shot(`${TAG}-g4-final`);
note(`FINAL_BODY ${JSON.stringify((await bodyText()).slice(0, 2200))}`);
note(`ERRORS ${JSON.stringify(errors.slice(0, 3))}`);
await ctx.close();
