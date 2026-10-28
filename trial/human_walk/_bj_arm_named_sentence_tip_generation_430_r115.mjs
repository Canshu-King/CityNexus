import { chromium } from "file:///D:/moodle/_cmdr_rescue_v3_1022/frontend/node_modules/playwright/index.mjs";
import fs from "node:fs";

// Two things this arm is meant to settle on the live screen, in one traveller-shaped path:
//   (a) the sentence a traveller reads when the city door refuses 「保存为正式候选方案」.  bf110 read
//       「这次未能保存，时间仍留在这里，可以重试。」 while the answer was 409 PLACE_NOT_IN_JOURNEY_CITY.  The
//       replacement ships in two arms: a named row (needs the backend that attaches details) and, when the
//       door only carries the code, placeCityRefusalSentence(null).  The running backend on :60362 is the
//       older generation -- it still answers details=null -- so this arm measures the second arm honestly,
//       and the refusal is printed verbatim rather than summarised.
//   (b) blocker 5's original question: after a refusal there is no reachable "apply this version" key.
//       If the promote succeeds (201) instead of refusing, the arm keeps walking the real chain: freeze and
//       read the measured shortfalls back, press rev-v3-replan, then rev-v3-replan-apply.
// Either outcome is a reading; neither is assumed.
// Isolated canary stack: vite :14462 / backend :60362 from E:/_cmdr_clean_1028 (tip ea51658c9a) with two
// frontend files carried forward to this generation for the measurement -- departureGaps.ts and
// DraftDepartureCard.tsx, copied at 18:33 and restored afterwards; the backend stays on its own generation.
// No seeded storage, no direct API calls, no DOM injection: every request below answers a real press.
const DIR = "D:/moodle/_cmdr_rescue_v3_1022/trial/results/20261026_gozero";
const OUT = `${DIR}/bj115-named-sentence-tip-generation-430.txt`;
const NL = String.fromCharCode(10);
const lines = [];
const note = (v) => { lines.push(v); fs.writeFileSync(OUT, lines.join(NL) + NL, "utf8"); };
const started = Date.now();
const elapsed = () => ((Date.now() - started) / 1000).toFixed(1);
const UUID = /[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}/i;
const SENTENCE_RX = /(这版安排里有一处地点记在另一座城市的清单上|对上的地点.*记在另一座城市的清单上|这次未能保存，时间仍留在这里，可以重试|这一版没能保存，原来的时间还在这里|已保存 \d+ 项正式安排)/;

async function launchAny(candidates) {
  const tried = [];
  for (const dir of candidates) {
    try {
      const box = await chromium.launchPersistentContext(dir, {
        channel: "chrome", headless: false, viewport: { width: 430, height: 932 }, deviceScaleFactor: 1,
      });
      note(`PROFILE_USED ${dir.split("/").pop()} after ${tried.length} failed`);
      return box;
    } catch (error) {
      const why = String(error).replace(/\s+/g, " ").slice(0, 120);
      tried.push(why);
      note(`PROFILE_LOCKED ${dir.split("/").pop()} ${why}`);
    }
  }
  note("ABORT no launchable profile " + JSON.stringify(tried));
  process.exit(9);
}
const ctx = await launchAny([
  "D:/moodle/_cmdr_v3_live_1022/_chrome_gozero_bj115",
  "D:/moodle/_cmdr_v3_live_1022/_chrome_gozero_bj115b",
]);
const page = ctx.pages()[0] ?? await ctx.newPage();
page.on("response", async (resp) => {
  const url = resp.url(); const method = resp.request().method();
  if (!url.includes("/api/v1/") || (method !== "POST" && method !== "PUT")) return;
  if (!/goal-tasks|plans|journeys|departure|routes|gaps/.test(url)) return;
  const line = `HTTP ${method} ${resp.status()} ${url.replace(/^http:\/\/[^/]+/, "")}`;
  if (resp.status() >= 400) {
    let d = ""; try { d = JSON.stringify(await resp.json()).slice(0, 600); } catch { d = "(unreadable)"; }
    note(line + " BODY " + d);
  } else note(line);
});
page.on("pageerror", (e) => note("PAGEERROR " + String(e).slice(0, 160)));

