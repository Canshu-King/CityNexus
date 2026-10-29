import { chromium } from "file:///D:/moodle/_cmdr_rescue_v3_1022/frontend/node_modules/playwright/index.mjs";
import fs from "node:fs";

// Knife 2a, second surface.  r116 proved the goal-task event timeline is real, expandable and carries no
// private text (trial/results/20261026_gozero/bk116-agent-tool-timeline-430.txt:47-50).  What it did not
// read is the other timeline in the same panel -- the one built from AgentRunStep rows
// (frontend/src/trial/mobile/WorkspaceActions.tsx:680), which is the surface the 599ed95b76 disclosure
// actually changed: every step row now names who answered for it.
//
// This arm therefore answers three separate questions and prints a reading for each, assuming none:
//   (a) does the step timeline mount at all for a live journey (visibleTask.tool_steps can be empty);
//   (b) once expanded, how many rows carry the disclosure, and do the vendor words the server writes
//       (backend/app/agent/goal_amap.py:153, goal_artifacts.py:262) reach the screen;
//   (c) does anything private reach the screen instead -- uuid, key material, model text.
// Isolated canary stack: vite :14464 / backend :60364 from E:/_cmdr_tip_113 (detached at dea0328e0b) with
// one frontend file carried forward for the measurement -- WorkspaceActions.tsx, checked out at the
// 599ed95b76 blob 82a158d91bf0e66cf2ed743e222a1ec6dd732196 and restored afterwards; the tree's own tip
// report stays dea0328e0b and the backend is untouched.
// No seeded storage, no direct API calls, no DOM injection: every request below answers a real press.
const DIR = "D:/moodle/_cmdr_rescue_v3_1022/trial/results/20261026_gozero";
const OUT = `${DIR}/bn122-tool-step-source-390.txt`;
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
        channel: "chrome", headless: false, viewport: { width: 390, height: 844 }, deviceScaleFactor: 1,
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
  "D:/moodle/_cmdr_v3_live_1022/_chrome_gozero_bn122",
  "D:/moodle/_cmdr_v3_live_1022/_chrome_gozero_bn122b",
]);
const page = ctx.pages()[0] ?? await ctx.newPage();
page.on("response", async (resp) => {
  const url = resp.url(); const method = resp.request().method();
  if (!url.includes("/api/v1/") || (method !== "POST" && method !== "PUT")) return;
  if (!/goal-tasks|plans|journeys|departure|routes|gaps/.test(url)) return;
  const line = `HTTP ${method} ${resp.status()} ${url.replace(/^http:\/\/[^/]+/, "")}`;
  if (resp.status() >= 400) {
    let d = ""; try { d = JSON.stringify(await resp.json()).slice(0, 400); } catch { d = "(unreadable)"; }
    note(line + " BODY " + d);
  } else note(line);
});
page.on("pageerror", (e) => note("PAGEERROR " + String(e).slice(0, 160)));

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
  // A swallowed click rejection is how an instrument reports "pressed" for a press that never landed:
  // the first 390x844 run printed STEPS_SUMMARY_PRESSED true while the details stayed closed.  Scroll
  // with Playwright's own container-aware call, then name the rejection instead of hiding it.
  await target.scrollIntoViewIfNeeded().catch((e) => note(`SCROLL_FAIL ${label} ` + String(e).replace(/\s+/g, " ").slice(0, 150)));
  await target.click({ timeout: 15000 }).catch((e) => note(`CLICK_FAIL ${label} ` + String(e).replace(/\s+/g, " ").slice(0, 220)));
  await page.waitForTimeout(1200);
  return true;
}

const stateLine = () => page.evaluate(() => {
  const body = document.body.innerText || "";
  return (body.match(/[^\n]*(正在研究|已整理 \d+ 天|当前展示的是已保存版本)[^\n]*/) || [null])[0]
    ?.replace(/\s+/g, " ").slice(0, 60) ?? null;
});

await page.goto("http://127.0.0.1:14464/revolution", { waitUntil: "domcontentloaded", timeout: 60000 });
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

const skipEnd = Date.now() + 5 * 60 * 1000;
while (Date.now() < skipEnd) {
  const s = page.locator('[data-testid="rev-agent-skip-questions"]');
  if (await s.count()) { await s.first().click().catch(() => {}); note(`SKIP t=${elapsed()}`); break; }
  await page.waitForTimeout(3000);
}
let ready = false;
const draftEnd = Date.now() + 12 * 60 * 1000;
let tick = 0;
while (Date.now() < draftEnd) {
  tick += 1;
  const line = await stateLine().catch(() => null);
  if (tick % 3 === 1) note(`DRAFT_WAIT ${tick} state=${JSON.stringify(line)} t=${elapsed()}`);
  if (/已整理 \d+ 天|当前展示的是已保存版本/.test(line || "")) {
    ready = true; note(`DRAFT_READY ${JSON.stringify(line)} t=${elapsed()}`); break;
  }
  await page.waitForTimeout(6000);
}
if (!ready) note(`NO_DRAFT t=${elapsed()}`);
note(`JOURNEY_URL ${page.url().replace(/^http:\/\/[^/]+/, "")}`);

