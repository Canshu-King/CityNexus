import { chromium } from "file:///D:/moodle/_cmdr_rescue_v3_1022/frontend/node_modules/playwright/index.mjs";
import fs from "node:fs";

const DIR = "D:/moodle/_cmdr_rescue_v3_1022/trial/results/20261026_gozero";
const OUT = `${DIR}/half-day-430.txt`;
const NL = String.fromCharCode(10);
const lines = [];
const note = (v) => { lines.push(v); fs.writeFileSync(OUT, lines.join(NL) + NL, "utf8"); };
const t0 = Date.now();
const el = () => ((Date.now() - t0) / 1000).toFixed(1);

const ctx = await chromium.launchPersistentContext("D:/moodle/_cmdr_v3_live_1022/_chrome_gozero_1026w", {
  channel: "chrome", headless: false, viewport: { width: 390, height: 844 }, deviceScaleFactor: 1,
});
const page = ctx.pages()[0] ?? await ctx.newPage();
const errors = [];
page.on("pageerror", (e) => errors.push(String(e).slice(0, 160)));
let cdp = null;
async function shot(name) {
  try {
    cdp ??= await page.context().newCDPSession(page);
    const { data } = await cdp.send("Page.captureScreenshot", { format: "png" });
    fs.writeFileSync(`${DIR}/${name}.png`, Buffer.from(data, "base64"));
    note(`SHOT_CDP ${name} t=${el()}`);
  } catch (e) { note(`SHOT_ERR ${name} ${String(e).slice(0, 80)}`); }
}
const bodyText = () => page.evaluate(() => document.body.innerText || "").catch(() => "");
async function visible(loc) { try { return await loc.first().isVisible(); } catch { return false; } }
async function press(loc, label, timeout = 10000) {
  const target = loc.first();
  try { await target.waitFor({ state: "visible", timeout }); } catch { note(`MISS ${label}`); return false; }
  await target.evaluate((n) => n.scrollIntoView({ block: "center" })).catch(() => {});
  await page.waitForTimeout(250);
  const ok = await target.evaluate((node) => {
    const b = node.getBoundingClientRect();
    if (!b.width || !b.height) return false;
    const top = document.elementFromPoint(b.left + b.width / 2, b.top + b.height / 2);
    return Boolean(top) && (node === top || node.contains(top)) && !node.disabled;
  });
  note(`HIT ${label} ${ok} t=${el()}`);
  if (!ok) return false;
  await target.click({ timeout: 15000 }).catch(() => {});
  await page.waitForTimeout(800);
  return true;
}

async function openDraft() {
  await press(page.getByRole("button", { name: /我的旅程/ }), "journey-tab", 12000);
  await page.waitForTimeout(2200);
  await press(page.getByRole("button", { name: /继续这趟/ }), "continue-trip", 12000);
  await page.waitForTimeout(6000);
  await page.locator('section[aria-label="可编辑旅行草案"]').waitFor({ state: "visible", timeout: 15000 }).catch(() => {});
  await press(page.getByRole("button", { name: /按天调整行程/ }), "day-tab", 12000);
  await page.waitForTimeout(1500);
}
async function daySlots(dayIndex) {
  await press(page.locator(`#rev-v3-day-tab-${dayIndex}`), `day-${dayIndex}`, 8000);
  await page.waitForTimeout(600);
  const panel = page.locator(`#rev-v3-day-${dayIndex}`);
  const slots = panel.locator("details.rev-goal-draft-slot");
  const total = await slots.count();
  const out = [];
  for (let i = 0; i < total; i += 1) {
    const text = (await slots.nth(i).locator("summary").first().innerText().catch(() => "")).replace(/\s+/g, " ").trim();
    out.push(text);
  }
  return out;
}

const bearer = JSON.parse(fs.readFileSync("D:/moodle/_cmdr_v3_live_1022/.gozero_bearer.json", "utf8"));
await page.goto("http://127.0.0.1:14461/revolution", { waitUntil: "domcontentloaded", timeout: 60000 });
await page.evaluate(([token, traveler, journey, taskId]) => {
  sessionStorage.setItem("citynexus.traveler.bearer", token);
  sessionStorage.setItem("citynexus.traveler.session-id", traveler);
  localStorage.setItem("citynexus.v8.journey_id", journey);
  if (taskId) localStorage.setItem("citynexus.revolution.goal-task." + traveler + "." + journey, taskId);
}, [bearer.access_token, bearer.traveler_id, bearer.journey_id, bearer.task_id]);
await page.reload({ waitUntil: "domcontentloaded" });
await page.waitForTimeout(8000);
note("SESSION_SET task=" + String(bearer.task_id).slice(0, 8));
note(`ENTER ${JSON.stringify((await bodyText()).slice(0, 120))}`);
await openDraft();
const editor = page.locator('section[aria-label="可编辑旅行草案"]');
note(`EDITOR ${await editor.count()}`);
if (!(await editor.count())) { note("NO_EDITOR"); note(`BODY ${JSON.stringify((await bodyText()).slice(0, 300))}`); await ctx.close(); process.exit(0); }

const before1 = await daySlots(0);
const before2 = await daySlots(1);
note(`BEFORE_DAY1 ${JSON.stringify(before1)}`);
note(`BEFORE_DAY2 ${JSON.stringify(before2)}`);
await shot("half-day-430-before");

const day2 = page.locator("#rev-v3-day-1");
const targetIndex = before2.findIndex((text) => /下午/.test(text)) >= 0
  ? before2.findIndex((text) => /下午/.test(text)) : 0;
const slot = day2.locator("details.rev-goal-draft-slot").nth(targetIndex);
await slot.locator("summary").first().click().catch(() => {});
await page.waitForTimeout(500);
const titleInput = slot.locator('label:has-text("安排") input').first();
const oldTitle = await titleInput.inputValue().catch(() => "");
await titleInput.fill(`${oldTitle}（只改这一段）`).catch(() => {});
note(`TYPED day2 slot=${targetIndex} old=${JSON.stringify(oldTitle)}`);
await page.waitForTimeout(400);

const save = editor.getByRole("button", { name: /保存草案/ });
const saved = await press(save, "save-draft", 15000);
let savedText = "";
if (saved) {
  for (let i = 0; i < 20; i += 1) {
    await page.waitForTimeout(1200);
    const text = await bodyText();
    const mark = (text.match(/草案已保存到这趟旅行|保存失败.{0,40}|请补一个标题.{0,40}/) || [null])[0];
    if (mark) { savedText = mark; break; }
  }
}
note(`SAVE_RESULT ${JSON.stringify(savedText)}`);

await openDraft();
const after1 = await daySlots(0);
const after2 = await daySlots(1);
note(`AFTER_DAY1 ${JSON.stringify(after1)}`);
note(`AFTER_DAY2 ${JSON.stringify(after2)}`);
note(`DAY1_UNCHANGED ${JSON.stringify(before1) === JSON.stringify(after1)}`);
const changed = after2.filter((text, i) => before2[i] !== text);
note(`DAY2_CHANGED ${JSON.stringify(changed)}`);
await shot("half-day-430-after");
note(`ERRORS ${JSON.stringify(errors.slice(0, 3))}`);
await ctx.close();
