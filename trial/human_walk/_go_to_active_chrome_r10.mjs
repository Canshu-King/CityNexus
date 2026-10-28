import { chromium } from "file:///D:/moodle/_cmdr_rescue_v3_1022/frontend/node_modules/playwright/index.mjs";
import fs from "node:fs";

const W = Number(process.env.RW || 390);
const H = Number(process.env.RH || 844);
const TAG = String(W);
const PROFILE = process.env.PROFILE || "D:/moodle/_cmdr_v3_live_1022/_chrome_gozero_1026c";
const BASE = "http://127.0.0.1:14461";
const DIR = "D:/moodle/_cmdr_rescue_v3_1022/trial/results/20261026_gozero";
const OUT = `${DIR}/go-active-${TAG}-full-r10.txt`;
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
    else if (body && typeof body === "object") note(`PLAN_ONE ${JSON.stringify({ id: body.id, version_no: body.version_no, status: body.status, selectable: body.selectable, stale: body.stale })}`);
  }
});

async function shot(name) {
  await page.screenshot({ path: `${DIR}/${name}.png`, fullPage: false }).catch(() => {});
  note(`SHOT ${name} t=${elapsed()}`);
}

async function visible(locator) {
  try { return await locator.first().isVisible(); } catch { return false; }
}

async function press(locator, label, timeout = 8000) {
  const target = locator.first();
  try { await target.waitFor({ state: "visible", timeout }); } catch { note(`MISS ${label}`); return false; }
  // scrollIntoViewIfNeeded() leaves an element that is only just inside the viewport alone, and the
  // fixed composer then sits on top of it: the hit test said false on 70+ presses. Centre it first.
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

const PREFER = ["不去长城", "市区", "胡同", "慢走", "慢游", "少走", "文化", "均衡", "颐和园"];

async function readChoices() {
  const section = page.locator('section[aria-label="Agent 请你选择"]').first();
  if (!(await section.count())) return null;
  if (!(await section.isVisible().catch(() => false))) return null;
  const labels = await section.locator("button").allInnerTexts().catch(() => []);
  if (!labels.length) return null;
  return labels.map((text) => text.split(String.fromCharCode(10))[0]);
}

await page.goto(`${BASE}/revolution`, { waitUntil: "domcontentloaded", timeout: 60000 });
await page.waitForTimeout(4000);
await shot(`${TAG}-cold`);
const composer = page.getByRole("textbox", { name: /想怎么玩/ }).first();
if (await composer.count()) {
  await composer.fill("2026 年 12 月 3 日到 4 日在北京玩两天，两个人，每段步行不超过 1 公里，太远坐地铁");
  await page.waitForTimeout(500);
  await press(page.getByRole("button", { name: /继续规划/ }), "continue");
  await page.waitForTimeout(2500);
}
note(`JOURNEY ${await page.evaluate(() => localStorage.getItem("citynexus.v8.journey_id")).catch(() => null)}`);
if (await visible(page.getByRole("button", { name: "对话", exact: true }))) {
  await press(page.getByRole("button", { name: "对话", exact: true }), "tab-chat");
  await page.waitForTimeout(1200);
}
const settings = page.getByRole("button", { name: /对话设置/ });
if (await visible(settings)) {
  await press(settings, "open-settings");
  await page.waitForTimeout(700);
}
for (const label of [/本次允许 AI 处理旅行目标/, /本次允许查询公开地图和地点来源/]) {
  const box = page.getByRole("checkbox", { name: label }).first();
  if (await box.count() && !(await box.isChecked())) await box.check().catch(() => {});
  note(`CONSENT ${label} ${await box.isChecked().catch(() => null)}`);
}
const closeSettings = page.getByRole("button", { name: /关闭对话设置/ });
if (await visible(closeSettings)) {
  await press(closeSettings, "close-settings");
  await page.waitForTimeout(400);
}
const send = page.getByRole("button", { name: /发送/ });
if (await visible(send)) {
  await press(send, "send");
  note("SENT");
}

const confirmBox = page.getByRole("checkbox", { name: /按以上时间准备方案/ }).first();
const skip = page.locator('[data-testid="rev-agent-skip-questions"]');
let answered = 0;
let researchPresses = 0;
let draftReady = false;
for (let cycle = 1; cycle <= 130; cycle += 1) {
  // A saved draft renders the confirm checkbox even while a research turn is still running;
  // pressing "开始研究" again then starts a second paid turn (measured on r8: 18 turns, 16 tools).
  // The draft is the door here, so wait for it to become enabled instead of asking for more work.
  if ((await confirmBox.count()) > 0) {
    if (await confirmBox.isEnabled().catch(() => false)) {
      note(`DRAFT_READY cycle=${cycle} t=${elapsed()}`);
      draftReady = true;
      break;
    }
    note(`DRAFT_PENDING cycle=${cycle} t=${elapsed()}`);
    if (cycle % 5 === 0) await shot(`${TAG}-draft-pending-${cycle}`);
    await page.waitForTimeout(6000);
    continue;
  }
  const choices = await readChoices();
  if (choices) {
    answered += 1;
    const question = await page.locator('section[aria-label="Agent 请你选择"] h3').first().innerText().catch(() => "");
    if (answered >= 1 && await visible(skip)) {
      await shot(`${TAG}-pending-question`);
      note(`QUESTION ${JSON.stringify(question.slice(0, 160))}`);
      await press(skip, "skip-questions", 15000);
      note(`SKIP_PRESSED cycle=${cycle} t=${elapsed()}`);
      await page.waitForTimeout(3000);
      continue;
    }
    const before = JSON.stringify(choices);
    let index = choices.findIndex((text) => PREFER.some((word) => text.includes(word)));
    if (index < 0) index = 0;
    note(`ROUND cycle=${cycle} labels=${before} pick=${JSON.stringify(choices[index])}`);
    const buttons = page.locator('section[aria-label="Agent 请你选择"]').first().locator("button");
    await press(buttons.nth(index), `answer-cycle${cycle}`);
    const end = Date.now() + 240000;
    while (Date.now() < end) {
      await page.waitForTimeout(2500);
      const next = await readChoices();
      if (!next || JSON.stringify(next) !== before) break;
    }
    await shot(`${TAG}-cycle${cycle}-after`);
    continue;
  }
  const research = page.getByRole("button", { name: /按讨论的方向开始研究/ });
  // A saved draft makes the research button pointless and expensive: pressing it again bought a
  // second and third paid run (03:31:56 timeout, 03:35:02) while the draft card was still mounting.
  const bodyNow = await page.evaluate(() => document.body.innerText || "").catch(() => "");
  const draftSaved = /已整理\s*\d+\s*天/.test(bodyNow) || /版本\s*\d+\s*→\s*[1-9]/.test(bodyNow);
  if (!draftSaved && researchPresses < 1 && await visible(research) && await press(research, `research-${cycle}`, 15000)) {
    researchPresses += 1;
    note(`RESEARCH_PRESSED cycle=${cycle} t=${elapsed()}`);
    await page.waitForTimeout(4000);
    continue;
  }
  const body = await page.evaluate(() => document.body.innerText || "").catch(() => "");
  note(`WAIT cycle=${cycle} t=${elapsed()} headline=${JSON.stringify((body.match(/旅行研究 · [^\n]+/) || [null])[0])}`);
  if (cycle % 4 === 0) await shot(`${TAG}-wait-${cycle}`);
  await page.waitForTimeout(6000);
}

if (!draftReady) {
  const body = await page.evaluate(() => (document.body.innerText || "").slice(0, 1200)).catch(() => "");
  note(`NO_DRAFT_BODY ${JSON.stringify(body)}`);
  await shot(`${TAG}-no-draft`);
} else {
  await confirmBox.scrollIntoViewIfNeeded().catch(() => {});
  await page.waitForTimeout(400);
  if (!(await confirmBox.isChecked())) await confirmBox.check().catch(() => {});
  note(`CONFIRM_CHECKED ${await confirmBox.isChecked().catch(() => null)}`);
  await shot(`${TAG}-confirmed`);
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
      active: /正在使用|旅程已开始|可以确认出发|已选用/.test(txt),
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
  const body = await page.evaluate(() => (document.body.innerText || "").slice(0, 1400)).catch(() => "");
  note(`JOURNEY_BODY ${JSON.stringify(body)}`);
}
note(`FINAL_JOURNEY ${await page.evaluate(() => localStorage.getItem("citynexus.v8.journey_id")).catch(() => null)}`);
note(`ERRORS ${JSON.stringify(errors.slice(0, 3))}`);
await ctx.close();
