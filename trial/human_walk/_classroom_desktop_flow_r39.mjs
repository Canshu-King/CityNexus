import { chromium } from "file:///D:/moodle/_cmdr_rescue_v3_1022/frontend/node_modules/playwright/index.mjs";
import fs from "node:fs";
const BASE = "http://127.0.0.1:14492";
const OUT = "D:/moodle/_cmdr_rescue_v3_1022/trial/results/20261022_v3_human_chrome";
const NL = String.fromCharCode(10);
const lines = [];
const started = Date.now();
const note = (v) => { lines.push(v); fs.writeFileSync(OUT + "/classroom-desktop-flow-39.txt", lines.join(NL) + NL, "utf8"); };
const mark = (s) => note(`STEP ${s} t=${((Date.now() - started) / 1000).toFixed(1)}s`);
const clean = (s) => String(s || "").replace(/\s+/g, " ").trim();

const browser = await chromium.launch({ headless: true });
const ctx = await browser.newContext({ viewport: { width: 1280, height: 900 }, deviceScaleFactor: 1 });
await ctx.addInitScript(() => {
  if (!sessionStorage.getItem("__probe_booted")) { localStorage.clear(); sessionStorage.clear(); sessionStorage.setItem("__probe_booted", "1"); }
});
const page = await ctx.newPage();
const errors = [];
page.on("pageerror", (e) => errors.push(String(e).slice(0, 160)));
await page.goto(BASE + "/revolution", { waitUntil: "networkidle", timeout: 60000 });
await page.waitForTimeout(1400); mark("open");
await page.locator('[data-testid="rev-mobile-tab-trips"]').click();
await page.waitForTimeout(1000); mark("trips");
await page.locator('[data-testid="rev-demo-session"]').click();
await page.waitForTimeout(3600); mark("demo");
await page.screenshot({ path: OUT + "/classroom-desktop-flow-39-1-entry.png", fullPage: false });

await page.getByRole("button", { name: /行程守护/ }).first().click();
await page.waitForTimeout(2400); mark("guardian");
const card = page.locator('[data-testid="rev-guardian-proposal"]');
const box = await card.boundingBox().catch(() => null);
note(`CARD_BOX ${JSON.stringify(box)}`);
note(`CARD_TEXT ${JSON.stringify(clean(await page.locator('[data-testid="rev-guardian-proposal-diff"]').innerText().catch(() => "")))}`);
await page.screenshot({ path: OUT + "/classroom-desktop-flow-39-2-card.png", fullPage: false });

const accept = page.locator('[data-testid="rev-guardian-accept-replan"]');
const acceptBox = await accept.boundingBox().catch(() => null);
const hit = acceptBox
  ? await page.evaluate(({ x, y }) => {
      const el = document.elementFromPoint(x, y);
      return el ? (el.closest('[data-testid="rev-guardian-accept-replan"]') ? "self" : (el.className || el.tagName)) : "none";
    }, { x: acceptBox.x + acceptBox.width / 2, y: acceptBox.y + acceptBox.height / 2 })
  : "no-button";
note(`ACCEPT_HIT ${JSON.stringify(hit)}`);
await accept.click({ timeout: 8000 }).catch((e) => note(`ACCEPT_CLICK_ERROR ${String(e).slice(0, 120)}`));
await page.waitForTimeout(5200); mark("accept");
let body = "";
for (let i = 0; i < 5; i++) {
  body = await page.evaluate(() => document.body.innerText);
  if (/第一站：/.test(body)) break;
  await page.waitForTimeout(1200);
}
note(`AFTER_FIRST_STOP ${JSON.stringify(clean((body.split("第一站：")[1] || "").split(NL)[0]))}`);
note(`AFTER_SCROLL ${JSON.stringify(await page.evaluate(() => ({ y: Math.round(window.scrollY), height: document.body.scrollHeight, view: window.innerHeight })))}`);
const firstStop = page.locator("text=第一站：").first();
const stopBox = await firstStop.boundingBox().catch(() => null);
note(`FIRST_STOP_BOX ${JSON.stringify(stopBox)}`);
note(`FIRST_STOP_IN_VIEW ${JSON.stringify(!!stopBox && stopBox.y >= 0 && stopBox.y + stopBox.height <= 900)}`);
await page.evaluate(() => window.scrollTo({ top: 0, behavior: "instant" }));
await page.waitForTimeout(600);
await page.screenshot({ path: OUT + "/classroom-desktop-flow-39-3b-top.png", fullPage: false });
await page.screenshot({ path: OUT + "/classroom-desktop-flow-39-3-after.png", fullPage: false });
note(`TOTAL_S ${((Date.now() - started) / 1000).toFixed(1)}`);
note(`ERRORS ${JSON.stringify(errors.slice(0, 3))}`);
await ctx.close();
await browser.close();
