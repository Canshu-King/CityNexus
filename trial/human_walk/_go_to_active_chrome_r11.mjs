import { chromium } from "file:///D:/moodle/_cmdr_rescue_v3_1022/frontend/node_modules/playwright/index.mjs";
import fs from "node:fs";

const W = Number(process.env.RW || 390);
const H = Number(process.env.RH || 844);
const TAG = String(W);
const PROFILE = process.env.PROFILE || "D:/moodle/_cmdr_v3_live_1022/_chrome_gozero_1026f";
const BASE = "http://127.0.0.1:14461";
const DIR = "D:/moodle/_cmdr_rescue_v3_1022/trial/results/20261026_gozero";
const OUT = `${DIR}/go-active-${TAG}-flow.txt`;
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
  if (/plans/.test(url) && resp.status() < 300) {
    const body = await resp.json().catch(() => null);
    if (Array.isArray(body)) note(`PLANS ${JSON.stringify(body.map((p) => ({ id: p.id, version_no: p.version_no, status: p.status, selectable: p.selectable, stale: p.stale, current: p.is_current })))}`);
  }
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

await page.goto(`${BASE}/revolution`, { waitUntil: "domcontentloaded", timeout: 60000 });
await page.waitForTimeout(4000);
await shot(`${TAG}-flow-cold`);
await page.getByRole("textbox", { name: /想怎么玩/ }).first()
  .fill("2026 年 12 月 3 日到 4 日在北京玩两天，两个人，每段步行不超过 1 公里，太远坐地铁");
await page.waitForTimeout(500);
await press(page.getByRole("button", { name: /继续规划/ }), "continue");
await page.waitForTimeout(2500);
await press(page.getByRole("button", { name: "对话", exact: true }), "tab-chat");
await page.waitForTimeout(1200);
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
const choicesSection = page.locator('section[aria-label="Agent 请你选择"]').first();
let skipped = false;
const skipDeadline = Date.now() + 6 * 60 * 1000;
while (Date.now() < skipDeadline) {
  if (await visible(skip)) {
    await shot(`${TAG}-flow-pending-question`);
    const question = await bodyText();
    const asked = (question.match(/（[^）]{0,80}）/) || [""])[0];
    note(`QUESTION_HINT ${JSON.stringify(asked)}`);
    if (await press(skip, "skip-questions", 15000)) { skipped = true; note(`SKIP_PRESSED t=${elapsed()}`); break; }
  }
  await page.waitForTimeout(3000);
}
note(`SKIPPED ${skipped}`);

let draftSeen = false;
const researchDeadline = Date.now() + 16 * 60 * 1000;
while (Date.now() < researchDeadline) {
  const body = await bodyText();
  if (/已整理\s*\d+\s*天/.test(body) || /版本\s*0\s*→\s*[1-9]/.test(body) || /行程草案/.test(body)) {
    draftSeen = true; note(`DRAFT_SEEN t=${elapsed()}`); break;
  }
  if (skipped && !/正在研究|回复中|Agent 正在处理/.test(body)) {
    note(`IDLE_WITHOUT_DRAFT_TEXT t=${elapsed()}`);
    break;
  }
  await page.waitForTimeout(6000);
}
await shot(`${TAG}-flow-after-research`);
note(`DRAFT_SEEN ${draftSeen}`);

// The draft card lives on the journey layer, not in the assistant conversation.
await press(page.getByRole("button", { name: /我的旅程/ }), "journey-tab", 10000);
await page.waitForTimeout(3500);
await shot(`${TAG}-flow-journey`);
const confirmBox = page.getByRole("checkbox", { name: /按以上时间准备方案/ }).first();
let cardSeen = false;
for (let i = 0; i < 20; i += 1) {
  if ((await confirmBox.count()) > 0 && await confirmBox.isVisible().catch(() => false)) { cardSeen = true; break; }
  await page.waitForTimeout(3000);
}
note(`CARD_SEEN ${cardSeen} t=${elapsed()}`);
await shot(`${TAG}-flow-card`);

if (cardSeen) {
  await confirmBox.scrollIntoViewIfNeeded().catch(() => {});
  if (!(await confirmBox.isChecked())) await confirmBox.check().catch(() => {});
  note(`CONFIRM_CHECKED ${await confirmBox.isChecked().catch(() => null)}`);
  await press(page.getByRole("button", { name: /保存为正式候选方案/ }), "save-candidate", 60000);
  await page.waitForTimeout(5000);
  await shot(`${TAG}-flow-saved`);
  const gen = page.locator('[data-testid="rev-v3-generate-plans"]');
  if (await visible(gen)) {
    await press(gen, "generate-plans", 60000);
    await page.waitForTimeout(8000);
    await shot(`${TAG}-flow-generated`);
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
      await shot(`${TAG}-flow-selected-${step}`);
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
    const body = await bodyText();
    note(`GAP step=${step} ${JSON.stringify(gaps.slice(0, 2))} GATE ${JSON.stringify(gate.slice(0, 1))} HEAD ${JSON.stringify((body.match(/旅行研究 · [^\n]+/) || [null])[0])}`);
    await shot(`${TAG}-flow-gap-${step}`);
    await page.waitForTimeout(6000);
  }
  const startButton = page.locator('[data-testid="rev-plan-start"]');
  if (await visible(startButton)) {
    await press(startButton, "start-journey", 30000);
    await page.waitForTimeout(10000);
    await shot(`${TAG}-flow-started`);
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
await shot(`${TAG}-flow-final`);
const body = await bodyText();
note(`FINAL_BODY ${JSON.stringify(body.slice(0, 1600))}`);
note(`ERRORS ${JSON.stringify(errors.slice(0, 3))}`);
await ctx.close();
