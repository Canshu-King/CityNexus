import { chromium } from "file:///D:/moodle/_cmdr_rescue_v3_1022/frontend/node_modules/playwright/index.mjs";
import fs from "node:fs";

const DIR = "D:/moodle/_cmdr_rescue_v3_1022/trial/results/20261026_gozero";
const OUT = `${DIR}/go-live-430.txt`;
const NL = String.fromCharCode(10);
const lines = [];
const note = (v) => { lines.push(v); fs.writeFileSync(OUT, lines.join(NL) + NL, "utf8"); };
const t0 = Date.now();
const el = () => ((Date.now() - t0) / 1000).toFixed(1);
const bearer = JSON.parse(fs.readFileSync("D:/moodle/_cmdr_v3_live_1022/.gozero_bearer.json", "utf8"));

const ctx = await chromium.launchPersistentContext("D:/moodle/_cmdr_v3_live_1022/_chrome_gozero_1031", {
  channel: "chrome", headless: false, viewport: { width: 430, height: 932 }, deviceScaleFactor: 1,
});
const page = ctx.pages()[0] ?? await ctx.newPage();
const http = [];
page.on("response", (r) => {
  const u = r.url();
  if (!/departure|plans|goal-tasks/.test(u)) return;
  if (!["POST", "PUT"].includes(r.request().method())) return;
  http.push(`${r.status()} ${u.replace(/^http:\/\/[^/]+/, "").slice(0, 96)}`);
  note("HTTP " + http[http.length - 1]);
});
let cdp = null;
async function shot(name) {
  try {
    cdp ??= await page.context().newCDPSession(page);
    const { data } = await cdp.send("Page.captureScreenshot", { format: "png" });
    fs.writeFileSync(`${DIR}/${name}.png`, Buffer.from(data, "base64"));
    note("SHOT " + name + " t=" + el());
  } catch (e) { note("SHOT_ERR " + String(e).slice(0, 60)); }
}
async function press(loc, label, timeout = 12000) {
  const t = loc.first();
  try { await t.waitFor({ state: "visible", timeout }); } catch { note(`MISS ${label} t=${el()}`); return false; }
  await t.evaluate((n) => n.scrollIntoView({ block: "center" })).catch(() => {});
  await page.waitForTimeout(250);
  const ok = await t.evaluate((node) => {
    const b = node.getBoundingClientRect();
    if (!b.width || !b.height) return false;
    const top = document.elementFromPoint(b.left + b.width / 2, b.top + b.height / 2);
    return Boolean(top) && (node === top || node.contains(top)) && !node.disabled;
  });
  note(`HIT ${label} ${ok} t=${el()}`);
  if (!ok) return false;
  await t.click({ timeout: 15000 }).catch(() => {});
  await page.waitForTimeout(900);
  return true;
}
const body = () => page.evaluate(() => document.body.innerText || "").catch(() => "");

async function removeSlot(dayIndex, titleMark) {
  await press(page.locator(`#rev-v3-day-tab-${dayIndex}`), `day-${dayIndex}`);
  await page.waitForTimeout(600);
  const slots = page.locator(`#rev-v3-day-${dayIndex} details.rev-goal-draft-slot`);
  const total = await slots.count();
  for (let i = 0; i < total; i += 1) {
    const text = (await slots.nth(i).locator("summary").first().innerText().catch(() => "")) || "";
    if (!text.includes(titleMark)) continue;
    await slots.nth(i).locator("summary").first().click().catch(() => {});
    await page.waitForTimeout(400);
    const remove = slots.nth(i).getByRole("button", { name: /移除这项安排/ });
    if (!(await remove.count())) { note("NO_REMOVE " + titleMark); return false; }
    await remove.first().click({ timeout: 8000 }).catch(() => {});
    note("REMOVED " + JSON.stringify(text.replace(/\s+/g, " ").slice(0, 40)));
    await page.waitForTimeout(600);
    return true;
  }
  note("SLOT_NOT_FOUND " + titleMark);
  return false;
}

await page.goto("http://127.0.0.1:14461/revolution", { waitUntil: "domcontentloaded", timeout: 60000 });
await page.evaluate(([token, traveler, journey, taskId]) => {
  sessionStorage.setItem("citynexus.traveler.bearer", token);
  sessionStorage.setItem("citynexus.traveler.session-id", traveler);
  localStorage.setItem("citynexus.v8.journey_id", journey);
  if (taskId) localStorage.setItem("citynexus.revolution.goal-task." + traveler + "." + journey, taskId);
}, [bearer.access_token, bearer.traveler_id, bearer.journey_id, bearer.task_id]);
await page.reload({ waitUntil: "domcontentloaded" });
await page.waitForTimeout(7000);
await press(page.getByRole("button", { name: /我的旅程/ }), "journey-tab");
await page.waitForTimeout(2500);
await press(page.getByRole("button", { name: /继续这趟/ }), "continue-trip");
await page.waitForTimeout(4000);

const editor = page.locator('section[aria-label="可编辑旅行草案"]');
note("EDITOR " + await editor.count());
await removeSlot(0, "全聚德");
await removeSlot(1, "什刹海前海");
const save = editor.getByRole("button", { name: /保存草案/ });
if (await press(save, "save-draft")) {
  for (let i = 0; i < 16; i += 1) {
    await page.waitForTimeout(1200);
    const mark = ((await body()).match(/草案已保存到这趟旅行|保存失败.{0,40}/) || [null])[0];
    if (mark) { note("SAVE " + JSON.stringify(mark)); break; }
  }
}

const confirmBox = page.getByRole("checkbox", { name: /按以上时间准备方案/ }).first();
if (await confirmBox.count() && !(await confirmBox.isChecked())) await confirmBox.check().catch(() => {});
const gen = page.getByRole("button", { name: /保存为正式候选方案|生成正式候选方案/ });
await press(gen, "generate-plan", 20000);
await page.waitForTimeout(8000);

const price = page.locator('[data-testid="rev-v3-accept-price"]');
if (await price.first().isVisible().catch(() => false)) await press(price, "accept-price");
const freeze = page.locator('[data-testid="rev-v3-freeze-routes"]');
for (let i = 0; i < 3; i += 1) {
  if (!(await freeze.first().isVisible().catch(() => false))) break;
  await press(freeze, `freeze-${i}`, 60000);
  await page.waitForTimeout(5000);
  const refresh = page.getByRole("button", { name: /刷新方案/ });
  if (await refresh.first().isVisible().catch(() => false)) { await press(refresh, `refresh-${i}`); await page.waitForTimeout(4000); }
}

const select = page.locator('[data-testid="rev-plan-select"]');
for (let i = 0; i < 3; i += 1) {
  if (!(await select.first().isVisible().catch(() => false))) break;
  const selCount = await select.count();
  note("SELECT_CARDS " + selCount);
  if (!(await press(select.nth(Math.max(0, selCount - 1)), `select-${i}`, 20000))) break;
  await page.waitForTimeout(5000);
  const alerts = await page.locator('[role="alert"]').allInnerTexts().catch(() => []);
  note("ALERTS " + JSON.stringify(alerts.slice(0, 3)));
  if (!alerts.some((a) => /排不下|不开放/.test(a))) break;
}

const start = page.locator('[data-testid="rev-plan-start"]');
note("START_VISIBLE " + await start.first().isVisible().catch(() => false));
if (await press(start, "start-trip", 20000)) {
  await page.waitForTimeout(8000);
}
note("AFTER_HEAD " + JSON.stringify((await body()).slice(0, 700)));
await shot("go-live-430-after");
await ctx.close();
