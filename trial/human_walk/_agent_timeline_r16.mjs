import { chromium } from "file:///D:/moodle/_cmdr_rescue_v3_1022/frontend/node_modules/playwright/index.mjs";
import fs from "node:fs";

const BASE = "http://127.0.0.1:14461";
const DIR = "D:/moodle/_cmdr_rescue_v3_1022/trial/results/20261026_gozero";
const OUT = `${DIR}/agent-timeline-390b.txt`;
const NL = String.fromCharCode(10);
const lines = [];
const note = (value) => { lines.push(value); fs.writeFileSync(OUT, lines.join(NL) + NL, "utf8"); };
const elapsed = (t0) => ((Date.now() - t0) / 1000).toFixed(1);
const started = Date.now();

const ctx = await chromium.launchPersistentContext(process.env.PROFILE || "D:/moodle/_cmdr_v3_live_1022/_chrome_gozero_timeline2", {
  channel: "chrome", headless: false, viewport: { width: 390, height: 844 }, deviceScaleFactor: 1,
});
const page = ctx.pages()[0] ?? await ctx.newPage();

async function visible(locator) { try { return await locator.first().isVisible(); } catch { return false; } }
async function press(locator, label, timeout = 8000) {
  const target = locator.first();
  try { await target.waitFor({ state: "visible", timeout }); } catch { note(`MISS ${label}`); return false; }
  await target.evaluate((node) => node.scrollIntoView({ block: "center" })).catch(() => {});
  await page.waitForTimeout(250);
  const ok = await target.evaluate((node) => {
    const box = node.getBoundingClientRect();
    const top = document.elementFromPoint(box.left + box.width / 2, box.top + box.height / 2);
    return Boolean(top) && (node === top || node.contains(top)) && !node.disabled;
  });
  note(`HIT ${label} ${ok} t=${elapsed(started)}`);
  if (!ok) return false;
  await target.click({ timeout: 15000 }).catch(() => {});
  await page.waitForTimeout(600);
  return true;
}

await page.goto(`${BASE}/revolution`, { waitUntil: "domcontentloaded", timeout: 60000 });
await page.waitForTimeout(4000);
await page.getByRole("textbox", { name: /想怎么玩/ }).first()
  .fill("2026 年 12 月 3 日到 4 日在北京玩两天，两个人，每段步行不超过 1 公里，太远坐地铁");
await page.waitForTimeout(400);
await press(page.getByRole("button", { name: /继续规划/ }), "continue");
await page.waitForTimeout(2200);
await press(page.getByRole("button", { name: "对话", exact: true }), "tab-chat");
await page.waitForTimeout(1000);
await press(page.getByRole("button", { name: /对话设置/ }), "settings");
await page.waitForTimeout(600);
for (const label of [/本次允许 AI 处理旅行目标/, /本次允许查询公开地图和地点来源/]) {
  const box = page.getByRole("checkbox", { name: label }).first();
  if (await box.count() && !(await box.isChecked())) await box.check().catch(() => {});
}
await press(page.getByRole("button", { name: /关闭对话设置/ }), "close-settings");
await page.waitForTimeout(300);
await press(page.getByRole("button", { name: /发送/ }), "send");

const skip = page.locator('[data-testid="rev-agent-skip-questions"]');
for (let i = 0; i < 60; i += 1) {
  if (await visible(skip) && await press(skip, "skip", 10000)) { note("SKIPPED"); break; }
  await page.waitForTimeout(3000);
}
// Wait for the research round to write at least one tool step.
let cards = 0;
for (let i = 0; i < 120; i += 1) {
  const body = await page.evaluate(() => document.body.innerText || "").catch(() => "");
  if (/已整理\s*\d+\s*天/.test(body)) { note(`DRAFT t=${elapsed(started)}`); break; }
  await page.waitForTimeout(5000);
}
// The timeline lives in the assistant layer; the composer must be idle before touching it.
const composer = page.locator("#rev-mission-chat-input");
for (let i = 0; i < 120 && !(await composer.isEnabled().catch(() => false)); i += 1) await page.waitForTimeout(3000);
note(`IDLE t=${elapsed(started)}`);
await press(page.getByRole("button", { name: "对话", exact: true }), "tab-chat");
await page.waitForTimeout(1500);

const timeline = page.locator('[data-testid="rev-agent-tool-timeline"]');
const has = await visible(timeline);
note(`TIMELINE ${has} t=${elapsed(started)}`);
if (has) {
  await timeline.scrollIntoViewIfNeeded().catch(() => {});
  await page.waitForTimeout(400);
  await timeline.evaluate((node) => { if (node instanceof HTMLDetailsElement) node.open = true; }).catch(() => {});
  await page.waitForTimeout(400);
  const summary = await timeline.locator("summary").innerText().catch(() => "");
  const statuses = await timeline.locator('[data-testid="rev-agent-tool-status"]').allInnerTexts().catch(() => []);
  const next = await page.locator('[data-testid="rev-agent-next-action"]').innerText().catch(() => "");
  const count = await timeline.locator("li").count();
  note(`SUMMARY ${JSON.stringify(summary)} STEPS ${count} STATUSES ${JSON.stringify(statuses.slice(0, 8))}`);
  note(`NEXT ${JSON.stringify(next)}`);
  await page.screenshot({ path: `${DIR}/390-agent-timeline-local.png`, fullPage: false }).catch(() => {});
  note("SHOT 390-agent-timeline");
  const box = await timeline.boundingBox().catch(() => null);
  if (box) note(`BOX ${JSON.stringify({ x: Math.round(box.x), y: Math.round(box.y), w: Math.round(box.width), h: Math.round(box.height) })}`);
}
note(`ERRORS ${JSON.stringify([])}`);
await ctx.close();
