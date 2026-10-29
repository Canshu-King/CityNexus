import { chromium } from "file:///D:/moodle/_cmdr_rescue_v3_1022/frontend/node_modules/playwright/index.mjs";
import fs from "node:fs";

// Blocker 5 of the delivery doc still says: after the departure gate refuses a version, the traveller has
// no reachable "apply this version" key.  The source says otherwise and gives an exact chain -- press
// 「核实并冻结今天的转场」 (DraftDepartureCard.tsx:218 verifyRoutes) which freezes hops and then reads the
// measured shortfalls back (travelGaps at :235), which mounts the gaps card (:348), which holds
// rev-v3-replan (:355) whose press sets planShown and mounts rev-v3-replan-apply (:357, label
// 「按这一版安排」 from departureGaps.ts:488).  Nobody has walked that chain on the clean generation, so the
// blocker is an untested claim about the traveller, not a measured fact.  This arm presses every link and
// reports what each one actually does.
// Isolated canary stack: vite :14462 / backend :60362 on the zero-dirty worktree E:/_cmdr_clean_1028 with
// its own SQLite.  Nothing is seeded, no localStorage, no DOM injection: every request below is the answer
// to a real press.
const DIR = "D:/moodle/_cmdr_rescue_v3_1022/trial/results/20261026_gozero";
const OUT = `${DIR}/be109-replan-apply-chain-430.txt`;
const NL = String.fromCharCode(10);
const lines = [];
const note = (v) => { lines.push(v); fs.writeFileSync(OUT, lines.join(NL) + NL, "utf8"); };
const started = Date.now();
const elapsed = () => ((Date.now() - started) / 1000).toFixed(1);
const UUID = /[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}/i;