const IDS = ["rev-v3-travel-gaps", "rev-v3-replan", "rev-v3-replan-diff", "rev-v3-replan-apply",
  "rev-v3-replan-reverify", "rev-v3-replan-refusal", "rev-v3-gap-shortfall"];
const census = () => page.evaluate((ids) => {
  const out = ids.map((id) => {
    const nodes = Array.from(document.querySelectorAll(`[data-testid="${id}"]`));
    const node = nodes[0];
    if (!node) return { id, count: 0 };
    const b = node.getBoundingClientRect();
    const top = b.width && b.height ? document.elementFromPoint(b.left + b.width / 2, b.top + b.height / 2) : null;
    return { id, count: nodes.length,
      visible: b.width > 0 && b.height > 0,
      disabled: "disabled" in node ? Boolean(node.disabled) : null,
      box: `${Math.round(b.width)}x${Math.round(b.height)}@${Math.round(b.top)}`,
      hitSelf: Boolean(top) && (node === top || node.contains(top) || top.contains(node)),
      label: (node.innerText || "").replace(/\s+/g, " ").trim().slice(0, 40) };
  });
  const body = document.body.innerText || "";
  const texts = Array.from(document.querySelectorAll("button")).map((b) => (b.innerText || "").replace(/\s+/g, " ").trim());
  const sentence = (body.match(/[^。\n]*(记在另一座城市的清单上|可以重试|原来的时间还在这里|已保存 \d+ 项正式安排)[^。\n]*[。]?/) || [null])[0];
  return { keys: out,
    sentence: sentence ? sentence.replace(/\s+/g, " ").trim().slice(0, 120) : null,
    freeze_label: texts.find((t) => /核实并冻结今天的转场|重新核实转场|正在核实转场/.test(t)) ?? null,
    promote_label: texts.find((t) => /保存为正式候选方案|按以上时间重新准备方案|正在保存安排/.test(t)) ?? null,
    stateLine: (body.match(/[^\n]*(正在研究|已整理 \d+ 天|当前展示的是已保存版本)[^\n]*/) || [null])[0]?.replace(/\s+/g, " ").slice(0, 50) ?? null };
}, IDS);
const report = (tag, c) => {
  note(`${tag} state=${JSON.stringify(c.stateLine)} sentence=${JSON.stringify(c.sentence)}`);
  note(`${tag} freeze=${JSON.stringify(c.freeze_label)} promote=${JSON.stringify(c.promote_label)}`);
  for (const k of c.keys) note(`${tag} KEY ${JSON.stringify(k)}`);
};
async function leak(tag) {
  const band = await page.locator(".rev-plan-message, [role='alert'], [role='status']").allInnerTexts().catch(() => []);
  const body = await page.evaluate(() => document.body.innerText || "").catch(() => "");
  const joined = band.join(" | ");
  note(`${tag} TEXTS ${JSON.stringify(band.slice(0, 6))}`);
  note(`${tag} LEAK api_in_body=${body.includes("CityNexus API")} api_in_band=${joined.includes("CityNexus API")} uuid_in_band=${UUID.test(joined)}`);
}
async function tap(locator, label, timeout = 9000) {
  const target = locator.first();
  try { await target.waitFor({ state: "visible", timeout }); } catch { note(`MISS ${label}`); return false; }
  await target.evaluate((n) => n.scrollIntoView({ block: "center" })).catch(() => {});
  await page.waitForTimeout(300);
  const hit = await target.evaluate((n) => {
    const b = n.getBoundingClientRect();
    if (!b.width || !b.height) return false;
    const top = document.elementFromPoint(b.left + b.width / 2, b.top + b.height / 2);
    return Boolean(top) && (n === top || n.contains(top)) && !n.disabled;
  }).catch(() => false);
  note(`HIT ${label} ${hit} t=${elapsed()}`);
  if (!hit) return false;
  await target.click({ timeout: 15000 }).catch(() => {});
  await page.waitForTimeout(1200);
  return true;
}

