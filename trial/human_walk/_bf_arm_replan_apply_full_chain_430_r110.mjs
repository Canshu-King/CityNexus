import { chromium } from "file:///D:/moodle/_cmdr_rescue_v3_1022/frontend/node_modules/playwright/index.mjs";
import fs from "node:fs";

// be109 answered nothing about the traveller: it entered a journey whose agent round had just started, so
// the departure card had no draft to hold, and it never pressed the promote key that puts 「核实并冻结今天的
// 转场」 on the screen at all (DraftDepartureCard.tsx:340 renders that button only once `result` exists).
// It also lied in one field: freeze_label was built with Array.find(<RegExp>) -- a RegExp is truthy, so
// find returned the first button on the page instead of the freeze button.  Both fixed here.
// The full chain blocker 5 asks about, one press per link:
//   tick 按以上时间准备方案  ->  press 保存为正式候选方案 (prepare-plan)  ->  result exists
//   press 核实并冻结今天的转场 (freezeGoalRoutes :225, then travelGaps :235)  ->  gaps card :348
//   press rev-v3-replan (:355)  ->  planShown  ->  rev-v3-replan-apply (:357, 「按这一版安排」)
// Isolated canary stack: vite :14462 / backend :60362 on the zero-dirty worktree E:/_cmdr_clean_1028
// (generation ea51658c9a, git status 0 lines), its own SQLite.  Nothing seeded, no localStorage, no DOM
// injection -- every request below is the answer to a real press.
const DIR = "D:/moodle/_cmdr_rescue_v3_1022/trial/results/20261026_gozero";
const OUT = `${DIR}/bf110-replan-apply-full-chain-430-r4.txt`;
const NL = String.fromCharCode(10);
const lines = [];
const note = (v) => { lines.push(v); fs.writeFileSync(OUT, lines.join(NL) + NL, "utf8"); };
const started = Date.now();
const elapsed = () => ((Date.now() - started) / 1000).toFixed(1);
const UUID = /[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}/i;

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
  "D:/moodle/_cmdr_v3_live_1022/_chrome_gozero_bf110",
  "D:/moodle/_cmdr_v3_live_1022/_chrome_gozero_bf110b",
]);
const page = ctx.pages()[0] ?? await ctx.newPage();
page.on("response", async (resp) => {
  const url = resp.url(); const method = resp.request().method();
  if (!url.includes("/api/v1/") || (method !== "POST" && method !== "PUT")) return;
  if (!/goal-tasks|plans|journeys|departure|routes|gaps/.test(url)) return;
  const line = `HTTP ${method} ${resp.status()} ${url.replace(/^http:\/\/[^/]+/, "")}`;
  if (resp.status() >= 400) {
    let d = ""; try { d = JSON.stringify(await resp.json()).slice(0, 700); } catch { d = "(unreadable)"; }
    note(line + " BODY " + d);
  } else note(line);
});
page.on("pageerror", (e) => note("PAGEERROR " + String(e).slice(0, 160)));

const IDS = ["rev-v3-travel-gaps", "rev-v3-gap-shortfalls", "rev-v3-gap-shortfall", "rev-v3-replan-refusal",
  "rev-v3-replan", "rev-v3-replan-diff", "rev-v3-replan-apply", "rev-v3-replan-reverify"];