// The first profile is tried, and if another arm still holds its lock the arm says so and moves to a
// second one instead of dying the way bb104 died silently on _chrome_gozero_az102.
async function launchAny(candidates) {
  const tried = [];
  for (const dir of candidates) {
    try {
      const box = await chromium.launchPersistentContext(dir, {
        channel: "chrome", headless: false, viewport: { width: 430, height: 932 }, deviceScaleFactor: 1,
      });
      note(`PROFILE_USED ${dir.split("/").pop()} after ${tried.length} failed`);
      return { box, tried };
    } catch (error) {
      const why = String(error).replace(/\s+/g, " ").slice(0, 120);
      tried.push(why);
      note(`PROFILE_LOCKED ${dir.split("/").pop()} ${why}`);
    }
  }
  note("ABORT no launchable profile " + JSON.stringify(tried));
  process.exit(9);
}
const BASE_PROFILES = [
  "D:/moodle/_cmdr_v3_live_1022/_chrome_gozero_be109",
  "D:/moodle/_cmdr_v3_live_1022/_chrome_gozero_be109b",
];
const { box: ctx } = await launchAny(BASE_PROFILES);
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
// One evaluate, one tick: every key's mount state, geometry, disabled flag and whether a tap at its
// centre would land on it rather than on the chat dock.
const census = () => page.evaluate((ids) => {
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
  const body = document.body.innerText || "";
  return {
    url: location.pathname, keys: out,
    stateLine: (body.match(/[^\n]*(当前展示的是已保存版本|已保存 \d+ 项正式安排|等这一轮结束|正在研究)[^\n]*/) || [null])[0]?.replace(/\s+/g, " ").slice(0, 60) ?? null,
    freeze_label: (Array.from(document.querySelectorAll("button")).map((b) => (b.innerText || "").trim())
      .find((t) => /核实并冻结今天的转场|重新核实转场|正在核实转场/) || null),
  };
}, IDS);
const report = (tag, c) => {
  note(`${tag} state=${JSON.stringify(c.stateLine)} freeze=${JSON.stringify(c.freeze_label)}`);
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

// Leave the trial screen and enter the trip: the departure card lives inside the journey cockpit (bc105
// and bd106 established that; nine earlier arms never got there).
await tap(page.locator('[data-testid="rev-mobile-tab-trips"]'), "trips-tab", 10000);
await page.waitForTimeout(2000);
const cards = page.locator("article, [data-testid*='trip-card'], [data-testid*='journey'], li button");
const n = await cards.count().catch(() => 0);
note("CARDS " + n);
let entered = false;
for (let k = 0; k < Math.min(n, 6); k += 1) {
  if (await tap(cards.nth(k), `card-${k}`, 7000)) {
    await page.waitForTimeout(4000);
    const c = await census();
    report(`IN_CARD_${k}`, c);
    entered = true;
    break;
  }
}
if (!entered) { note("ABORT could not enter any trip card"); await ctx.close(); process.exit(6); }
await tap(page.locator('[data-testid="rev-mission-layer-timeline"]'), "layer-timeline", 9000);
await page.waitForTimeout(3000);
let c = await census();
report("ON_TIMELINE", c);
await page.screenshot({ path: `${DIR}/430-be109-on-timeline.png` }).catch(() => {});

// Link 1 of the chain: the freeze + travelGaps press.  Without it the gaps card cannot exist.
const freeze = page.getByRole("button", { name: /核实并冻结今天的转场|重新核实转场/ });
const pressedFreeze = await tap(freeze, "freeze-routes", 12000);
note(`FREEZE_PRESSED ${pressedFreeze} t=${elapsed()}`);
if (pressedFreeze) {
  const end = Date.now() + 90 * 1000;
  let tick = 0;
  while (Date.now() < end) {
    c = await census();
    const gapBlock = c.keys.find((k) => k.id === "rev-v3-travel-gaps") || { count: 0 };
    const busy = (c.freeze_label || "").includes("正在核实");
    tick += 1;
    note(`FREEZE_WAIT ${tick} busy=${busy} gaps=${gapBlock.count} t=${elapsed()}`);
    if (!busy && gapBlock.count > 0) break;
    await page.waitForTimeout(4000);
  }
}
report("AFTER_FREEZE", c);
await page.screenshot({ path: `${DIR}/430-be109-after-freeze.png` }).catch(() => {});
await leak("AFTER_FREEZE");

// Link 2: does the traveller get a key that leads to applying the re-planned version?
c = await census();
const plan = c.keys.find((k) => k.id === "rev-v3-replan") || { count: 0 };
const reverify = c.keys.find((k) => k.id === "rev-v3-replan-reverify") || { count: 0 };
note(`REPLAN_DOOR replan=${plan.count} hit=${plan.hitSelf ?? false} reverify=${reverify.count} t=${elapsed()}`);
if (plan.count) {
  if (await tap(page.locator('[data-testid="rev-v3-replan"]'), "rev-v3-replan", 10000)) {
    await page.waitForTimeout(2500);
    c = await census();
    report("AFTER_REPLAN", c);
    await page.screenshot({ path: `${DIR}/430-be109-after-replan.png` }).catch(() => {});
    const apply = c.keys.find((k) => k.id === "rev-v3-replan-apply") || { count: 0 };
    note(`APPLY_DOOR count=${apply.count} visible=${apply.visible ?? false} hit=${apply.hitSelf ?? false} `
      + `disabled=${apply.disabled ?? null} box=${apply.box ?? null} label=${JSON.stringify(apply.label ?? null)} t=${elapsed()}`);
    if (apply.count) {
      const pressed = await tap(page.locator('[data-testid="rev-v3-replan-apply"]'), "rev-v3-replan-apply", 15000);
      note(`APPLY_PRESSED ${pressed} t=${elapsed()}`);
      await page.waitForTimeout(14000);
      await leak("AFTER_APPLY");
      c = await census();
      report("AFTER_APPLY", c);
      await page.screenshot({ path: `${DIR}/430-be109-after-apply.png` }).catch(() => {});
    }
  }
} else if (reverify.count) {
  // The refusal shape with no proposed rows: the card offers re-verification instead.  Record the sentence
  // the traveller reads, because that is the whole product question.
  const sentence = await page.locator('[data-testid="rev-v3-replan-refusal"]').first().innerText().catch(() => null);
  note(`NO_ROWS refusal_sentence=${JSON.stringify((sentence || "").replace(/\s+/g, " ").slice(0, 90))}`);
  if (await tap(page.locator('[data-testid="rev-v3-replan-reverify"]'), "rev-v3-replan-reverify", 10000)) {
    await page.waitForTimeout(16000);
    c = await census();
    report("AFTER_REVERIFY", c);
    await page.screenshot({ path: `${DIR}/430-be109-after-reverify.png` }).catch(() => {});
  }
} else {
  note(`NO_DOOR gaps_block=${JSON.stringify(c.keys.find((k) => k.id === "rev-v3-travel-gaps") ?? null)} t=${elapsed()}`);
  await page.screenshot({ path: `${DIR}/430-be109-no-door.png` }).catch(() => {});
}
const body = await page.evaluate(() => document.body.innerText || "");
note("FINAL_HAS_APPLIED " + /已按|重新安排|这一版|按这一版安排/.test(body));
note("FINAL_CLEAN " + !body.includes("CityNexus API"));
note("DONE t=" + elapsed());
await ctx.close();
