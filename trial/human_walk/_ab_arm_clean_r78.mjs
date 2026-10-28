import { chromium } from "file:///D:/moodle/_cmdr_rescue_v3_1022/frontend/node_modules/playwright/index.mjs";
import fs from "node:fs";

const W = Number(process.env.RW || 390);
const H = Number(process.env.RH || 844);
const TAG = String(W);
const PROFILE = process.env.PROFILE || "D:/moodle/_cmdr_v3_live_1022/_chrome_gozero_ab78";
const BASE = "http://127.0.0.1:14462";
const DIR = "D:/moodle/_cmdr_rescue_v3_1022/trial/results/20261026_gozero";
const OUT = `${DIR}/ab-clean-chain-${TAG}-r78.txt`;
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
    try { detail = JSON.stringify(await resp.json()).slice(0, 2000); } catch { detail = "(unreadable body)"; }
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

// The last open box on the first knife: a traveller who moves exactly one half-day band must see the
// other bands stay where they were.  Only the last time input is touched, then the real 保存 is pressed.
const openFold = page.locator("text=编辑行程时间（可选）").first();
if (await visible(openFold)) { await openFold.click().catch(() => {}); await page.waitForTimeout(1500); }
const timeInputs = page.locator('input[type="time"]');
const readTimes = () => timeInputs.evaluateAll((nodes) => nodes.map((node) => ({
  label: node.getAttribute("aria-label") || "", value: node.value,
})));
const before = await readTimes();
note(`DRIFT_FOLD ${await visible(openFold)} TIME_COUNT ${before.length} BEFORE ${JSON.stringify(before).slice(0, 900)} t=${elapsed()}`);
if (before.length > 1) {
  const lastIndex = before.length - 1;
  const lastLabel = before[lastIndex].label;
  const current = before[lastIndex].value;
  const [hh, mm] = current.split(":").map((part) => Number(part));
  const total = Math.max(0, hh * 60 + mm - 45);
  const next = `${String(Math.floor(total / 60) % 24).padStart(2, "0")}:${String(total % 60).padStart(2, "0")}`;
  await timeInputs.nth(lastIndex).fill(next);
  note(`TIME_EDITED ${JSON.stringify(lastLabel)} ${current} -> ${next} t=${elapsed()}`);
  if (await visible(confirmBox) && !(await confirmBox.isChecked().catch(() => false))) await confirmBox.check().catch(() => {});
  await page.waitForTimeout(1200);
  note(`W_CONFIRM ${await confirmBox.isChecked().catch(() => false)} SAVE_ENABLED ${await saveButton.isEnabled().catch(() => false)} t=${elapsed()}`);
  if (await press(saveButton, "save-drift", 30000)) {
    await page.waitForTimeout(7000);
    const alerted = await page.locator(".rev-plan-message, [role='alert'], [role='status']").allInnerTexts().catch(() => []);
    note(`DRIFT_SAVE_ALERT ${JSON.stringify(alerted.slice(0, 3))}`);
    const after = await readTimes();
    const changed = after.filter((row) => {
      const prior = before.find((item) => item.label === row.label);
      return prior ? row.value !== prior.value : true;
    }).map((row) => row.label);
    const lost = before.filter((row) => !after.some((item) => item.label === row.label)).map((row) => row.label);
    note(`TIME_AFTER ${JSON.stringify(after).slice(0, 900)} t=${elapsed()}`);
    note(`DRIFT_CHANGED_ONLY ${JSON.stringify(changed)} COUNT ${before.length}->${after.length} LOST ${JSON.stringify(lost)}`);
    const movedOthers = changed.filter((label) => label !== lastLabel);
    note(`DRIFT_COUNT ${movedOthers.length} TARGET_ONLY ${changed.length === 1 ? "yes" : "no"} t=${elapsed()}`);
    await shot(`${TAG}-drift-after`);
  } else {
    note("DRIFT_SAVE_NOT_PRESSED");
  }
} else {
  note("DRIFT_NO_TIME_INPUTS -- the fold never opened or the draft has no timed bands");
}

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
        // The card says exactly which row to move and which rows to leave alone; the walk has to obey it,
        // otherwise the same 422 comes back forever.  Anything ending past 21:00 is pulled back to 21:00.
        if (saved.join(' ').includes('超出了这趟旅行的结束')) {
          const pulled = await timeInputs.evaluateAll((nodes) => {
            const fixed = [];
            for (const node of nodes) {
              if (!/结束时间/.test(node.getAttribute('aria-label') || '')) continue;
              if (node.value <= '21:00') continue;
              fixed.push(node.getAttribute('aria-label'));
              const setter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
              setter.call(node, '21:00');
              node.dispatchEvent(new Event('input', { bubbles: true }));
            }
            return fixed;
          });
          note(`SAVE_REPAIR ${round}/${i} ${JSON.stringify(pulled)} t=${elapsed()}`);
          await page.waitForTimeout(1500);
          continue;
        }
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
    const selEnabled = selVisible ? await select.first().isEnabled().catch(() => false) : false;
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
            // The sentence offers two exits; take the one it lists second — pull the earlier stop's end
            // time forward by fifteen minutes on every band — then let the loop re-save, re-freeze and re-select.
            const movedBack = await timeInputs.evaluateAll((nodes) => {
              const touched = [];
              for (const node of nodes) {
                const label = node.getAttribute("aria-label") || "";
                if (!/结束时间/.test(label)) continue;
                const parts = node.value.split(":").map((part) => Number(part));
                const minutes = Math.max(0, parts[0] * 60 + parts[1] - 15);
                const next = `${String(Math.floor(minutes / 60)).padStart(2, "0")}:${String(minutes % 60).padStart(2, "0")}`;
                if (next === node.value) continue;
                touched.push(`${label} ${node.value}->${next}`);
                const setter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, "value").set;
                setter.call(node, next);
                node.dispatchEvent(new Event("input", { bubbles: true }));
              }
              return touched;
            });
            note(`GAP_REPAIR ${round} ${JSON.stringify(movedBack).slice(0, 320)} t=${elapsed()}`);
            await page.waitForTimeout(1500);
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

