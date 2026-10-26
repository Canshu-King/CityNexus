import { chromium } from "file:///D:/moodle/_cmdr_rescue_v3_1022/frontend/node_modules/playwright/index.mjs";
import fs from "node:fs";

const DIR = "D:/moodle/_cmdr_rescue_v3_1022/trial/results/20261026_gozero";
const OUT = `${DIR}/my-trips-430.txt`;
const NL = String.fromCharCode(10);
const lines = [];
const note = (v) => { lines.push(v); fs.writeFileSync(OUT, lines.join(NL) + NL, "utf8"); };
const bearer = JSON.parse(fs.readFileSync("D:/moodle/_cmdr_v3_live_1022/.gozero_bearer.json", "utf8"));

const ctx = await chromium.launchPersistentContext("D:/moodle/_cmdr_v3_live_1022/_chrome_gozero_1032", {
  channel: "chrome", headless: false, viewport: { width: 430, height: 932 }, deviceScaleFactor: 1,
});
const page = ctx.pages()[0] ?? await ctx.newPage();
let cdp = null;
async function shot(name) {
  try {
    cdp ??= await page.context().newCDPSession(page);
    const { data } = await cdp.send("Page.captureScreenshot", { format: "png" });
    fs.writeFileSync(`${DIR}/${name}.png`, Buffer.from(data, "base64"));
    note("SHOT " + name);
  } catch (e) { note("SHOT_ERR " + String(e).slice(0, 60)); }
}
async function press(loc, label, timeout = 12000) {
  const t = loc.first();
  try { await t.waitFor({ state: "visible", timeout }); } catch { note("MISS " + label); return false; }
  await t.evaluate((n) => n.scrollIntoView({ block: "center" })).catch(() => {});
  await page.waitForTimeout(250);
  const ok = await t.evaluate((node) => {
    const b = node.getBoundingClientRect();
    if (!b.width || !b.height) return false;
    const top = document.elementFromPoint(b.left + b.width / 2, b.top + b.height / 2);
    return Boolean(top) && (node === top || node.contains(top)) && !node.disabled;
  });
  note(`HIT ${label} ${ok}`);
  if (!ok) return false;
  await t.click({ timeout: 15000 }).catch(() => {});
  await page.waitForTimeout(900);
  return true;
}
const extract = async () => {
  const text = await page.evaluate(() => document.body.innerText || "").catch(() => "");
  const pick = (re) => (text.match(re) || [null])[0];
  return {
    first: pick(/第一站[：:][^\n]{0,60}/),
    next: pick(/下一站[^\n]{0,60}/),
    now: pick(/现在[：:][^\n]{0,50}/),
    running: /行程执行中|旅途正在继续/.test(text),
    plan: (text.match(/\d+ 天 · \d+ 项安排/g) || []).slice(0, 3),
  };
};

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
await page.waitForTimeout(3000);
note("TRIPS_BODY " + JSON.stringify((await page.evaluate(() => document.body.innerText || "")).slice(0, 900)));
await shot("my-trips-430-list");

await press(page.getByRole("button", { name: /继续这趟/ }), "continue-trip");
await page.waitForTimeout(3500);
note("BEFORE_RELOAD " + JSON.stringify(await extract()));
await shot("my-trips-430-plan");
await page.reload({ waitUntil: "domcontentloaded" });
await page.waitForTimeout(8000);
note("AFTER_RELOAD " + JSON.stringify(await extract()));
await shot("my-trips-430-reloaded");
await ctx.close();
