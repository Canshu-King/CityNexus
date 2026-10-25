import { chromium } from "file:///D:/moodle/_cmdr_rescue_v3_1022/frontend/node_modules/playwright/index.mjs";
import fs from "node:fs";
const BASE = process.env.SIM_BASE || "http://127.0.0.1:14494";
const TICKET = process.env.PAIR_TICKET || "";
const OUT = "D:/moodle/_cmdr_rescue_v3_1022/trial/results/20261022_v3_human_chrome";
const NL = String.fromCharCode(10);
const lines = [];
const started = Date.now();
const note = (v) => { lines.push(v); fs.writeFileSync(OUT + "/classroom-two-day-loop-31.txt", lines.join(NL) + NL, "utf8"); };
const mark = (s) => note(`STEP ${s} t=${((Date.now() - started) / 1000).toFixed(1)}s`);

const browser = await chromium.launch({ headless: true });
const ctx = await browser.newContext({ viewport: { width: 430, height: 932 }, deviceScaleFactor: 1 });
await ctx.addInitScript(() => {
  if (!sessionStorage.getItem("__probe_booted")) { localStorage.clear(); sessionStorage.clear(); sessionStorage.setItem("__probe_booted", "1"); }
});
const page = await ctx.newPage();
const errors = [];
const sims = [];
page.on("pageerror", (e) => errors.push(String(e).slice(0, 160)));
page.on("response", (r) => {
  const url = r.url();
  if (url.includes("/simulation/") && !url.includes("/demo/simulation-clock/")) sims.push(`${r.request().method()} ${r.status()}`);
});
const statusText = async () => (await page.locator('[data-testid="rev-presenter-run"]').innerText()).replace(/\s+/g, " ").trim();

await page.goto(`${BASE}/revolution#pair=${encodeURIComponent(TICKET)}`, { waitUntil: "networkidle", timeout: 60000 });
await page.waitForTimeout(4500);
const panel = page.locator('[data-testid="rev-presenter"]');
note(`PANEL count=${await panel.count()} visible=${await panel.isVisible().catch(() => false)}`);
note(`BEFORE ${await statusText().catch(() => "")}`);
mark("entered");

if ((await statusText().catch(() => "")).includes("尚未开演")) {
  await panel.locator("button", { hasText: "开演" }).click();
  await page.waitForTimeout(2800);
  note(`AFTER_START ${await statusText()}`);
  mark("started");
}
await panel.locator("button", { hasText: "闭馆" }).click();
await page.waitForTimeout(2600);
note(`AFTER_SCENE ${await statusText()}`);
mark("scene");

await panel.locator("button", { hasText: "交给守护助手" }).click();
await page.waitForTimeout(1500);
note(`SLOW ${JSON.stringify(await page.locator('[data-testid="rev-presenter-slow"]').innerText().catch(() => ""))}`);
let settled = "";
for (let round = 1; round <= 75; round += 1) {
  await page.waitForTimeout(8000);
  settled = await statusText();
  if (!settled.includes("等待守护决策") && !settled.includes("守护正在分析")) { note(`GUARDIAN_SETTLED round=${round} ${settled}`); break; }
}
note(`AFTER_GUARDIAN ${settled}`);
mark("guardian");

await page.getByRole("button", { name: /行程守护/ }).first().click();
await page.waitForTimeout(2400);
let proposal = "";
for (let round = 1; round <= 20; round += 1) {
  proposal = await page.locator('[data-testid="rev-guardian-proposal-diff"]').innerText().catch(() => "");
  if (proposal) break;
  await page.waitForTimeout(3000);
}
note(`PROPOSAL ${JSON.stringify(proposal.replace(/\s+/g, " ").trim())}`);
const accept = page.locator('[data-testid="rev-guardian-accept-replan"]');
note(`ACCEPT_BUTTON ${await accept.count()}`);
if (await accept.count()) {
  await accept.click();
  await page.waitForTimeout(6500);
  mark("accepted");
}
const presenter = page.locator('[data-testid="rev-presenter"]');
await presenter.scrollIntoViewIfNeeded().catch(() => {});
await page.waitForTimeout(800);
note(`STATUS_AFTER_ACCEPT ${await statusText()}`);
const resume = presenter.locator("button", { hasText: "继续模拟" });
note(`RESUME_BUTTON ${await resume.count()}`);
if (await resume.count()) {
  await resume.click();
  await page.waitForTimeout(3200);
  mark("resumed");
}
note(`AFTER_RESUME ${await statusText()}`);
for (let round = 1; round <= 10; round += 1) {
  const status = await statusText();
  if (!status.includes("模拟进行中")) break;
  const advance = presenter.locator("button", { hasText: "走到下一阶段" });
  if (!(await advance.count())) break;
  await advance.click();
  await page.waitForTimeout(2400);
  note(`ADVANCE_${round} ${await statusText()}`);
}
note(`FINAL ${await statusText()}`);
note(`HISTORY ${JSON.stringify((await page.locator('[data-testid="rev-presenter-history"] li').allInnerTexts()).map((h) => h.replace(/\s+/g, " ").trim()))}`);
await page.screenshot({ path: OUT + "/classroom-two-day-loop-31-phone.png", fullPage: false });
note(`SIM_HTTP ${JSON.stringify(sims)}`);
note(`ERRORS ${JSON.stringify(errors.slice(0, 3))}`);
await ctx.close();
await browser.close();
