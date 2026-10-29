import { chromium } from "file:///D:/moodle/_cmdr_rescue_v3_1022/frontend/node_modules/playwright/index.mjs";
import fs from "node:fs";

const W = Number(process.env.RW || 390);
const H = Number(process.env.RH || 844);
const TAG = String(W);
const BASE = "http://127.0.0.1:14461";
const DIR = "D:/moodle/_cmdr_rescue_v3_1022/trial/results/20261026_gozero";
const OUT = `${DIR}/go-active-${TAG}.txt`;
const NL = String.fromCharCode(10);
const lines = [];
const note = (value) => { lines.push(value); fs.writeFileSync(OUT, lines.join(NL) + NL, "utf8"); };
const started = Date.now();
const elapsed = () => ((Date.now() - started) / 1000).toFixed(1);

const browser = await chromium.launch({ channel: "chrome", headless: false });
const ctx = await browser.newContext({ viewport: { width: W, height: H }, deviceScaleFactor: 1 });
const page = await ctx.newPage();
const errors = [];
page.on("pageerror", (error) => errors.push(String(error).slice(0, 140)));
page.on("response", (resp) => {
  const url = resp.url();
  const method = resp.request().method();
  if (!url.includes("/api/v1/") || (method !== "POST" && method !== "PUT")) return;
  if (!/goal-tasks|plans|journeys/.test(url)) return;
  note(`HTTP ${method} ${resp.status()} ${url.replace(/^http:\/\/[^/]+/, "")}`);
});

async function shot(name) {
  await page.screenshot({ path: `${DIR}/${name}.png`, fullPage: false }).catch(() => {});
  note(`SHOT ${name} t=${elapsed()}`);
}

async function press(locator, label, timeout = 8000) {
  try { await locator.waitFor({ state: "visible", timeout }); } catch { note(`MISS ${label}`); return false; }
  await locator.scrollIntoViewIfNeeded().catch(() => {});
  await page.waitForTimeout(300);
  const ok = await locator.evaluate((node) => {
    const box = node.getBoundingClientRect();
    if (box.width === 0 || box.height === 0) return false;
    const top = document.elementFromPoint(box.left + box.width / 2, box.top + box.height / 2);
    return Boolean(top) && (node === top || node.contains(top)) && !node.disabled;
  });
  note(`HIT ${label} ${ok} t=${elapsed()}`);
  if (!ok) return false;
  await locator.click({ timeout: 10000 }).catch(() => {});
  await page.waitForTimeout(700);
  return true;
}

const PREFER = ["不去长城", "市区", "胡同", "慢走", "慢游", "少走", "文化", "均衡", "颐和园"];

async function readChoices() {
  const section = page.locator('section[aria-label="Agent 请你选择"]').first();
  if (!(await section.count())) return null;
  if (!(await section.isVisible().catch(() => false))) return null;
  const buttons = section.locator("button");
  const labels = await buttons.allInnerTexts().catch(() => []);
  if (!labels.length) return null;
  return labels.map((text) => text.split(String.fromCharCode(10))[0]);
}

async function waitChoices(timeout) {
  const end = Date.now() + timeout;
  for (;;) {
    const labels = await readChoices();
    if (labels) return labels;
    if (Date.now() > end) return null;
    await page.waitForTimeout(2500);
  }
}

await page.goto(`${BASE}/revolution`, { waitUntil: "domcontentloaded", timeout: 60000 });
await page.waitForTimeout(4000);
await page.getByRole("textbox", { name: /想怎么玩/ }).first()
  .fill("2026 年 12 月 3 日到 4 日在北京玩两天，两个人，每段步行不超过 1 公里，太远坐地铁");
await page.waitForTimeout(500);
await shot(`${TAG}-cold`);
await press(page.getByRole("button", { name: /继续规划/ }).first(), "continue");
await page.waitForTimeout(2200);
await press(page.getByRole("button", { name: "对话", exact: true }).first(), "tab-chat");
await page.waitForTimeout(1200);
await press(page.getByRole("button", { name: /对话设置/ }).first(), "open-settings");
await page.waitForTimeout(700);
for (const label of [/本次允许 AI 处理旅行目标/, /本次允许查询公开地图和地点来源/]) {
  const box = page.getByRole("checkbox", { name: label }).first();
  if (await box.count() && !(await box.isChecked())) await box.check().catch(() => {});
  note(`CONSENT ${label} ${await box.isChecked().catch(() => null)}`);
}
await press(page.getByRole("button", { name: /关闭对话设置/ }).first(), "close-settings");
await page.waitForTimeout(400);
await press(page.getByRole("button", { name: /发送/ }).first(), "send");
note("SENT");

