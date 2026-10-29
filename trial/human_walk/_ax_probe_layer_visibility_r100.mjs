import { chromium } from "file:///D:/moodle/_cmdr_rescue_v3_1022/frontend/node_modules/playwright/index.mjs";
import fs from "node:fs";

// Section 99 left one question open: the layer tabs are in the DOM with disabled:false, yet a locator
// waiting for "visible" times out.  This measures why, in a single evaluate, for all three testids at
// once: rect size, offsetParent, computed visibility/display, and the nearest <details> ancestor with
// its open state.  Those four separate "inside a collapsed disclosure", "zero box", "css hidden" and
// "detached" -- which is the difference between a product defect and my own instrument.
const DIR = "D:/moodle/_cmdr_rescue_v3_1022/trial/results/20261026_gozero";
const OUT = `${DIR}/ax-layer-visibility-r100.txt`;
const NL = String.fromCharCode(10);
const lines = [];
const note = (v) => { lines.push(v); fs.writeFileSync(OUT, lines.join(NL) + NL, "utf8"); };
const started = Date.now();
const elapsed = () => ((Date.now() - started) / 1000).toFixed(1);

const ctx = await chromium.launchPersistentContext("D:/moodle/_cmdr_v3_live_1022/_chrome_gozero_ax100", {
  channel: "chrome", headless: false, viewport: { width: 430, height: 932 }, deviceScaleFactor: 1,
});
const page = ctx.pages()[0] ?? await ctx.newPage();
const ids = ["rev-mission-layer-map", "rev-mission-layer-timeline", "rev-mission-layer-agent"];

const measure = () => page.evaluate((list) => list.map((id) => {
  const n = document.querySelector(`[data-testid="${id}"]`);
  if (!n) return { id, present: false };
  const b = n.getBoundingClientRect();
  const cs = getComputedStyle(n);
  let details = null;
  for (let p = n; p; p = p.parentElement) { if (p.tagName === "DETAILS") { details = { open: p.open }; break; } }
  let hiddenAncestor = null;
  for (let p = n; p; p = p.parentElement) {
    const s = getComputedStyle(p);
    if (s.display === "none" || s.visibility === "hidden" || Number(s.opacity) === 0) {
      hiddenAncestor = `${p.tagName}.${String(p.className).slice(0, 30)} display=${s.display} vis=${s.visibility} op=${s.opacity}`;
      break;
    }
  }
  return { id, present: true, w: Math.round(b.width), h: Math.round(b.height), top: Math.round(b.top),
    offsetParent: n.offsetParent ? n.offsetParent.tagName : null,
    display: cs.display, visibility: cs.visibility, opacity: cs.opacity,
    disabled: Boolean(n.disabled), details, hiddenAncestor };
}), ids);

await page.goto("http://127.0.0.1:14462/revolution", { waitUntil: "domcontentloaded", timeout: 60000 });
await page.waitForTimeout(6000);
note(`COLD ${JSON.stringify(await measure())} t=${elapsed()}`);

await page.getByRole("textbox", { name: /想怎么玩/ }).first()
  .fill("2026 年 12 月 3 日到 4 日在北京玩两天，两个人，每段步行不超过 1 公里，太远坐地铁");
await page.waitForTimeout(600);
await page.getByRole("button", { name: /继续规划/ }).first().click().catch(() => note("CONTINUE_MISS"));
await page.waitForTimeout(3000);
await page.getByRole("button", { name: "对话", exact: true }).first().click().catch(() => note("CHAT_MISS"));
await page.waitForTimeout(1500);
await page.getByRole("button", { name: /对话设置/ }).first().click().catch(() => note("SETTINGS_MISS"));
await page.waitForTimeout(800);
for (const label of [/本次允许 AI 处理旅行目标/, /本次允许查询公开地图和地点来源/]) {
  const box = page.getByRole("checkbox", { name: label }).first();
  if (await box.count() && !(await box.isChecked())) await box.check().catch(() => {});
}
await page.getByRole("button", { name: /关闭对话设置/ }).first().click().catch(() => {});
await page.waitForTimeout(500);
await page.getByRole("button", { name: /发送/ }).first().click().catch(() => note("SEND_MISS"));
note(`SENT t=${elapsed()}`);

const skipEnd = Date.now() + 6 * 60 * 1000;
while (Date.now() < skipEnd) {
  const s = page.locator('[data-testid="rev-agent-skip-questions"]');
  if (await s.count()) { await s.first().click().catch(() => {}); note(`SKIP t=${elapsed()}`); break; }
  await page.waitForTimeout(3000);
}
const draftEnd = Date.now() + 12 * 60 * 1000;
let seen = false;
while (Date.now() < draftEnd) {
  const m = await measure();
  if (m.some((x) => x.present)) { seen = true; note(`LAYERS_PRESENT t=${elapsed()} ${JSON.stringify(m)}`); break; }
  await page.waitForTimeout(6000);
}
if (!seen) note(`NO_LAYER_KEYS_IN_WINDOW t=${elapsed()} ${JSON.stringify(await measure())}`);
else note(`AFTER ${JSON.stringify(await measure())} t=${elapsed()}`);
const body = await page.evaluate(() => document.body.innerText || "").catch(() => "");
note(`HAS_SAVE_KEY ${body.includes("保存为正式候选方案")} t=${elapsed()}`);
await page.screenshot({ path: `${DIR}/430-ax-layer-visibility.png` }).catch(() => {});
await ctx.close();
