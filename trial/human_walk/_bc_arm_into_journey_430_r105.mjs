import { chromium } from "file:///D:/moodle/_cmdr_rescue_v3_1022/frontend/node_modules/playwright/index.mjs";
import fs from "node:fs";

// Why nine arms never found the key.  bb2 matched all three labels of DraftDepartureCard:324 and still
// read key_label null, while its own cockpit field said "explore/agent" the whole time -- the walk stays
// on the trial/explore screen and never enters the trip, and the departure card lives inside the trip
// cockpit.  So this arm does the one thing the others skipped: after the draft, go through 我的旅程 into
// that journey, then look for the key there and press it twice.
// Isolated canary stack: vite :14462 / backend :60362 on the zero-dirty worktree E:/_cmdr_clean_1028,
// its own SQLite, throwaway profile.  Nothing is seeded; every request comes from a real press.
const DIR = "D:/moodle/_cmdr_rescue_v3_1022/trial/results/20261026_gozero";
const OUT = `${DIR}/bc-into-journey-430-r105.txt`;
const NL = String.fromCharCode(10);
const lines = [];
const note = (v) => { lines.push(v); fs.writeFileSync(OUT, lines.join(NL) + NL, "utf8"); };
const started = Date.now();
const elapsed = () => ((Date.now() - started) / 1000).toFixed(1);
const UUID = /[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}/i;
const LABELS = ["保存为正式候选方案", "按以上时间重新准备方案", "正在保存安排…"];

const ctx = await chromium.launchPersistentContext("D:/moodle/_cmdr_v3_live_1022/_chrome_gozero_bc105", {
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

const probe = () => page.evaluate((labels) => {
  const nodes = Array.from(document.querySelectorAll("button"));
  const key = nodes.find((b) => labels.some((l) => (b.innerText || "").includes(l)));
  const body = document.body.innerText || "";
  const box = key ? key.getBoundingClientRect() : null;
  const cs = key ? getComputedStyle(key) : null;
  const fs2 = key ? key.closest("fieldset") : null;
  return {
    url: location.pathname,
    key_label: key ? (key.innerText || "").replace(/\s+/g, " ").trim().slice(0, 22) : null,
    key_present: Boolean(key),
    key_visible: box ? box.width > 0 && box.height > 0 && cs.visibility === "visible" && Number(cs.opacity) > 0 : false,
    key_disabled: key ? Boolean(key.disabled) : null,
    fieldset_disabled: fs2 ? Boolean(fs2.disabled) : null,
    key_box: box ? `${Math.round(box.width)}x${Math.round(box.height)}@${Math.round(box.top)}` : null,
    stateLine: (body.match(/[^\n]*(正在处理|正在研究|已整理|行程草案|当前展示的是已保存版本|等这一轮结束)[^\n]*/) || [null])[0]?.replace(/\s+/g, " ").slice(0, 56) ?? null,
  };
}, LABELS);

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
async function leakReading(tag) {
  const band = await page.locator(".rev-plan-message, [role='alert'], [role='status']").allInnerTexts().catch(() => []);
  const body = await page.evaluate(() => document.body.innerText || "").catch(() => "");
  const joined = band.join(" | ");
  note(`${tag} TEXTS ${JSON.stringify(band.slice(0, 5))}`);
  note(`${tag} LEAK api_in_body=${body.includes("CityNexus API")} api_in_band=${joined.includes("CityNexus API")} uuid_in_band=${UUID.test(joined)}`);
  note(`${tag} MAPPED ${JSON.stringify((body.match(/[^。]*?(这一版已经排好|不再改草案|刷新一下再继续|这一轮还在进行中|重新核实)[^。]*。/) || [null])[0])}`);
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

const skipEnd = Date.now() + 6 * 60 * 1000;
while (Date.now() < skipEnd) {
  const s = page.locator('[data-testid="rev-agent-skip-questions"]');
  if (await s.count()) { await s.first().click().catch(() => {}); note(`SKIP t=${elapsed()}`); break; }
  await page.waitForTimeout(3000);
}
const draftEnd = Date.now() + 12 * 60 * 1000;
let draft = false;
while (Date.now() < draftEnd) {
  const p = await probe();
  if (/已整理|行程草案/.test(p.stateLine || "")) { draft = true; note(`DRAFT t=${elapsed()} ${JSON.stringify(p)}`); break; }
  await page.waitForTimeout(6000);
}
if (!draft) note(`NO_DRAFT t=${elapsed()} ${JSON.stringify(await probe())}`);

// The step every earlier arm skipped: leave the trial screen and go into the trip itself.
await tap(page.locator('[data-testid="rev-mobile-tab-trips"]'), "trips-tab", 10000);
note(`ON_TRIPS ${JSON.stringify(await probe())} t=${elapsed()}`);
await page.screenshot({ path: `${DIR}/430-bc-trips.png` }).catch(() => {});
const cards = page.locator("article, [data-testid*='trip-card'], [data-testid*='journey'], li button");
const n = await cards.count().catch(() => 0);
note("CARDS " + n);
for (let k = 0; k < Math.min(n, 6); k += 1) {
  if (await tap(cards.nth(k), `card-${k}`, 7000)) {
    await page.waitForTimeout(4000);
    const p = await probe();
    note(`IN_CARD ${k} ${JSON.stringify(p)} t=${elapsed()}`);
    if (p.key_present) break;
  }
}
let p = await probe();
if (!p.key_present) {
  // Inside a journey the itinerary layer is where the departure card lives.
  await tap(page.locator('[data-testid="rev-mission-layer-timeline"]'), "layer-timeline", 9000);
  await page.waitForTimeout(4000);
  p = await probe();
  note(`AFTER_LAYER ${JSON.stringify(p)} t=${elapsed()}`);
}
if (!p.key_present) {
  await leakReading("STILL_NO_KEY");
  await page.screenshot({ path: `${DIR}/430-bc-still-no-key.png` }).catch(() => {});
  note("ABORT entered the journey and the key is still not in the tree -- next question is which panel renders DraftDepartureCard");
  await ctx.close();
  process.exit(6);
}

const key = page.getByRole("button", { name: /保存为正式候选方案|按以上时间重新准备方案|正在保存安排…/ });
for (const round of [1, 2]) {
  const pressed = await tap(key, `press-${round}`, 20000);
  note(`PRESSED_${round} ${pressed} t=${elapsed()}`);
  await page.waitForTimeout(round === 1 ? 16000 : 9000);
  await leakReading(`R${round}`);
  await page.screenshot({ path: `${DIR}/430-bc-after-press-${round}.png` }).catch(() => {});
  note(`AFTER_P${round} ${JSON.stringify(await probe())} t=${elapsed()}`);
}
const finalBody = await page.evaluate(() => document.body.innerText || "");
note("FINAL_HAS_SAVED " + /已保存\s*\d+\s*项正式安排/.test(finalBody));
note("FINAL_CLEAN " + !finalBody.includes("CityNexus API"));
note("DONE t=" + elapsed());
await ctx.close();