let labels = null;
for (let round = 1; round <= 8; round += 1) {
  if (!labels) labels = await waitChoices(240000);
  if (!labels) { note(`ROUND ${round} no-choices`); await shot(`${TAG}-round${round}-none`); break; }
  const before = JSON.stringify(labels);
  let index = labels.findIndex((text) => PREFER.some((word) => text.includes(word)));
  if (index < 0) index = 0;
  note(`ROUND ${round} labels=${before} pick=${JSON.stringify(labels[index])}`);
  const buttons = page.locator('section[aria-label="Agent 请你选择"]').first().locator("button");
  await press(buttons.nth(index), `answer-${round}`);
  labels = null;
  const end = Date.now() + 240000;
  while (Date.now() < end) {
    await page.waitForTimeout(2500);
    const now = await readChoices();
    if (now && JSON.stringify(now) !== before) { labels = now; break; }
  }
  await shot(`${TAG}-round${round}-after`);
  if (!labels) { note(`ROUND ${round} choices-cleared`); break; }
}

const confirmBox = page.getByRole("checkbox", { name: /按以上时间准备方案/ }).first();
const confirmSeen = await confirmBox.waitFor({ state: "attached", timeout: 240000 }).then(() => true).catch(() => false);
if (confirmSeen) {
  await confirmBox.scrollIntoViewIfNeeded().catch(() => {});
  await page.waitForTimeout(400);
  if (!(await confirmBox.isChecked())) await confirmBox.check().catch(() => {});
  note(`CONFIRM_SCHEDULE ${await confirmBox.isChecked().catch(() => null)} t=${elapsed()}`);
  await shot(`${TAG}-confirmed`);
  await press(page.getByRole("button", { name: /保存为正式候选方案/ }).first(), "save-candidate", 60000);
  await page.waitForTimeout(5000);
  await shot(`${TAG}-saved`);
  await press(page.locator('[data-testid="rev-v3-generate-plans"]').first(), "generate-plans", 120000);
  await page.waitForTimeout(6000);
  await shot(`${TAG}-generated`);
  const select = page.locator('[data-testid="rev-plan-select"]').first();
  const selectSeen = await select.waitFor({ state: "visible", timeout: 180000 }).then(() => true).catch(() => false);
  note(`SELECT_BUTTON ${selectSeen} t=${elapsed()}`);
  if (selectSeen) {
    await shot(`${TAG}-plans`);
    await press(select, "select-plan");
    await page.waitForTimeout(6000);
    await shot(`${TAG}-selected`);
  }
} else {
  note("NO_CONFIRM_SCHEDULE");
  const body = await page.evaluate(() => (document.body.innerText || "").slice(0, 700)).catch(() => "");
  note(`BODY ${JSON.stringify(body)}`);
  await shot(`${TAG}-no-draft`);
}

const deadline = Date.now() + 120000;
let last = "";
while (Date.now() < deadline) {
  await page.waitForTimeout(5000);
  const now = await page.evaluate(() => {
    const txt = document.body.innerText || "";
    return {
      active: /正在使用|已选用|旅程已开始|可以确认出发|出发/.test(txt),
      headline: (txt.match(/旅行研究 · [^\n]+/) || [null])[0],
      selected: /正在使用|已选用/.test(txt),
      journey: (() => { try { return localStorage.getItem("citynexus.v8.journey_id"); } catch { return null; } })(),
    };
  });
  const mark = JSON.stringify({ active: now.active, selected: now.selected, headline: now.headline });
  if (mark !== last) { note(`STATE t=${elapsed()} ${mark} journey=${now.journey}`); last = mark; }
  if (now.selected) break;
}
await shot(`${TAG}-final`);
note(`FINAL_JOURNEY ${await page.evaluate(() => localStorage.getItem("citynexus.v8.journey_id")).catch(() => null)}`);
note(`ERRORS ${JSON.stringify(errors.slice(0, 3))}`);
await browser.close();