const steps = () => page.evaluate(() => {
  const box = document.querySelector(".rev-agent-tool-timeline");
  const rows = Array.from(document.querySelectorAll(".rev-agent-tool-timeline li"));
  const read = (el) => (el ? (el.innerText || "").replace(/\s+/g, " ").trim() : "");
  const src = Array.from(document.querySelectorAll('[data-testid="rev-agent-tool-source"]')).map(read);
  const body = document.body.innerText || "";
  const open = box ? (("open" in box) ? Boolean(box.open) : box.getAttribute("open") !== null) : null;
  const uuid = /[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}/i;
  return {
    present: Boolean(box), open,
    summary: read(box ? box.querySelector("summary") : null).slice(0, 80),
    rows: rows.length,
    row_texts: rows.slice(0, 4).map((r) => read(r).slice(0, 110)),
    source_rows: src.length,
    source_texts: src.slice(0, 8),
    vendors: {
      amap: src.filter((s) => s.indexOf("高德地图") >= 0).length,
      public_lists: src.filter((s) => s.indexOf("公开地点清单") >= 0 || s.indexOf("OpenStreetMap") >= 0
        || s.indexOf("公开检索") >= 0 || s.indexOf("官方网站") >= 0 || s.indexOf("路线计算服务") >= 0).length,
      not_recorded: src.filter((s) => s.indexOf("未记录的来源") >= 0 || s.indexOf("核实状态未记录") >= 0).length,
      checked: src.filter((s) => s.indexOf("已核实") >= 0).length,
      unchecked: src.filter((s) => s.indexOf("还没核实") >= 0).length,
    },
    private_markers: ["reasoning", "chain of thought", "思考过程", "内部指令", "system prompt",
      "api_key", "sk-", "CITYNEXUS_AMAP_WEB_KEY"].filter((n) => body.toLowerCase().indexOf(n.toLowerCase()) >= 0),
    uuid_in_source: uuid.test(src.join(" ")),
  };
});

const openedAgent = await tap(page.locator('[data-testid="rev-mission-layer-agent"]'), "layer-agent", 9000);
note(`AGENT_LAYER_OPENED ${openedAgent} t=${elapsed()}`);
await page.waitForTimeout(2500);
let s = await steps();
note(`STEPS_BEFORE ${JSON.stringify(s)} t=${elapsed()}`);
await page.screenshot({ path: `${DIR}/390-bn122-steps-collapsed.png` }).catch(() => {});
if (s.present && !s.open) {
  const pressed = await tap(page.locator(".rev-agent-tool-timeline summary"), "steps-summary", 8000);
  note(`STEPS_SUMMARY_PRESSED ${pressed} t=${elapsed()}`);
  await page.waitForTimeout(1800);
  s = await steps();
  note(`STEPS_AFTER ${JSON.stringify(s)} t=${elapsed()}`);
  await page.screenshot({ path: `${DIR}/390-bn122-steps-open.png` }).catch(() => {});
}
if (s.present && s.rows > 0 && s.source_rows === 0) {
  // The row count is the discriminator: steps exist, so the disclosure block should exist with them.
  note("VERDICT DISCLOSURE_MISSING_ON_SCREEN rows=" + s.rows);
} else if (s.source_rows > 0) {
  note(`VERDICT DISCLOSURE_ON_SCREEN rows=${s.rows} sources=${s.source_rows} amap=${s.vendors.amap}`);
} else note("VERDICT STEP_TIMELINE_NOT_MOUNTED");
const hitProof = await page.evaluate(() => {
  const n = document.querySelector('[data-testid="rev-agent-tool-source"]');
  if (!n) return null;
  const b = n.getBoundingClientRect();
  const top = b.width && b.height ? document.elementFromPoint(b.left + b.width / 2, b.top + b.height / 2) : null;
  return { box: `${Math.round(b.width)}x${Math.round(b.height)}@${Math.round(b.top)}`,
    inViewport: b.top >= 0 && b.bottom <= (window.innerHeight || 844),
    visible: b.width > 0 && b.height > 0 };
}).catch(() => null);
note(`SOURCE_HIT_PROOF ${JSON.stringify(hitProof)}`);
note("FINAL_CLEAN " + !(await page.evaluate(() => document.body.innerText || "")).includes("CityNexus API"));
note("DONE t=" + elapsed());
await ctx.close();
