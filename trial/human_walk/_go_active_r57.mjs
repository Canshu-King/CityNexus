import { chromium } from "file:///D:/moodle/_cmdr_rescue_v3_1022/frontend/node_modules/playwright/index.mjs";
import fs from "node:fs";

const W = Number(process.env.RW || 390);
const H = Number(process.env.RH || 844);
const TAG = String(W);
const PROFILE = process.env.PROFILE || "D:/moodle/_cmdr_v3_live_1022/_chrome_gozero_map46";
const BASE = "http://127.0.0.1:14461";
const DIR = "D:/moodle/_cmdr_rescue_v3_1022/trial/results/20261026_gozero";
const OUT = `${DIR}/go-active-${TAG}-r57.txt`;
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
// The reading that decides where the fault is: every map-places answer this page gets, with the shape of
// its first point.  Recorded from the very first request, not only after the map layer is opened.
const mapReads = [];
page.on("response", async (resp) => {
  if (!resp.url().includes("/map-places")) return;
  let body = null;
  try { body = await resp.json(); } catch { body = null; }
  const first = (body && Array.isArray(body.candidates) && body.candidates[0]) || null;
  mapReads.push(JSON.stringify({http_status: resp.status(), candidates: Array.isArray(body?.candidates) ? body.candidates.length : null,
    first: first && {candidate_id: String(first.candidate_id).slice(0, 22), origin: first.origin ?? null,
      coordinate_system: first.coordinate_system ?? null, region_status: first.region_status ?? null,
      selection_state: first.selection_state ?? null}}));
});
page.on("pageerror", (error) => errors.push(String(error).slice(0, 160)));
page.on("response", async (resp) => {
  const url = resp.url();
  const method = resp.request().method();
  if (!url.includes("/api/v1/") || (method !== "POST" && method !== "PUT")) return;
  if (!/goal-tasks|plans|journeys|departure/.test(url)) return;
  const line = `HTTP ${method} ${resp.status()} ${url.replace(/^http:\/\/[^/]+/, "")}`;
  if (resp.status() >= 400) {
    let detail = "";
    try { detail = JSON.stringify(await resp.json()).slice(0, 500); } catch { detail = "(unreadable body)"; }
    note(line + " BODY " + detail);
  } else {
    note(line);
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
await shot(`${TAG}-g7-cold`);
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
await shot(`${TAG}-g7-after-research`);

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
  await shot(`${TAG}-g7-after-fix`);
}

async function dropOptionalSlot() {
  const dayTab = page.getByRole("button", { name: /按天调整行程/ });
  if (await visible(dayTab)) { await press(dayTab, "day-tab", 10000); await page.waitForTimeout(1500); }
  const editor = page.locator('section[aria-label="可编辑旅行草案"]');
  if (!(await editor.count())) { note("NO_DRAFT_EDITOR"); return false; }
  const slots = editor.locator("details.rev-goal-draft-slot");
  const total = await slots.count();
  note(`DRAFT_SLOTS ${total}`);
  for (let i = 0; i < total; i += 1) {
    const slot = slots.nth(i);
    const text = (await slot.locator("summary").first().innerText().catch(() => "")) || "";
    if (!/可选|南锣/.test(text)) continue;
    await slot.locator("summary").first().click({ timeout: 8000 }).catch(() => {});
    await page.waitForTimeout(500);
    const remove = slot.getByRole("button", { name: /移除这项安排/ });
    if (!(await remove.count())) { note("NO_REMOVE_BUTTON"); return false; }
    await remove.first().click({ timeout: 8000 }).catch(() => {});
    note(`REMOVED ${JSON.stringify(text.slice(0, 40))}`);
    await page.waitForTimeout(600);
    const save = editor.getByRole("button", { name: /保存草案/ });
    if (!(await save.count())) { note("NO_SAVE_BUTTON"); return true; }
    await save.first().scrollIntoViewIfNeeded().catch(() => {});
    await save.first().click({ timeout: 8000 }).catch(() => {});
    for (let k = 0; k < 20; k += 1) {
      await page.waitForTimeout(1500);
      const body = await bodyText();
      const mark = (body.match(/草案已保存到这趟旅行|保存失败.{0,40}|请补一个标题.{0,40}/) || [null])[0];
      if (mark) { note(`DRAFT_SAVE ${JSON.stringify(mark)}`); break; }
    }
    return true;
  }
  note("NO_OPTIONAL_SLOT");
  return false;
}

await openJourney();
await dropOptionalSlot();
await page.waitForTimeout(1500);
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
      if (await press(saveButton, `save-${round}-${i}`, 30000)) {
        await page.waitForTimeout(6000);
        // Arm M pressed 保存为正式候选方案 seven times and never once wrote down what the card said
        // back, so the refusal names lived only on the screen.  Read them every press.
        const saved = await page.locator(".rev-plan-message, [role='alert'], [role='status']").allInnerTexts().catch(() => []);
        note(`SAVE_ALERT ${round}/${i} ${JSON.stringify(saved.slice(0, 3))}`);
        continue;
      }
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
    const selCount = await select.count();
    const selVisible = await visible(select);
    const selEnabled = selVisible ? await select.isEnabled().catch(() => false) : false;
    if (selCount > 0) {
      const html = await select.first().evaluate((node) => ({ disabled: node.disabled, cls: node.className, parent: node.parentElement?.className || "" })).catch(() => null);
      note(`SELECT_STATE count=${selCount} visible=${selVisible} enabled=${selEnabled} ${JSON.stringify(html)} t=${elapsed()}`);
    }
    if (selVisible && !selEnabled && await visible(refreshPlan)) {
      await press(refreshPlan, `refresh-for-disabled-${round}-${i}`, 10000);
      await page.waitForTimeout(2500);
      continue;
    }
    if (selCount === 0 && (await visible(startButton)) && await press(startButton, `start-fallback-${round}-${i}`, 30000)) {
      startedJourney = true;
      await page.waitForTimeout(9000);
      await shot(`${TAG}-g7-started-fallback`);
      break;
    }
    if (selVisible && selEnabled) {
      await shot(`${TAG}-g7-plans-${round}`);
      if (await press(select, `select-${round}`, 30000)) {
        await page.waitForTimeout(5000);
        const refusal = await page.locator(".rev-plan-message, [role='alert']").allInnerTexts().catch(() => []);
        note(`SELECT_REFUSAL ${JSON.stringify(refusal.slice(0, 2))}`);
        // The refusal names the rows and says which door moves them, so ask for exactly that before
        // pressing anything -- the traveller's own recovery path, not a scripted override.
        const askBox = page.locator("#rev-mission-chat-input");
        if (await visible(askBox)) {
          for (let k = 0; k < 40 && !(await askBox.isEnabled().catch(() => false)); k += 1) await page.waitForTimeout(3000);
          await askBox.fill(`上面这句按不了：${refusal.join(" ").slice(0, 400)} 请把被点名的这几处按它们来源给的开放时间挪好，其它日期和其它安排都别动。`).catch(() => undefined);
          if (await press(page.getByRole("button", { name: /^发送/ }), `ask-refusal-${round}`, 15000)) {
            note(`ASK_REFUSAL_SENT ${round} t=${elapsed()}`);
            await waitIdle(10, 45);
          }
        }
        await shot(`${TAG}-g7-selected-${round}`);
        if (await visible(startButton) && await press(startButton, "start-journey", 30000)) {
          startedJourney = true;
          await page.waitForTimeout(10000);
          await shot(`${TAG}-g7-started`);
          break;
        }
        if (await visible(refreshPlan)) { await press(refreshPlan, `refresh-after-select-${round}`, 10000); await page.waitForTimeout(4000); }
        const replan = page.locator('[data-testid="rev-plan-replan"]');
        if (await visible(replan)) {
          await press(replan, `replan-${round}`, 15000);
          // The card shows the reveal hand first and the apply hand only after it is pressed
          // (DraftDepartureCard.tsx:342 then :344), so a walk that waits only for the apply key never
          // presses the one that makes it exist.
          const reveal = page.locator('[data-testid="rev-v3-replan"]');
          for (let k = 0; k < 25 && !(await visible(reveal)); k += 1) await page.waitForTimeout(1000);
          note(`REVEAL_SEEN ${await visible(reveal)} t=${elapsed()}`);
          if (await visible(reveal)) await press(reveal, `replan-reveal-${round}`, 15000);
          const apply = page.locator('[data-testid="rev-v3-replan-apply"]');
          for (let k = 0; k < 20 && !(await visible(apply)); k += 1) await page.waitForTimeout(1000);
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
    note(`LOOP ${round}/${i} GATE ${JSON.stringify(gate.slice(0, 1))} GAPS_ALL ${JSON.stringify(gaps)} ALERT ${JSON.stringify(alerts.slice(0, 1))}`);
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
await shot(`${TAG}-g7-final`);
note(`FINAL_BODY ${JSON.stringify((await bodyText()).slice(0, 2200))}`);
note(`ERRORS ${JSON.stringify(errors.slice(0, 3))}`);
// The knife under test is no longer the map: it is the hand that has to sit beside the server's
// refusal sentence (backend/app/services.py:742 makes the candidate unselectable while a confirmed
// time band still has no place).  Read every gap paragraph, then press the hand if it is there.
const gapsAll = await page.locator(".rev-plan-gap").allInnerTexts().catch(() => []);
note(`PLAN_GAPS_ALL ${JSON.stringify(gapsAll)} t=${elapsed()}`);
note(`PLAN_SELECT ${await page.locator('[data-testid="rev-plan-select"]').count()}`);
note(`PLAN_START ${await page.locator('[data-testid="rev-plan-start"]').count()}`);
const hand = page.locator('[data-testid="rev-plan-open-place-explore"]');
note(`PLAN_HAND ${await hand.count()} t=${elapsed()}`);
await shot(`${TAG}-r54-plan-blocked`);
if (await hand.count()) {
  const pressed = await press(hand, "open-place-hand", 12000);
  await page.waitForTimeout(4000);
  const after = await bodyText();
  note(`HAND_PRESSED ${pressed} t=${elapsed()}`);
  note(`AFTER_HAND_HEAD ${JSON.stringify(after.replace(/\s+/g, " ").slice(0, 300))}`);
  note(`AFTER_HAND_HAS_EXPLORE ${/探索|查找地点|候选地点|已找到的地点/.test(after)}`);
  await shot(`${TAG}-r54-after-hand`);
}
// The knife under test: after the traveller's own accept, the 地图 layer must show the stops that the
// accepted plan contains -- not 「0 处地点」 beside a schedule of six.
const mapCalls = [];
page.on("response", async (resp) => {
  if (!resp.url().includes("/map-places")) return;
  let count = -2;
  try { const body = await resp.json(); count = (body.candidates || []).length; } catch { count = -2; }
  mapCalls.push(`http_status=${resp.status()} candidates=${count}`);
});
await press(page.getByRole("button", { name: /^地图$/ }), "map-layer", 15000);
await page.waitForTimeout(3000);
const pane = page.locator('[data-testid="rev-mission-layer-map"]');
const paneText = async () => (await pane.first().innerText().catch(() => "")) || "";
note("MAP_PANE " + await pane.count());
note("MAP_CALLS " + JSON.stringify(mapCalls));
note("MAP_READS_EVERY " + JSON.stringify(mapReads));
note("MAP_HEAD " + JSON.stringify((await paneText()).replace(/\s+/g, " ").slice(0, 300)));
note("MAP_PLANNED_TAGS " + await page.locator('[data-testid="rev-map-planned-stop"]').count());
note("MAP_LIST_ITEMS " + await page.locator('ol[aria-label="地图地点"] li').count());
note("MAP_COUNT_LINE " + JSON.stringify(await page.evaluate(() => (document.body.innerText.match(/地图地点 \d+ 处 · 高德地点 \d+ 处/) || [null])[0])));
note("MAP_AMAP_LINKS " + await page.getByText("在高德地图打开", { exact: false }).count());
await shot(`${TAG}-g8-map-preview`);
await press(page.getByRole("button", { name: "加载地图", exact: true }), "load-map", 12000);
await page.waitForTimeout(7000);
note("MAP_CANVAS " + await page.locator('[data-testid="rev-workspace-map-canvas"]').count());
note("MAP_PINS " + await page.locator(".rev-workspace-map-pin").count());
note("MAP_AFTER_CONSENT " + JSON.stringify((await paneText()).replace(/\s+/g, " ").slice(0, 400)));
await shot(`${TAG}-g8-map-loaded`);
note("MAP_CALLS_AFTER " + JSON.stringify(mapCalls));
note("ERRORS_MAP " + JSON.stringify(errors.slice(0, 3)));
// The refresh arm: a traveller who reloads must land on the same map, not on an empty one.
await page.reload({ waitUntil: "domcontentloaded", timeout: 60000 });
await page.waitForTimeout(12000);
await press(page.getByRole("button", { name: /^地图$/ }), "map-layer-after-reload", 15000);
await page.waitForTimeout(3000);
note("RELOAD_MAP_COUNT_LINE " + JSON.stringify(await page.evaluate(() => (document.body.innerText.match(/地图地点 \d+ 处 · 高德地点 \d+ 处/) || [null])[0])));
note("RELOAD_PLANNED_TAGS " + await page.locator('[data-testid="rev-map-planned-stop"]').count());
note("RELOAD_LIST_ITEMS " + await page.locator('ol[aria-label="地图地点"] li').count());
note("RELOAD_MAP_READS " + JSON.stringify(mapReads.slice(-3)));
await shot(`${TAG}-g8-map-reloaded`);
await ctx.close();
