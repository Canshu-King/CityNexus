import { chromium } from "file:///D:/moodle/_cmdr_rescue_v3_1022/frontend/node_modules/playwright/index.mjs";
import fs from "node:fs";
const BASE = "http://127.0.0.1:14492";
const OUT = "D:/moodle/_cmdr_rescue_v3_1022/trial/results/20261022_v3_human_chrome";
const NL = String.fromCharCode(10);
const lines = [];
const started = Date.now();
const note = (v) => { lines.push(v); fs.writeFileSync(OUT + "/classroom-touch-order-52.txt", lines.join(NL) + NL, "utf8"); };
const mark = (s) => note(`STEP ${s} t=${((Date.now() - started) / 1000).toFixed(1)}s`);
const clean = (s) => String(s || "").replace(/\s+/g, " ").trim();

const browser = await chromium.launch({ headless: true });
const ctx = await browser.newContext({ viewport: { width: 430, height: 932 }, deviceScaleFactor: 2, hasTouch: true, isMobile: true });
await ctx.addInitScript(() => {
  if (!sessionStorage.getItem("__probe_booted")) { localStorage.clear(); sessionStorage.clear(); sessionStorage.setItem("__probe_booted", "1"); }
});
const page = await ctx.newPage();
const errors = [];
page.on("pageerror", (e) => errors.push(String(e).slice(0, 160)));
await page.goto(BASE + "/revolution", { waitUntil: "networkidle", timeout: 60000 });
await page.waitForTimeout(1400);
await page.locator('[data-testid="rev-mobile-tab-trips"]').tap();
await page.waitForTimeout(1000);
await page.locator('[data-testid="rev-demo-session"]').tap();
await page.waitForTimeout(3600); mark("demo");

await page.getByRole("button", { name: /地图/ }).first().tap();
await page.waitForTimeout(1200); mark("map-tab");
const load = page.getByRole("button", { name: /加载地图/ }).first();
note(`LOAD_BUTTON ${await load.count()}`);
await load.tap().catch(() => {});
await page.waitForTimeout(3200); mark("map-loaded");
note(`DOT_AFTER_MAP ${JSON.stringify(clean(await page.locator('[data-testid="rev-map-traveller-state"]').innerText().catch(() => "")))}`);

await page.getByRole("button", { name: /执行与待办/ }).first().tap();
await page.waitForTimeout(1400); mark("back-to-todo");
await page.getByRole("button", { name: /行程守护/ }).first().tap();
await page.waitForTimeout(2400); mark("guardian");
const card = page.locator('[data-testid="rev-guardian-proposal"]');
note(`CARD ${await card.count()} TEXT ${JSON.stringify(clean(await page.locator('[data-testid="rev-guardian-proposal-diff"]').innerText().catch(() => "")))}`);
const accept = page.locator('[data-testid="rev-guardian-accept-replan"]');
const acceptBox = await accept.boundingBox().catch(() => null);
const acceptHit = acceptBox
  ? await page.evaluate(({ x, y }) => {
      const el = document.elementFromPoint(x, y);
      return el ? (el.closest('[data-testid="rev-guardian-accept-replan"]') ? "self" : (el.className || el.tagName)) : "none";
    }, { x: acceptBox.x + acceptBox.width / 2, y: acceptBox.y + acceptBox.height / 2 })
  : "no-button";
note(`ACCEPT_HIT ${JSON.stringify(acceptHit)}`);
await accept.tap().catch(() => {});
await page.waitForTimeout(5600); mark("accepted");
let body = "";
for (let i = 0; i < 5; i += 1) {
  body = await page.evaluate(() => document.body.innerText);
  if (/第一站：/.test(body)) break;
  await page.waitForTimeout(1200);
}
note(`FIRST_STOP_AFTER_ACCEPT ${JSON.stringify(clean((body.split("第一站：")[1] || "").split(NL)[0]))}`);
await page.screenshot({ path: OUT + "/classroom-touch-order-52-after.png", fullPage: false });

await page.reload({ waitUntil: "networkidle", timeout: 60000 });
await page.waitForTimeout(4200); mark("reloaded");
body = await page.evaluate(() => document.body.innerText);
note(`FIRST_STOP_AFTER_RELOAD ${JSON.stringify(clean((body.split("第一站：")[1] || "").split(NL)[0]))}`);
note(`CLOCK_AFTER_RELOAD ${JSON.stringify(clean(await page.locator('[data-testid="rev-clock-virtual"]').innerText().catch(() => "")))}`);
await page.screenshot({ path: OUT + "/classroom-touch-order-52-reload.png", fullPage: false });
note(`TOTAL_S ${((Date.now() - started) / 1000).toFixed(1)}`);
note(`ERRORS ${JSON.stringify(errors.slice(0, 3))}`);
await ctx.close();
await browser.close();
