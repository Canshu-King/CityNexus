import { chromium } from "file:///D:/moodle/_cmdr_rescue_v3_1022/frontend/node_modules/playwright/index.mjs";
import fs from "node:fs";

// SETUP DISCLOSURE: isolated canary stack only -- vite http://127.0.0.1:14462 and backend :60362
// serving the zero-dirty worktree E:/_cmdr_clean_1028 at ea51658c9a, its own SQLite
// E:/_cmdr_clean_1028_data/citynexus_v3_clean_1028.db, and a fresh throwaway Chrome profile.  No
// shared preview database, no seeded state: every request below comes from a hand press in real
// Chrome, and the 409 that matters is produced by pressing the same key a second time.
const W = 430;
const H = 932;
const TAG = String(W);
const PROFILE = "D:/moodle/_cmdr_v3_live_1022/_chrome_gozero_aq92";
const BASE = "http://127.0.0.1:14462";
const DIR = "D:/moodle/_cmdr_rescue_v3_1022/trial/results/20261026_gozero";
const OUT = `${DIR}/aq2-clean-chain-430-r92.txt`;
const NL = String.fromCharCode(10);
const lines = [];
const note = (value) => { lines.push(value); fs.writeFileSync(OUT, lines.join(NL) + NL, "utf8"); };
const started = Date.now();
const elapsed = () => ((Date.now() - started) / 1000).toFixed(1);
const UUID = /[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}/i;

