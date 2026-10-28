import { chromium } from "file:///D:/moodle/_cmdr_rescue_v3_1022/frontend/node_modules/playwright/index.mjs";
import fs from "node:fs";

// ORD #341, one run.  Section 100 left exactly one unknown: under what condition does
// "保存为正式候选方案" mount, given the layer tabs are already visible while the key is absent.  So poll
// that key's own state every three seconds inside a single evaluate -- presence, box size, computed
// visibility, which layer is active, and the task-state sentence on screen -- and the moment it becomes
// pressable, press it twice.  The first press is the real save; the second is the resume 409 that on
// 840534ec11 printed "CityNexus API 409: /journeys/<uuid>/agent/goal-tasks/<uuid>/resume" onto a
// traveller's screen.  This is the screen proof for the reason-to-sentence mapping.
// Isolated stack only: vite :14462 / backend :60362 serving the zero-dirty worktree
// E:/_cmdr_clean_1028, its own canary SQLite, and a throwaway Chrome profile.  No seeded state.
const DIR = "D:/moodle/_cmdr_rescue_v3_1022/trial/results/20261026_gozero";
const OUT = `${DIR}/bb2-three-labels-430-r104.txt`;
const NL = String.fromCharCode(10);
const lines = [];
const note = (v) => { lines.push(v); fs.writeFileSync(OUT, lines.join(NL) + NL, "utf8"); };
const started = Date.now();
const elapsed = () => ((Date.now() - started) / 1000).toFixed(1);
const UUID = /[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}/i;
// Section 103: DraftDepartureCard:324 renders one button with three labels depending on state, so a
// judgement keyed to a single Chinese string is a judgement about the copy version, not the screen.
const KEY_LABELS = ["保存为正式候选方案", "按以上时间重新准备方案", "正在保存安排…"];
const KEY_TEXT = KEY_LABELS[0];
const labelOf = (text) => KEY_LABELS.find((l) => (text || "").includes(l)) || null;

const ctx = await chromium.launchPersistentContext("D:/moodle/_cmdr_v3_live_1022/_chrome_gozero_bb104_r104c", {
  channel: "chrome", headless: false, viewport: { width: 430, height: 932 }, deviceScaleFactor: 1,
});
const page = ctx.pages()[0] ?? await ctx.newPage();
page.on("response", async (resp) => {
  const url = resp.url(); const method = resp.request().method();
  if (!url.includes("/api/v1/") || (method !== "POST" && method !== "PUT")) return;
  if (!/goal-tasks|plans|journeys|departure/.test(url)) return;
  const line = `HTTP ${method} ${resp.status()} ${url.replace(/^http:\/\/[^/]+/, "")}`;
  if (resp.status() >= 400) {
    let d = ""; try { d = JSON.stringify(await resp.json()).slice(0, 700); } catch { d = "(unreadable)"; }
    note(line + " BODY " + d);
  } else note(line);
});
page.on("pageerror", (e) => note("PAGEERROR " + String(e).slice(0, 160)));

// One evaluate answers all five questions about the same instant, so no reading is compared across time.
const probe = () => page.evaluate((keyText) => {
  const nodes = Array.from(document.querySelectorAll("button"));
  const key = nodes.find((b) => ["保存为正式候选方案","按以上时间重新准备方案","正在保存安排…"].some((l) => (b.innerText || "").includes(l)));
  let activeLayer = null;
  for (const b of nodes) {
    const cls = String(b.className || "");
    if (/rev-mission-layer/.test(cls) && /is-active|active/.test(cls)) { activeLayer = (b.innerText || "").trim().slice(0, 8); break; }
  }
  const body = document.body.innerText || "";
  const stateLine = (body.match(/[^\n]*(正在处理|正在研究|已整理|行程草案|当前展示的是已保存版本|等这一轮结束)[^\n]*/) || [null])[0];
  const cockpit = (() => { const c = document.querySelector('[data-testid="rev-mission-cockpit"]'); return c ? `${c.dataset.space || "?"}/${c.dataset.layer || "?"}` : null; })();
  return {
    cockpit,
    key_label: key ? (key.innerText || "").replace(/\s+/g, " ").trim().slice(0, 20) : null,
    key_present: Boolean(key),
    key_visible: key ? (() => { const b = key.getBoundingClientRect(); const s = getComputedStyle(key); return b.width > 0 && b.height > 0 && s.visibility === "visible" && Number(s.opacity) > 0; })() : false,
    key_disabled: key ? Boolean(key.disabled) : null,
    key_box: key ? (() => { const b = key.getBoundingClientRect(); return `${Math.round(b.width)}x${Math.round(b.height)}@${Math.round(b.top)}`; })() : null,
    activeLayer,
    stateLine: stateLine ? stateLine.replace(/\s+/g, " ").slice(0, 60) : null,
  };
}, KEY_TEXT);

