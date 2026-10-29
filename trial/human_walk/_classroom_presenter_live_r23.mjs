import { chromium } from "file:///D:/moodle/_cmdr_rescue_v3_1022/frontend/node_modules/playwright/index.mjs";
import fs from "node:fs";
const BASE = "http://127.0.0.1:14493";
const OUT = "D:/moodle/_cmdr_rescue_v3_1022/trial/results/20261022_v3_human_chrome";
const NL = String.fromCharCode(10);
const lines = [];
const note = (v) => { lines.push(v); fs.writeFileSync(OUT + "/classroom-presenter-live-23.txt", lines.join(NL) + NL, "utf8"); };

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

await page.goto(BASE + "/revolution", { waitUntil: "networkidle", timeout: 60000 });
await page.waitForTimeout(1200);
await page.locator('[data-testid="rev-mobile-tab-trips"]').click();
await page.waitForTimeout(1000);
await page.locator('[data-testid="rev-demo-session"]').click();
await page.waitForTimeout(3600);

const panel = page.locator('[data-testid="rev-presenter"]');
const count = await panel.count();
const visible = count > 0 && await panel.isVisible().catch(() => false);
note(`PHONE_PRESENTER count=${count} visible=${visible}`);
if (visible) {
  const status = (await page.locator('[data-testid="rev-presenter-run"]').innerText()).replace(/\s+/g, " ").trim();
  note(`STATUS ${status}`);
  note(`CITIES ${(await page.locator('[data-testid="rev-presenter-cities"]').innerText()).replace(/\s+/g, " ").trim()}`);
  const buttons = await panel.locator("button").allInnerTexts();
  note(`BUTTONS ${JSON.stringify(buttons.map((b) => b.replace(/\s+/g, " ").trim()))}`);
  const noteCount = await page.locator('[data-testid="rev-presenter-model-note"]').count();
  note(`MODEL_NOTE count=${noteCount}${noteCount ? " " + (await page.locator('[data-testid="rev-presenter-model-note"]').innerText()).replace(/\s+/g, " ").trim() : ""}`);
  const history = await page.locator('[data-testid="rev-presenter-history"] li').allInnerTexts();
  note(`HISTORY ${JSON.stringify(history.map((h) => h.replace(/\s+/g, " ").trim()))}`);

  await panel.locator("button", { hasText: "刷新读数" }).click();
  await page.waitForTimeout(2200);
  note(`AFTER_REFRESH_STATUS ${(await page.locator('[data-testid="rev-presenter-run"]').innerText()).replace(/\s+/g, " ").trim()}`);

  const resume = panel.locator("button", { hasText: "事件处理完了" });
  if (await resume.count()) {
    await resume.click();
    await page.waitForTimeout(2200);
    const message = page.locator('[data-testid="rev-presenter-message"]');
    note(`RESUME_WITHOUT_RESOLUTION message=${JSON.stringify(await message.count() ? (await message.innerText()).replace(/\s+/g, " ").trim() : "")}`);
  }
  await page.screenshot({ path: OUT + "/presenter-live-23-phone.png", fullPage: false });
}
note(`SIM_HTTP ${JSON.stringify(sims)}`);
note(`ERRORS ${JSON.stringify(errors.slice(0, 3))}`);
await ctx.close();
await browser.close();
