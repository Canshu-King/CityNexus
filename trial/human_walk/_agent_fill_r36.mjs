import { chromium } from "file:///D:/moodle/_cmdr_rescue_v3_1022/frontend/node_modules/playwright/index.mjs";
import fs from "node:fs";

const DIR = "D:/moodle/_cmdr_rescue_v3_1022/trial/results/20261026_gozero";
const OUT = `${DIR}/agent-fill-430.txt`;
const NL = String.fromCharCode(10);
const lines = [];
const note = (v) => { lines.push(v); fs.writeFileSync(OUT, lines.join(NL) + NL, "utf8"); };
const t0 = Date.now();
const el = () => ((Date.now() - t0) / 1000).toFixed(1);

const bearer = JSON.parse(fs.readFileSync("D:/moodle/_cmdr_v3_live_1022/.gozero_bearer.json", "utf8"));
const ctx = await chromium.launchPersistentContext("D:/moodle/_cmdr_v3_live_1022/_chrome_gozero_1026y", {
  channel: "chrome", headless: false, viewport: { width: 430, height: 932 }, deviceScaleFactor: 1,
});
const page = ctx.pages()[0] ?? await ctx.newPage();
const errors = [];
page.on("pageerror", (e) => errors.push(String(e).slice(0, 160)));
page.on("response", (resp) => {
  const url = resp.url();
  if (!/goal-tasks/.test(url)) return;
  if (!["POST", "PUT"].includes(resp.request().method())) return;
  note(`HTTP ${resp.status()} ${url.replace(/^http:\/\/[^/]+/, "").slice(0, 110)}`);
});
let cdp = null;
async function shot(name) {
  try {
    cdp ??= await page.context().newCDPSession(page);
    const { data } = await cdp.send("Page.captureScreenshot", { format: "png" });
    fs.writeFileSync(`${DIR}/${name}.png`, Buffer.from(data, "base64"));
    note(`SHOT ${name} t=${el()}`);
  } catch (e) { note("SHOT_ERR " + String(e).slice(0, 80)); }
}
async function press(loc, label, timeout = 12000) {
  const target = loc.first();
  try { await target.waitFor({ state: "visible", timeout }); } catch { note(`MISS ${label} t=${el()}`); return false; }
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
  await page.waitForTimeout(900);
  return true;
}
const body = () => page.evaluate(() => document.body.innerText || "").catch(() => "");
const pending = async () => ((await body()).match(/地点待定/g) || []).length;

await page.goto("http://127.0.0.1:14461/revolution", { waitUntil: "domcontentloaded", timeout: 60000 });
await page.evaluate(([token, traveler, journey, taskId]) => {
  sessionStorage.setItem("citynexus.traveler.bearer", token);
  sessionStorage.setItem("citynexus.traveler.session-id", traveler);
  localStorage.setItem("citynexus.v8.journey_id", journey);
  if (taskId) localStorage.setItem("citynexus.revolution.goal-task." + traveler + "." + journey, taskId);
}, [bearer.access_token, bearer.traveler_id, bearer.journey_id, bearer.task_id]);
await page.reload({ waitUntil: "domcontentloaded" });
await page.waitForTimeout(7000);
await press(page.getByRole("button", { name: /我的旅程/ }), "journey-tab", 12000);
await page.waitForTimeout(2500);
await press(page.getByRole("button", { name: /继续这趟/ }), "continue-trip", 12000);
await page.waitForTimeout(3000);
note(`PENDING_BEFORE ${await pending()}`);

const askAgent = page.getByRole("button", { name: /和 Agent 补齐出发资料/ });
if (!(await press(askAgent, "ask-agent", 12000))) {
  note("ASK_AGENT_MISSING");
} else {
  await page.waitForTimeout(1200);
  await press(page.getByRole("button", { name: /^发送/ }), "send", 12000);
  const end = Date.now() + 8 * 60 * 1000;
  let sawBusy = false;
  let i = 0;
  while (Date.now() < end) {
    await page.waitForTimeout(10000);
    i += 1;
    const text = await body();
    const busy = /正在研究|回复中|Agent 正在处理|正在查询/.test(text);
    if (busy) sawBusy = true;
    const left = (text.match(/地点待定/g) || []).length;
    if (i % 3 === 0) note(`TICK ${i} busy=${busy} pending=${left} t=${el()}`);
    if (!busy && sawBusy && i > 2) { note(`IDLE t=${el()} pending=${left}`); break; }
  }
}
note(`PENDING_AFTER ${await pending()}`);
const text = await body();
const lack = (text.match(/这版方案还缺：[^\n]{0,160}/) || [null])[0];
note(`LACK ${JSON.stringify(lack)}`);
note(`BODY_TAIL ${JSON.stringify(text.slice(-900))}`);
await shot("agent-fill-430-after");
note(`ERRORS ${JSON.stringify(errors.slice(0, 3))}`);
await ctx.close();