// X arm tail: after the traveller presses the hand beside the refusal sentence, actually walk the
// explore screen -- find a real place, let the screen turn it into a formal plan place, then take
// the 选用 / 出发 doors on the same journey and read the map against the activity count.
// Every step surveys the screen first, so a miss reports what the traveller could see instead of
// silently pressing nothing.
const survey = async (label) => {
  const seen = await page.evaluate(() => {
    const nodes = Array.from(document.querySelectorAll("button,[role='button'],input,select,a[data-testid]")).slice(0, 90);
    return nodes.filter((node) => {
      const box = node.getBoundingClientRect();
      return box.width > 4 && box.height > 4;
    }).map((node) => ({
      tag: node.tagName,
      id: node.getAttribute("data-testid") || "",
      name: String(node.getAttribute("aria-label") || node.innerText || node.placeholder || "").replace(/\s+/g, " ").slice(0, 44),
      dis: Boolean(node.disabled),
    }));
  });
  note(`SURVEY_${label} ${JSON.stringify(seen).slice(0, 3000)} t=${elapsed()}`);
  return seen;
};

const byTestId = (id) => page.locator(`[data-testid="${id}"]`);
const byTestIdPrefix = (prefix) => page.locator(`[data-testid^="${prefix}"]`);
const pressNear = async (locator, label, timeout = 15000) => {
  if (!(await locator.count())) { note(`MISS ${label} absent t=${elapsed()}`); return false; }
  const target = locator.first();
  if (!(await target.isVisible().catch(() => false))) {
    await target.evaluate((node) => node.scrollIntoView({ block: "center" })).catch(() => undefined);
    await page.waitForTimeout(1200);
    const stillHidden = !(await target.isVisible().catch(() => false));
    note(`SCROLL_RETRY ${label} stillHidden=${stillHidden} t=${elapsed()}`);
    if (stillHidden) return false;
  }
  const hit = await target.evaluate((node) => {
    node.scrollIntoView({ block: "center" });
    const box = node.getBoundingClientRect();
    const cx = box.left + box.width / 2;
    const cy = box.top + box.height / 2;
    const top = document.elementFromPoint(cx, cy);
    return { hitSelf: top === node || node.contains(top), cx, cy, disabled: Boolean(node.disabled) };
  }).catch(() => null);
  note(`HIT ${label} ${JSON.stringify(hit)} t=${elapsed()}`);
  if (!hit || !hit.hitSelf || hit.disabled) return false;
  await page.mouse.click(hit.cx, hit.cy);
  await page.waitForTimeout(1500);
  return true;
};
const typeInto = async (locator, value, label) => {
  if (!(await locator.count())) { note(`MISS type-${label} absent t=${elapsed()}`); return false; }
  const box = locator.first();
  if (!(await box.isVisible().catch(() => false))) { note(`MISS type-${label} hidden t=${elapsed()}`); return false; }
  await box.click({ timeout: 8000 }).catch(() => undefined);
  await box.fill(value).catch(() => undefined);
  note(`TYPED ${label} ${JSON.stringify(await box.inputValue().catch(() => ""))} t=${elapsed()}`);
  return true;
};

