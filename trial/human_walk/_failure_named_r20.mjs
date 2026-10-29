import { chromium } from "file:///D:/moodle/_cmdr_rescue_v3_1022/frontend/node_modules/playwright/index.mjs";
import fs from "node:fs";

const BASE = "http://127.0.0.1:14461";
const DIR = "D:/moodle/_cmdr_rescue_v3_1022/trial/results/20261026_gozero";
const OUT = `${DIR}/failure-path-390.txt`;
const NL = String.fromCharCode(10);
const lines = [];
const note = (v) => { lines.push(v); fs.writeFileSync(OUT, lines.join(NL) + NL, "utf8"); };
const started = Date.now();
const elapsed = () => ((Date.now() - started) / 1000).toFixed(1);

const ctx = await chromium.launchPersistentContext("D:/moodle/_cmdr_v3_live_1022/_chrome_gozero_fail", {
  channel: "chrome", headless: false, viewport: { width: 390, height: 844 },
});
const page = ctx.pages()[0] ?? await ctx.newPage();
page.on("response", (resp) => {
  const url = resp.url();
  if (/goal-tasks.*\/(run|resume)$/.test(url)) note(`POST ${resp.status()} ${url.split("/").slice(-2).join("/")} t=${elapsed()}`);
});
async function shot(name) {
  await page.screenshot({ path: `${DIR}/${name}.png`, fullPage: false }).catch(() => {});
  note(`SHOT ${name}`);
}
async function visible(l) { try { return await l.first().isVisible(); } catch { return false; } }
async function press(l, label, timeout = 8000) {
  const t = l.first();
  try { await t.waitFor({ state: "visible", timeout }); } catch { note(`MISS ${label}`); return false; }
  await t.evaluate((n) => n.scrollIntoView({ block: "center" })).catch(() => {});
  await page.waitForTimeout(250);
  const ok = await t.evaluate((node) => {
    const b = node.getBoundingClientRect();
    const top = document.elementFromPoint(b.left + b.width / 2, b.top + b.height / 2);
    return Boolean(top) && (node === top || node.contains(top)) && !node.disabled;
  });
  note(`HIT ${label} ${ok}`);
  if (!ok) return false;
  await t.click({ timeout: 15000 }).catch(() => {});
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
note(`SENT t=${elapsed()}`);

const alert = page.locator('[data-testid="rev-agent-failure"]');
const deadline = Date.now() + 6 * 60 * 1000;
let text = "";
while (Date.now() < deadline) {
  if (await visible(alert)) { text = await alert.first().innerText().catch(() => ""); break; }
  const body = await page.evaluate(() => document.body.innerText || "");
  if (/正在研究|Agent 正在处理/.test(body)) { await page.waitForTimeout(5000); continue; }
  const named = (body.match(/现场模型[^\n]{0,80}/) || [null])[0];
  if (named) { text = named; break; }
  await page.waitForTimeout(5000);
}
note(`FAILURE_TEXT ${JSON.stringify(text)} t=${elapsed()}`);
if (text) {
  const node = await alert.count() ? alert.first() : page.getByText(text).first();
  await node.scrollIntoViewIfNeeded().catch(() => {});
  await page.waitForTimeout(500);
  await shot("390-failure-named");
}
const body = await page.evaluate(() => (document.body.innerText || "").slice(0, 900));
note(`BODY ${JSON.stringify(body)}`);
await ctx.close();
