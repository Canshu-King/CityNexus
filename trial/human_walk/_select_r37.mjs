import { chromium } from "file:///D:/moodle/_cmdr_rescue_v3_1022/frontend/node_modules/playwright/index.mjs";
import fs from "node:fs";

const DIR = "D:/moodle/_cmdr_rescue_v3_1022/trial/results/20261026_gozero";
const OUT = `${DIR}/select-430.txt`;
const NL = String.fromCharCode(10);
const lines = [];
const note = (v) => { lines.push(v); fs.writeFileSync(OUT, lines.join(NL) + NL, "utf8"); };
const bearer = JSON.parse(fs.readFileSync("D:/moodle/_cmdr_v3_live_1022/.gozero_bearer.json", "utf8"));

const ctx = await chromium.launchPersistentContext("D:/moodle/_cmdr_v3_live_1022/_chrome_gozero_1030", {
  channel: "chrome", headless: false, viewport: { width: 430, height: 932 }, deviceScaleFactor: 1,
});
const page = ctx.pages()[0] ?? await ctx.newPage();
const http = [];
page.on("response", (r) => {
  const u = r.url();
  if (!/departure|plans|goal-tasks/.test(u)) return;
  if (!["POST", "PUT"].includes(r.request().method())) return;
  http.push(`${r.status()} ${u.replace(/^http:\/\/[^/]+/, "").slice(0, 100)}`);
});
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
  await page.waitForTimeout(1000);
  return true;
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

const workbench = page.locator('[data-testid="rev-plan-workbench"]');
note("WORKBENCH " + await workbench.count());
if (await workbench.count()) {
  note("CARD " + JSON.stringify((await workbench.first().innerText().catch(() => "")).slice(0, 1200)));
}
await shot("select-430-before");

const select = page.locator('[data-testid="rev-plan-select"]');
note("SELECT_VISIBLE " + await select.first().isVisible().catch(() => false));
if (await press(select, "select-plan", 15000)) {
  await page.waitForTimeout(4000);
  const alerts = await page.locator('[role="alert"]').allInnerTexts().catch(() => []);
  note("ALERTS " + JSON.stringify(alerts.slice(0, 4)));
  const body = await page.evaluate(() => document.body.innerText || "");
  const refusal = (body.match(/(赶路|时间不够|来不及|出发时间|还缺|不能选用|无法选用|规划)[^\n]{0,80}/g) || []).slice(0, 6);
  note("PHRASES " + JSON.stringify(refusal));
  note("AFTER_HEAD " + JSON.stringify(body.slice(0, 700)));
  await shot("select-430-after");
}
note("HTTP " + JSON.stringify(http.slice(-8)));
await ctx.close();