note(`EXPLORE_STAGE_PROBE area=${await byTestId("rev-quick-area").count()} category=${await byTestId("rev-quick-category").count()} results=${await byTestId("rev-quick-results").count()} explore=${await byTestId("rev-quick-explore").count()} t=${elapsed()}`);
await survey("EXPLORE_ENTRY");

// Step 1 — the area pane: look the city up and take the geocoder's own centre.
if (await byTestId("rev-quick-area").count()) {
  await typeInto(page.locator('[data-testid="rev-quick-area"] input'), "北京市", "CITY");
  await pressNear(byTestId("rev-quick-find-city"), "find-city");
  for (let i = 0; i < 30 && !(await byTestId("rev-quick-city-results").count()); i += 1) await page.waitForTimeout(1000);
  const cityButtons = page.locator('[data-testid="rev-quick-city-results"] button');
  note(`CITY_RESULTS ${await cityButtons.count()} ${JSON.stringify((await cityButtons.allInnerTexts().catch(() => [])).slice(0, 3)).slice(0, 300)} t=${elapsed()}`);
  if (await cityButtons.count()) {
    await pressNear(cityButtons, "city-first");
    await page.waitForTimeout(2000);
    if (await byTestId("rev-quick-use-approx-center").count()) await pressNear(byTestId("rev-quick-use-approx-center"), "use-approx-center");
    await survey("AFTER_AREA");
  } else {
    note("NO_CITY_RESULT_SCREEN t=" + elapsed());
    await byTestId("rev-quick-photon-search").count() && pressNear(byTestId("rev-quick-photon-search"), "photon-search");
    await survey("AFTER_PHOTON");
  }
}

// Step 2 — the interest pane: name one place the traveller actually wants, and search.
for (let i = 0; i < 20 && !(await byTestId("rev-quick-results").count()); i += 1) await page.waitForTimeout(1500);
note(`RESULTS_PANE ${await byTestId("rev-quick-results").count()} t=${elapsed()}`);
await survey("INTEREST_OR_RESULTS");
const nameBox = page.locator('input[placeholder*="例如"]');
if (await nameBox.count()) {
  await typeInto(nameBox, "天坛", "PLACE_NAME");
  const searchButton = page.getByRole("button", { name: /搜索|查找|看结果/ });
  await pressNear(searchButton, "place-name-search");
  for (let i = 0; i < 40 && !(await byTestId("rev-quick-place-card").count()); i += 1) await page.waitForTimeout(1500);
}
await page.waitForTimeout(2000);

// Step 3 — read every card the provider returned, then look for the door that makes one of them
// the plan's place.
const cards = byTestIdPrefix("rev-quick-select-");
const cardCount = await cards.count();
const cardTexts = await page.locator('[data-testid="rev-quick-place-card"]').allInnerTexts().catch(() => []);
const blockers = await byTestIdPrefix("rev-quick-place-blocker-").allInnerTexts().catch(() => []);
note(`CARDS ${cardCount} t=${elapsed()}`);
note(`CARD_TEXTS ${JSON.stringify(cardTexts.slice(0, 4)).slice(0, 1200)}`);
note(`CARD_BLOCKERS ${JSON.stringify(blockers.slice(0, 6)).slice(0, 900)}`);
let formal = byTestIdPrefix("rev-quick-formal-");
note(`FORMAL_KEYS ${await formal.count()} t=${elapsed()}`);
if (!(await formal.count()) && cardCount) {
  // The cards carry their own fact-refresh door; use it on the first card the provider can name.
  const details = page.locator("details.rev-quick-place-blocker");
  note(`FACTS_DETAILS ${await details.count()} t=${elapsed()}`);
  for (let i = 0; i < Math.min(3, await details.count()); i += 1) {
    await details.nth(i).evaluate((node) => { node.open = true; }).catch(() => undefined);
  }
  const factKeys = byTestIdPrefix("rev-quick-facts-");
  note(`FACTS_KEYS ${await factKeys.count()} t=${elapsed()}`);
  for (let i = 0; i < Math.min(2, await factKeys.count()); i += 1) {
    await pressNear(factKeys.nth(i), `facts-${i}`);
    for (let k = 0; k < 20 && (await byTestIdPrefix("rev-quick-formal-").count()) === 0; k += 1) await page.waitForTimeout(2000);
    if ((await byTestIdPrefix("rev-quick-formal-").count()) > 0) break;
  }
  formal = byTestIdPrefix("rev-quick-formal-");
  note(`FORMAL_AFTER_FACTS ${await formal.count()} t=${elapsed()}`);
  await survey("EXPLORE_CARDS_FINAL");
}