await page.goto("http://127.0.0.1:14464/revolution", { waitUntil: "domcontentloaded", timeout: 60000 });
await page.waitForTimeout(7000);
await page.getByRole("textbox", { name: /想怎么玩/ }).first()
  .fill("2026 年 12 月 3 日到 4 日在北京玩两天，两个人，每段步行不超过 200 米，太远坐地铁");
await page.waitForTimeout(600);
await page.getByRole("button", { name: /继续规划/ }).first().click().catch(() => note("CONTINUE_MISS"));
await page.waitForTimeout(2500);
await page.getByRole("button", { name: "对话", exact: true }).first().click().catch(() => note("CHAT_MISS"));
await page.waitForTimeout(1200);
await page.getByRole("button", { name: /对话设置/ }).first().click().catch(() => {});
await page.waitForTimeout(800);
for (const label of [/本次允许 AI 处理旅行目标/, /本次允许查询公开地图和地点来源/]) {
  const box = page.getByRole("checkbox", { name: label }).first();
  if (await box.count() && !(await box.isChecked())) await box.check().catch(() => {});
}
await page.getByRole("button", { name: /关闭对话设置/ }).first().click().catch(() => {});
await page.waitForTimeout(400);
await page.getByRole("button", { name: /发送/ }).first().click().catch(() => note("SEND_MISS"));
note(`SENT t=${elapsed()}`);

const skipEnd = Date.now() + 5 * 60 * 1000;
while (Date.now() < skipEnd) {
  const s = page.locator('[data-testid="rev-agent-skip-questions"]');
  if (await s.count()) { await s.first().click().catch(() => {}); note(`SKIP t=${elapsed()}`); break; }
  await page.waitForTimeout(3000);
}
let ready = false;
const draftEnd = Date.now() + 11 * 60 * 1000;
let tick = 0;
while (Date.now() < draftEnd) {
  const c = await census();
  tick += 1;
  if (tick % 3 === 1) note(`DRAFT_WAIT ${tick} state=${JSON.stringify(c.stateLine)} t=${elapsed()}`);
  if (/已整理 \d+ 天|当前展示的是已保存版本/.test(c.stateLine || "")) { ready = true; note(`DRAFT_READY ${JSON.stringify(c.stateLine)} t=${elapsed()}`); break; }
  await page.waitForTimeout(6000);
}
if (!ready) note(`NO_DRAFT t=${elapsed()}`);

await tap(page.locator('[data-testid="rev-mobile-tab-trips"]'), "trips-tab", 10000);
await page.waitForTimeout(2000);
const cards = page.locator("article, [data-testid*='trip-card'], [data-testid*='journey'], li button");
const n = await cards.count().catch(() => 0);
note("CARDS " + n);
for (let k = 0; k < Math.min(n, 8); k += 1) {
  if (await tap(cards.nth(k), `card-${k}`, 7000)) {
    await page.waitForTimeout(3500);
    const c = await census();
    if (c.promote_label || c.keys.some((x) => x.count > 0)) { report(`IN_CARD_${k}`, c); break; }
  }
}
await tap(page.locator('[data-testid="rev-mission-layer-timeline"]'), "layer-timeline", 9000);
await page.waitForTimeout(3000);
let c = await census();
report("ON_TIMELINE", c);
await page.screenshot({ path: `${DIR}/430-bj115-on-timeline.png` }).catch(() => {});

const confirm = page.getByRole("checkbox", { name: /按以上时间准备方案/ });
const found = await confirm.count().catch(() => 0);
if (found) {
  const before = await confirm.first().isChecked().catch(() => null);
  if (before === false) await confirm.first().check({ force: true }).catch((e) => note("CHECK_ERR " + String(e).slice(0, 60)));
  await page.waitForTimeout(2200);
  note(`CONFIRMED ${await confirm.first().isChecked().catch(() => null)} was=${before} t=${elapsed()}`);
} else note("CONFIRM_KEY found=0");