async function leakReading(label) {
  const band = await page.locator(".rev-plan-message, [role='alert'], [role='status']").allInnerTexts().catch(() => []);
  const joined = band.join(" | ");
  const body = await page.evaluate(() => document.body.innerText || "").catch(() => "");
  note(`${label} TEXTS ${JSON.stringify(band.slice(0, 5))}`);
  note(`${label} LEAK api_in_body=${body.includes("CityNexus API")} api_in_band=${joined.includes("CityNexus API")} uuid_in_band=${UUID.test(joined)}`);
  note(`${label} SENTENCE ${JSON.stringify((body.match(/[^。]*?(这一版已经排好|不再改草案|刷新一下再继续|这一轮还在进行中)[^。]*。/) || [null])[0])}`);
}

await page.goto("http://127.0.0.1:14462/revolution", { waitUntil: "domcontentloaded", timeout: 60000 });
await page.waitForTimeout(6000);
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

const skipEnd = Date.now() + 6 * 60 * 1000;
while (Date.now() < skipEnd) {
  const s = page.locator('[data-testid="rev-agent-skip-questions"]');
  if (await s.count()) { await s.first().click().catch(() => {}); note(`SKIP t=${elapsed()}`); break; }
  await page.waitForTimeout(3000);
}

let pressed = false;
const end = Date.now() + 16 * 60 * 1000;
let last = "";
let tripTried = false;
for (let tick = 0; Date.now() < end; tick += 1) {
  const p = await probe();
  const flat = JSON.stringify(p);
  if (flat !== last) { note(`SEQ ${tick} t=${elapsed()} ${flat}`); last = flat; }  // only transitions
  // The rerun's source-named fix, before pressing anything: the save key lives in the "准备出发"
  // details (rev-v3-preparation) that mounts only when space === "journey" (MissionCockpit.tsx:421),
  // and space is the mobile bottom tab -- space={activeTab === "trips" ? "journey" : "explore"}
  // (RevolutionFirstLook.tsx:1562) -- not the map/timeline/agent layer tabs every arm from r100 to
  // r103 kept clicking.  Enter the trips tab the moment the draft line appears and stay there; the
  // cockpit's own effect puts the journey space on the timeline layer (MissionCockpit.tsx:153),
  // which is the pane the card and its key live in.
  if (!tripTried && /已整理|行程草案/.test(p.stateLine || "")) {
    tripTried = true;
    // Second arrangement fact, also from source not from a probe: rev-open-trip sits in the
    // capability grid INSIDE the timeline pane (MissionCockpit.tsx:405-423), so a cockpit left on
    // the agent layer has no such button -- the first rerun timed out on exactly this.  Land the
    // timeline layer first, then the trips tab.
    await page.locator('[data-testid="rev-mission-layer-timeline"]').first().click({ timeout: 8000 }).catch((e) => note("LAYER_ERR " + String(e).slice(0, 60)));
    await page.waitForTimeout(2500);
    note(`AFTER_LAYER ${JSON.stringify(await probe())} t=${elapsed()}`);
    const trip = page.locator('[data-testid="rev-open-trip"]');
    if (await trip.count().catch(() => 0)) {
      await trip.first().click({ timeout: 8000 }).catch((e) => note("TRIP_ERR " + String(e).slice(0, 60)));
      await page.waitForTimeout(3500);
      note(`AFTER_TRIP ${JSON.stringify(await probe())} t=${elapsed()}`);
    } else note("TRIP_MISSING t=" + elapsed());
  }
  if (p.key_present && p.key_visible && !p.key_disabled) { pressed = true; note(`KEY_UP ${tick} t=${elapsed()}`); break; }
  await page.waitForTimeout(3000);
}
if (!pressed) {
  await leakReading("NO_KEY_WINDOW");
  await page.screenshot({ path: `${DIR}/430-bb2-no-key-window.png` }).catch(() => {});
  note("ABORT the save key never mounted inside the window; the sequence above names the last state seen");
  await ctx.close();
  process.exit(6);
}

const key = page.getByRole("button", { name: /保存为正式候选方案|按以上时间重新准备方案|正在保存安排…/ });
for (const round of [1, 2]) {
  await key.first().scrollIntoViewIfNeeded().catch(() => {});
  const hit = await key.first().evaluate((n) => {
    const b = n.getBoundingClientRect();
    const top = document.elementFromPoint(b.left + b.width / 2, b.top + b.height / 2);
    return Boolean(top) && (n === top || n.contains(top)) && !n.disabled;
  }).catch(() => false);
  note(`HIT save-${round} ${hit} t=${elapsed()}`);
  if (hit) await key.first().click({ timeout: 15000 }).catch(() => {});
  await page.waitForTimeout(round === 1 ? 15000 : 9000);
  await leakReading(`R${round}`);
  await page.screenshot({ path: `${DIR}/430-bb2-after-save-${round}.png` }).catch(() => {});
  note(`AFTER_R${round} ${JSON.stringify(await probe())} t=${elapsed()}`);
}
const finalBody = await page.evaluate(() => document.body.innerText || "");
note("FINAL_HAS_SAVED " + /已保存\s*\d+\s*项正式安排/.test(finalBody));
note("FINAL_CLEAN " + (!finalBody.includes("CityNexus API")));
note("DONE t=" + elapsed());
await ctx.close();