// Step 4 — take the formal door, then read what the plan screen says.
const quickAlert = async () => (await page.locator(".rev-quick-alert").allInnerTexts().catch(() => [])).join(" ").slice(0, 400);
if (await formal.count()) {
  const pressed = await pressNear(formal, "formal-select", 20000);
  note(`FORMAL_PRESSED ${pressed} t=${elapsed()}`);
  await page.waitForTimeout(6000);
  note(`FORMAL_ALERT ${JSON.stringify(await quickAlert())}`);
  note(`FORMAL_BODY ${JSON.stringify((await bodyText()).replace(/\s+/g, " ").slice(0, 600))} t=${elapsed()}`);
  await shot(`${TAG}-x-after-formal`);
} else {
  note(`NO_FORMAL_DOOR cards=${cardCount} alert=${JSON.stringify(await quickAlert())} t=${elapsed()}`);
  await shot(`${TAG}-x-no-formal-door`);
}

// leg 2: the explore screen is not where the departure door lives, so take the traveller's own tab
// back to the journey before reading whether a select or a start key exists.
for (const name of [/^行程$/, /我的旅程/, /^日程$/]) {
  const tab = page.getByRole("button", { name });
  if ((await tab.count()) && (await pressNear(tab.first(), "back-to-journey"))) break;
}
await page.waitForTimeout(4000);
note(`BACK_ON_PLAN explore=${await byTestId("rev-quick-explore").count()} start=${await page.locator('[data-testid="rev-plan-start"]').count()} select=${await page.locator('[data-testid="rev-plan-select"]').count()} t=${elapsed()}`);
const planGaps = await page.locator(".rev-plan-gap").allInnerTexts().catch(() => []);
note(`X_PLAN_GAPS ${JSON.stringify(planGaps).slice(0, 800)} t=${elapsed()}`);
const xSelect = page.locator('[data-testid="rev-plan-select"]');
const xStart = page.locator('[data-testid="rev-plan-start"]');
const xSelectState = (await xSelect.count()) ? await xSelect.first().isEnabled().catch(() => false) : false;
note(`X_SELECT ${await xSelect.count()} enabled=${xSelectState} X_START ${await xStart.count()} t=${elapsed()}`);
await survey("PLAN_AFTER_FORMAL");
if ((await xSelect.count()) || (await xStart.count())) {
  await pressNear(xSelect, "select-final", 30000);
  await page.waitForTimeout(6000);
  const refusal = await page.locator(".rev-plan-message, [role='alert']").allInnerTexts().catch(() => []);
  note(`X_SELECT_REFUSAL ${JSON.stringify(refusal.slice(0, 2)).slice(0, 700)} t=${elapsed()}`);
  await shot(`${TAG}-x-after-select`);
  const readyStart = (await xStart.count()) ? await xStart.first().isEnabled().catch(() => false) : false;
  note(`X_START_READY ${await xStart.count()} enabled=${readyStart} t=${elapsed()}`);
  if (readyStart) {
    await pressNear(xStart, "start-journey", 40000);
    for (let i = 0; i < 40; i += 1) {
      const txt = await bodyText();
      if (/正在使用|旅程已开始|下一站/.test(txt)) break;
      await page.waitForTimeout(3000);
    }
    await page.waitForTimeout(4000);
    note(`X_ACTIVE_BODY ${JSON.stringify((await bodyText()).replace(/\s+/g, " ").slice(0, 700))} t=${elapsed()}`);
    await shot(`${TAG}-x-active`);
    const activityCount = await page.locator('[data-testid="rev-activity-row"], .rev-activity').count().catch(() => 0);
    note(`X_ACTIVITY_ROWS ${activityCount} t=${elapsed()}`);
    // The map arm of the same journey: the plan's stops must be on it, and their number must be the
    // schedule's number.
    await pressNear(page.getByRole("button", { name: /^地图$/ }), "map-layer", 20000);
    await page.waitForTimeout(4000);
    note(`X_MAP_COUNT_LINE ${JSON.stringify(await page.evaluate(() => (document.body.innerText.match(/地图地点 \d+ 处 · 高德地点 \d+ 处/) || [null])[0]))} t=${elapsed()}`);
    note(`X_MAP_PLANNED_TAGS ${await page.locator('[data-testid="rev-map-planned-stop"]').count()}`);
    note(`X_MAP_LIST_ITEMS ${await page.locator('ol[aria-label="地图地点"] li').count()}`);
    await shot(`${TAG}-x-map`);
  }
}
note(`X_END alert=${JSON.stringify(await quickAlert())} errors=${JSON.stringify(errors.slice(0, 3))} t=${elapsed()}`);
await ctx.close();