c = await census();
if (!c.promote_label) {
  // The card without a prepared draft offers no promote key at all; record the shape rather than pretend.
  report("NO_PROMOTE_KEY", c);
  await page.screenshot({ path: `${DIR}/430-bj115-no-promote.png` }).catch(() => {});
  note("DONE no promote key t=" + elapsed());
  await ctx.close();
  process.exit(7);
}
const promoted = await tap(page.getByRole("button", { name: /保存为正式候选方案|按以上时间重新准备方案|正在保存安排/ }), "promote", 20000);
note(`PROMOTE_PRESSED ${promoted} t=${elapsed()}`);
await page.waitForTimeout(15000);
c = await census();
report("AFTER_PROMOTE", c);
await leak("AFTER_PROMOTE");
await page.screenshot({ path: `${DIR}/430-bj115-after-promote.png` }).catch(() => {});
const refused = SENTENCE_RX.test(c.sentence || "") && /记在另一座城市的清单上|可以重试/.test(c.sentence || "");
note(`SENTENCE_KIND refused=${refused} verbatim=${JSON.stringify(c.sentence)} t=${elapsed()}`);

// If the promote went through, keep walking to the accept key blocker 5 asked about.
if (!refused) {
  const pressedFreeze = await tap(page.getByRole("button", { name: /核实并冻结今天的转场|重新核实转场/ }), "freeze-routes", 12000);
  note(`FREEZE_PRESSED ${pressedFreeze} t=${elapsed()}`);
  if (pressedFreeze) {
    const end = Date.now() + 150 * 1000;
    let f = 0;
    while (Date.now() < end) {
      c = await census();
      const block = c.keys.find((k) => k.id === "rev-v3-travel-gaps") || { count: 0 };
      const busy = (c.freeze_label || "").includes("正在核实");
      f += 1;
      note(`FREEZE_WAIT ${f} busy=${busy} gaps=${block.count} t=${elapsed()}`);
      if (!busy && (block.count > 0 || f > 8)) break;
      await page.waitForTimeout(5000);
    }
  }
  report("AFTER_FREEZE", c);
  await page.screenshot({ path: `${DIR}/430-bj115-after-freeze.png` }).catch(() => {});
  await leak("AFTER_FREEZE");
  c = await census();
  const plan = c.keys.find((k) => k.id === "rev-v3-replan") || { count: 0 };
  const reverify = c.keys.find((k) => k.id === "rev-v3-replan-reverify") || { count: 0 };
  const refusalLine = c.keys.find((k) => k.id === "rev-v3-replan-refusal") || { count: 0 };
  note(`REPLAN_DOOR replan=${plan.count} hit=${plan.hitSelf ?? false} box=${plan.box ?? null} reverify=${reverify.count} refusal_line=${JSON.stringify(refusalLine.label ?? null)} t=${elapsed()}`);
  if (plan.count && await tap(page.locator('[data-testid="rev-v3-replan"]'), "rev-v3-replan", 10000)) {
    await page.waitForTimeout(2500);
    c = await census();
    report("AFTER_REPLAN", c);
    await page.screenshot({ path: `${DIR}/430-bj115-after-replan.png` }).catch(() => {});
    const apply = c.keys.find((k) => k.id === "rev-v3-replan-apply") || { count: 0 };
    note(`APPLY_DOOR count=${apply.count} visible=${apply.visible ?? false} hit=${apply.hitSelf ?? false} disabled=${apply.disabled ?? null} box=${apply.box ?? null} label=${JSON.stringify(apply.label ?? null)} t=${elapsed()}`);
    if (apply.count && await tap(page.locator('[data-testid="rev-v3-replan-apply"]'), "rev-v3-replan-apply", 15000)) {
      await page.waitForTimeout(16000);
      c = await census();
      report("AFTER_APPLY", c);
      await leak("AFTER_APPLY");
      await page.screenshot({ path: `${DIR}/430-bj115-after-apply.png` }).catch(() => {});
      note("ACCEPT_KEY_WALKED true t=" + elapsed());
    }
  }
}
const body = await page.evaluate(() => document.body.innerText || "");
note("FINAL_CLEAN " + !body.includes("CityNexus API"));
note("DONE t=" + elapsed());
await ctx.close();
