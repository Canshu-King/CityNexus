import { chromium } from "file:///D:/moodle/_cmdr_rescue_v3_1022/frontend/node_modules/playwright/index.mjs";
const BASE = "http://127.0.0.1:14492";
const OUT = "D:/moodle/_cmdr_rescue_v3_1022/trial/results/20261022_v3_human_chrome";
const NL = String.fromCharCode(10);
const fs = await import("node:fs");
const lines = [];
const note = (v) => { lines.push(v); fs.writeFileSync(OUT + "/classroom-phone-card-37.txt", lines.join(NL) + NL, "utf8"); };
const clean = (s) => String(s || "").replace(/\s+/g, " ").trim();

const browser = await chromium.launch({ headless: true });
const ctx = await browser.newContext({ viewport: { width: 430, height: 932 }, deviceScaleFactor: 1 });
await ctx.addInitScript(() => {
  if (!sessionStorage.getItem("__probe_booted")) { localStorage.clear(); sessionStorage.clear(); sessionStorage.setItem("__probe_booted", "1"); }
});
const page = await ctx.newPage();
const errors = [];
page.on("pageerror", (e) => errors.push(String(e).slice(0, 160)));
await page.goto(BASE + "/revolution", { waitUntil: "networkidle", timeout: 60000 });
await page.waitForTimeout(1200);
await page.locator('[data-testid="rev-mobile-tab-trips"]').click();
await page.waitForTimeout(1000);
await page.locator('[data-testid="rev-demo-session"]').click();
await page.waitForTimeout(3600);
await page.getByRole("button", { name: /行程守护/ }).first().click();

const card = page.locator('[data-testid="rev-guardian-proposal"]');
const view = await page.evaluate(() => window.innerHeight);
for (const wait of [400, 1200, 2200, 3600]) {
  await page.waitForTimeout(wait === 400 ? 400 : wait - 400);
  const box = await card.boundingBox().catch(() => null);
  const inside = !!box && box.y >= 0 && box.y + box.height <= view;
  note(`AT_${wait}MS ${JSON.stringify(box)} in_view=${inside} scrollY=${await page.evaluate(() => Math.round(window.scrollY))}`);
}
note(`VALUE_TEXT ${JSON.stringify(clean(await page.locator('[data-testid="rev-guardian-proposal-diff"]').innerText().catch(() => "")))}`);
const accept = page.locator('[data-testid="rev-guardian-accept-replan"]');
const acceptBox = await accept.boundingBox().catch(() => null);
const hit = acceptBox
  ? await page.evaluate(({ x, y }) => {
      const el = document.elementFromPoint(x, y);
      if (!el) return "none";
      return el.closest('[data-testid="rev-guardian-accept-replan"]') ? "self" : (el.className || el.tagName);
    }, { x: acceptBox.x + acceptBox.width / 2, y: acceptBox.y + acceptBox.height / 2 })
  : "no-button";
note(`ACCEPT_BOX ${JSON.stringify(acceptBox)} HIT ${JSON.stringify(hit)}`);
await page.screenshot({ path: OUT + "/classroom-phone-card-37.png", fullPage: false });
note(`ERRORS ${JSON.stringify(errors.slice(0, 3))}`);
await ctx.close();
await browser.close();