const ctx = await chromium.launchPersistentContext(PROFILE, {
  channel: "chrome", headless: false, viewport: { width: W, height: H }, deviceScaleFactor: 1,
});
const page = ctx.pages()[0] ?? await ctx.newPage();
page.on("response", async (resp) => {
  const url = resp.url();
  const method = resp.request().method();
  if (!url.includes("/api/v1/") || (method !== "POST" && method !== "PUT")) return;
  if (!/goal-tasks|plans|journeys|departure/.test(url)) return;
  const line = `HTTP ${method} ${resp.status()} ${url.replace(/^http:\/\/[^/]+/, "")}`;
  if (resp.status() >= 400) {
    let detail = "";
    try { detail = JSON.stringify(await resp.json()).slice(0, 1200); } catch { detail = "(unreadable body)"; }
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
  await page.waitForTimeout(900);
  return true;
}
const bodyText = () => page.evaluate(() => document.body.innerText || "").catch(() => "");
const busy = (text) => /正在研究|回复中|Agent 正在处理/.test(text);

// Two readings, on purpose.  The narrow one is the band a traveller actually reads back; the wide
// one catches the same string escaping anywhere else on the screen.  "CityNexus API" can only be the
// client-side error string, so it is safe to judge on the whole body; a bare uuid also appears in
// legitimate source links, so it is only judged inside the message band.
async function leakReading(label) {
  const band = await page.locator(".rev-plan-message, [role='alert'], [role='status']").allInnerTexts().catch(() => []);
  const joined = band.join(" | ");
  const body = await bodyText();
  note(`${label} TEXTS ${JSON.stringify(band.slice(0, 4))}`);
  note(`${label} LEAK citynexus_api_in_body=${body.includes("CityNexus API")} `
    + `api_in_band=${joined.includes("CityNexus API")} uuid_in_band=${UUID.test(joined)}`);
  return { band: joined, body };
}

await page.goto(`${BASE}/revolution`, { waitUntil: "domcontentloaded", timeout: 60000 });
await page.waitForTimeout(4000);
await shot(`${TAG}-aq-cold`);
await page.getByRole("textbox", { name: /想怎么玩/ }).first()
  .fill("2026 年 12 月 3 日到 4 日在北京玩两天，两个人，每段步行不超过 1 公里，太远坐地铁");
await page.waitForTimeout(500);
await press(page.getByRole("button", { name: /继续规划/ }), "continue");
await page.waitForTimeout(2500);
await press(page.getByRole("button", { name: "对话", exact: true }), "tab-chat", 10000);
await page.waitForTimeout(1200);
await press(page.getByRole("button", { name: /对话设置/ }), "open-settings");
await page.waitForTimeout(700);
for (const label of [/本次允许 AI 处理旅行目标/, /本次允许查询公开地图和地点来源/]) {
  const box = page.getByRole("checkbox", { name: label }).first();
  if (await box.count() && !(await box.isChecked())) await box.check().catch(() => {});
  note(`CONSENT ${await box.isChecked().catch(() => null)}`);
}
await press(page.getByRole("button", { name: /关闭对话设置/ }), "close-settings");
await page.waitForTimeout(400);
await press(page.getByRole("button", { name: /发送/ }), "send");
note("SENT t=" + elapsed());

let skipped = false;
const skipEnd = Date.now() + 6 * 60 * 1000;
let recoveries = 0;
while (Date.now() < skipEnd) {
  if (await visible(page.locator('[data-testid="rev-agent-skip-questions"]'))
      && await press(page.locator('[data-testid="rev-agent-skip-questions"]'), "skip-questions", 15000)) {
    skipped = true; note(`SKIP t=${elapsed()}`); break;
  }
  const text = await bodyText();
  if (/这次有一部分还没完成|这一轮没有完成|请求失败|被限流|超时/.test(text) && recoveries < 2) {
    if (await press(page.getByRole("button", { name: /按讨论的方向开始研究/ }), `recover-${recoveries}`, 15000)) {
      recoveries += 1; note(`RECOVERY ${recoveries}`);
    }
  }
  await page.waitForTimeout(3000);
}
note(`SKIPPED ${skipped}`);

let draftSeen = false;
const researchEnd = Date.now() + 18 * 60 * 1000;
while (Date.now() < researchEnd) {
  const text = await bodyText();
  if (/已整理\s*\d+\s*天/.test(text) || /行程草案/.test(text)) { draftSeen = true; note(`DRAFT t=${elapsed()}`); break; }
  if (skipped && !busy(text)) { note(`IDLE_NO_DRAFT t=${elapsed()}`); break; }
  await page.waitForTimeout(6000);
}
note(`DRAFT_SEEN ${draftSeen}`);
await shot(`${TAG}-aq-after-research`);

const saveButton = page.getByRole("button", { name: /保存为正式候选方案/ });
// The r91 run aborted here for an instrument reason, not a product one: a draft heading can appear
// while the round is still running, and the card says so out loud ("Agent 正在研究，等这一轮结束即可
// 编辑保存").  So wait for the key itself, not for a heading on some other panel.
const keyEnd = Date.now() + 12 * 60 * 1000;
while (Date.now() < keyEnd && !(await visible(saveButton))) {
  if (await visible(saveButton)) break;
  const waiting = await page.locator(".rev-plan-message, [role='status']").allInnerTexts().catch(() => []);
  note(`WAIT_KEY t=${elapsed()} ${JSON.stringify(waiting.slice(0, 1))}`);
  await page.waitForTimeout(20000);
}
note(`SAVE_KEY ${await saveButton.count().catch(() => 0)} t=${elapsed()}`);
if (!(await visible(saveButton))) {
  note("ABORT no visible 保存为正式候选方案 key -- nothing to press twice");
  await leakReading("NO_KEY");
  await shot(`${TAG}-aq-no-key`);
  await ctx.close();
  process.exit(5);
}

// First press: the real save.  Second press: the same hand on the same key while the plan is already
// saved -- this is the press that produced the leak on the previous generation.
for (const round of [1, 2]) {
  if (!(await visible(saveButton))) { note(`R${round}_KEY_GONE`); break; }
  const pressed = await press(saveButton, `save-round-${round}`, 30000);
  note(`R${round}_PRESSED ${pressed} t=${elapsed()}`);
  await page.waitForTimeout(round === 1 ? 12000 : 6000);
  await leakReading(`R${round}`);
  await shot(`${TAG}-aq-after-save-${round}`);
}

// A third press only after the round has settled, because the same key is also the one the
// 转场 refusal path re-arms.
await page.waitForTimeout(4000);
if (await visible(saveButton)) {
  await press(saveButton, "save-round-3", 30000);
  await page.waitForTimeout(6000);
  await leakReading("R3");
  await shot(`${TAG}-aq-after-save-3`);
}
const finalText = await bodyText();
note("FINAL_HAS_SAVED " + /已保存\s*\d+\s*项正式安排/.test(finalText));
note("FINAL_HAS_PLANSentence " + (/这一版已经排好|不再改草案/.test(finalText)));
note("DONE t=" + elapsed());
await ctx.close();