const FREEZE_RX = /核实并冻结今天的转场|重新核实转场|正在核实转场/;
const census = () => page.evaluate(({ ids, freezeSource }) => {
  const rx = new RegExp(freezeSource);
  const out = ids.map((id) => {
    const nodes = Array.from(document.querySelectorAll(`[data-testid="${id}"]`));
    const node = nodes[0];
    if (!node) return { id, count: 0 };
    const b = node.getBoundingClientRect();
    const cs = getComputedStyle(node);
    const top = b.width && b.height ? document.elementFromPoint(b.left + b.width / 2, b.top + b.height / 2) : null;
    return {
      id, count: nodes.length,
      visible: b.width > 0 && b.height > 0 && cs.visibility === "visible" && Number(cs.opacity) > 0,
      disabled: "disabled" in node ? Boolean(node.disabled) : null,
      box: `${Math.round(b.width)}x${Math.round(b.height)}@${Math.round(b.top)}`,
      hitSelf: Boolean(top) && (node === top || node.contains(top) || top.contains(node)),
      label: (node.innerText || node.getAttribute("aria-label") || "").replace(/\s+/g, " ").trim().slice(0, 34),
    };
  });
  const texts = Array.from(document.querySelectorAll("button")).map((b) => (b.innerText || "").replace(/\s+/g, " ").trim());
  const body = document.body.innerText || "";
  return {
    keys: out,
    // .find with a RegExp argument is always truthy; find the label with an explicit test instead.
    freeze_label: texts.find((t) => rx.test(t)) ?? null,
    promote_label: texts.find((t) => /保存为正式候选方案|按以上时间重新准备方案|正在保存安排/.test(t)) ?? null,
    stateLine: (body.match(/[^\n]*(当前展示的是已保存版本|已保存 \d+ 项正式安排|等这一轮结束|正在研究|已整理|行程草案)[^\n]*/) || [null])[0]?.replace(/\s+/g, " ").slice(0, 60) ?? null,
  };
}, { ids: IDS, freezeSource: FREEZE_RX.source });
const report = (tag, c) => {
  note(`${tag} state=${JSON.stringify(c.stateLine)} freeze=${JSON.stringify(c.freeze_label)} promote=${JSON.stringify(c.promote_label)}`);
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

await page.goto("http://127.0.0.1:14462/revolution", { waitUntil: "domcontentloaded", timeout: 60000 });
await page.waitForTimeout(7000);
// SKIP_SENTENCE=1 re-enters a journey this arm already created instead of starting another round.
const SKIP_SENTENCE = process.env.SKIP_SENTENCE === "1";
note(`SKIP_SENTENCE ${SKIP_SENTENCE} t=${elapsed()}`);
if (!SKIP_SENTENCE) {
  await page.getByRole("textbox", { name: /想怎么玩/ }).first()
    .fill("2026 年 12 月 3 日到 4 日在北京玩两天，两个人，每段步行不超过 1 公里，太远坐地铁");
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

  // Wait for the draft the way bd106 proved it: the round has to finish before the card holds anything.
  const skipEnd = Date.now() + 6 * 60 * 1000;
  while (Date.now() < skipEnd) {
    const s = page.locator('[data-testid="rev-agent-skip-questions"]');
    if (await s.count()) { await s.first().click().catch(() => {}); note(`SKIP t=${elapsed()}`); break; }
    await page.waitForTimeout(3000);
  }
  let draft = false;
  const draftEnd = Date.now() + 12 * 60 * 1000;
  let tick = 0;
  while (Date.now() < draftEnd) {
    const c = await census();
    tick += 1;
    if (tick % 3 === 1) note(`DRAFT_WAIT ${tick} state=${JSON.stringify(c.stateLine)} promote=${JSON.stringify(c.promote_label)} t=${elapsed()}`);
    if (/已整理 \d+ 天|行程草案|当前展示的是已保存版本/.test(c.stateLine || "")) {
      draft = true; note(`DRAFT_READY ${JSON.stringify(c.stateLine)} promote=${JSON.stringify(c.promote_label)} t=${elapsed()}`);
      break;
    }
    await page.waitForTimeout(6000);
  }
  if (!draft) note(`NO_DRAFT t=${elapsed()} ${JSON.stringify(await census())}`);
}

// Enter the trip, because the card lives in the journey cockpit, not on the trial screen.
await tap(page.locator('[data-testid="rev-mobile-bottom-nav"]'), "bottom-nav", 4000);
await tap(page.locator('[data-testid="rev-mobile-tab-trips"]'), "trips-tab", 10000);
await page.waitForTimeout(2000);
const cards = page.locator("article, [data-testid*='trip-card'], [data-testid*='journey'], li button");
const n = await cards.count().catch(() => 0);
note("CARDS " + n);
let inCard = false;
for (let k = 0; k < Math.min(n, 6); k += 1) {
  if (await tap(cards.nth(k), `card-${k}`, 7000)) {
    await page.waitForTimeout(4000);
    let c = await census();
    report(`IN_CARD_${k}`, c);
    if (c.promote_label || c.keys.some((x) => x.count > 0)) { inCard = true; break; }
  }
}
await tap(page.locator('[data-testid="rev-mission-layer-timeline"]'), "layer-timeline", 9000);
await page.waitForTimeout(3000);
let c = await census();
report("ON_TIMELINE", c);
await page.screenshot({ path: `${DIR}/430-bf110-on-timeline.png` }).catch(() => {});
if (!c.promote_label) {
  note(`ABORT no promote key inside the journey (entered=${inCard}) -- the chain cannot be walked from here`);
  await ctx.close();
  process.exit(6);
}

// Link 0: tick the traveller's own confirmation, then press the promote key.  bc105/bd106 measured that
// the key is disabled={!confirmed} -- nine arms before that pressed an unticked checkbox's button.
const confirm = page.getByRole("checkbox", { name: /按以上时间准备方案/ });
const found = await confirm.count().catch(() => 0);
note(`CONFIRM_KEY found=${found} t=${elapsed()}`);
if (found) {
  const before = await confirm.first().isChecked().catch(() => null);
  if (before === false) await confirm.first().check({ force: true }).catch((e) => note("CHECK_ERR " + String(e).slice(0, 70)));
  await page.waitForTimeout(2500);
  note(`CONFIRMED ${await confirm.first().isChecked().catch(() => null)} was=${before} t=${elapsed()}`);
}
if (await tap(page.getByRole("button", { name: /保存为正式候选方案|按以上时间重新准备方案|正在保存安排…/ }), "promote", 20000)) {
  await page.waitForTimeout(16000);
  c = await census();
  report("AFTER_PROMOTE", c);
  await leak("AFTER_PROMOTE");
  await page.screenshot({ path: `${DIR}/430-bf110-after-promote.png` }).catch(() => {});
}

// Link 1: freeze + read the measured shortfalls back.
const freeze = page.getByRole("button", { name: /核实并冻结今天的转场|重新核实转场/ });
const pressedFreeze = await tap(freeze, "freeze-routes", 12000);
note(`FREEZE_PRESSED ${pressedFreeze} t=${elapsed()}`);
if (pressedFreeze) {
  const end = Date.now() + 120 * 1000;
  let f = 0;
  while (Date.now() < end) {
    c = await census();
    const block = c.keys.find((k) => k.id === "rev-v3-travel-gaps") || { count: 0 };
    const busy = (c.freeze_label || "").includes("正在核实");
    f += 1;
    note(`FREEZE_WAIT ${f} busy=${busy} gaps=${block.count} t=${elapsed()}`);
    if (!busy && block.count > 0) break;
    if (!busy && f > 6) break;
    await page.waitForTimeout(4000);
  }
}
report("AFTER_FREEZE", c);
await page.screenshot({ path: `${DIR}/430-bf110-after-freeze.png` }).catch(() => {});
await leak("AFTER_FREEZE");

// Links 2 and 3: does the traveller get a reachable key that applies the re-planned version?
c = await census();
const plan = c.keys.find((k) => k.id === "rev-v3-replan") || { count: 0 };
const reverify = c.keys.find((k) => k.id === "rev-v3-replan-reverify") || { count: 0 };
note(`REPLAN_DOOR replan=${plan.count} hit=${plan.hitSelf ?? false} box=${plan.box ?? null} reverify=${reverify.count} t=${elapsed()}`);
if (plan.count) {
  if (await tap(page.locator('[data-testid="rev-v3-replan"]'), "rev-v3-replan", 10000)) {
    await page.waitForTimeout(2500);
    c = await census();
    report("AFTER_REPLAN", c);
    await page.screenshot({ path: `${DIR}/430-bf110-after-replan.png` }).catch(() => {});
    const apply = c.keys.find((k) => k.id === "rev-v3-replan-apply") || { count: 0 };
    note(`APPLY_DOOR count=${apply.count} visible=${apply.visible ?? false} hit=${apply.hitSelf ?? false} `
      + `disabled=${apply.disabled ?? null} box=${apply.box ?? null} label=${JSON.stringify(apply.label ?? null)} t=${elapsed()}`);
    if (apply.count) {
      const pressed = await tap(page.locator('[data-testid="rev-v3-replan-apply"]'), "rev-v3-replan-apply", 15000);
      note(`APPLY_PRESSED ${pressed} t=${elapsed()}`);
      await page.waitForTimeout(16000);
      await leak("AFTER_APPLY");
      c = await census();
      report("AFTER_APPLY", c);
      await page.screenshot({ path: `${DIR}/430-bf110-after-apply.png` }).catch(() => {});
    }
  }
} else if (reverify.count) {
  const sentence = await page.locator('[data-testid="rev-v3-replan-refusal"]').first().innerText().catch(() => null);
  note(`NO_ROWS refusal_sentence=${JSON.stringify((sentence || "").replace(/\s+/g, " ").slice(0, 110))}`);
  if (await tap(page.locator('[data-testid="rev-v3-replan-reverify"]'), "rev-v3-replan-reverify", 10000)) {
    await page.waitForTimeout(20000);
    c = await census();
    report("AFTER_REVERIFY", c);
    await page.screenshot({ path: `${DIR}/430-bf110-after-reverify.png` }).catch(() => {});
  }
} else {
  note(`NO_DOOR gaps_block=${JSON.stringify(c.keys.find((k) => k.id === "rev-v3-travel-gaps") ?? null)} t=${elapsed()}`);
  await page.screenshot({ path: `${DIR}/430-bf110-no-door.png` }).catch(() => {});
}
const body = await page.evaluate(() => document.body.innerText || "");
note("FINAL_HAS_SAVED_AGAIN " + /已保存\s*\d+\s*项正式安排/.test(body));
note("FINAL_CLEAN " + !body.includes("CityNexus API"));
note("DONE t=" + elapsed());
await ctx.close();
