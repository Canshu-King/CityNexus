import { chromium } from "file:///D:/moodle/_cmdr_rescue_v3_1022/frontend/node_modules/playwright/index.mjs";
import fs from "node:fs";
const BASE = "http://127.0.0.1:14493";
const OUT = "D:/moodle/_cmdr_rescue_v3_1022/trial/results/20261022_v3_human_chrome";
const NL = String.fromCharCode(10);
const lines = [];
const note = (v) => { lines.push(v); fs.writeFileSync(OUT + "/classroom-presenter-event-card-25.txt", lines.join(NL) + NL, "utf8"); };

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
const read = async () => (await page.locator('[data-testid="rev-presenter-run"]').innerText()).replace(/\s+/g, " ").trim();
const buttons = async () => JSON.stringify((await page.locator('[data-testid="rev-presenter"] button').allInnerTexts()).map((b) => b.replace(/\s+/g, " ").trim()));

await page.goto(BASE + "/revolution", { waitUntil: "networkidle", timeout: 60000 });
await page.waitForTimeout(1200);
await page.locator('[data-testid="rev-mobile-tab-trips"]').click();
await page.waitForTimeout(1000);
await page.locator('[data-testid="rev-demo-session"]').click();
await page.waitForTimeout(3600);

const panel = page.locator('[data-testid="rev-presenter"]');
note(`PANEL count=${await panel.count()} visible=${await panel.isVisible().catch(() => false)}`);
note(`BEFORE ${await read()}`);

if ((await read()).includes("尚未开演")) {
  await panel.locator("button", { hasText: "开演" }).click();
  await page.waitForTimeout(2600);
  note(`AFTER_START ${await read()}`);
}

const scenes = page.locator('[data-testid="rev-presenter-scenes"]');
note(`SCENES count=${await scenes.count()} text=${JSON.stringify(await scenes.count() ? (await scenes.innerText()).replace(/\s+/g, " ").trim() : "")}`);
note(`BUTTONS_RUNNING ${await buttons()}`);

if (await scenes.count()) {
  await panel.locator("button", { hasText: "闭馆" }).click();
  await page.waitForTimeout(2600);
  note(`AFTER_CLOSURE ${await read()}`);
  note(`BUTTONS_PAUSED ${await buttons()}`);
  note(`HISTORY_PAUSED ${JSON.stringify((await page.locator('[data-testid="rev-presenter-history"] li').allInnerTexts()).map((h) => h.replace(/\s+/g, " ").trim()))}`);

  const guardian = panel.locator("button", { hasText: "交给守护助手" });
  if (await guardian.count()) {
    await guardian.click();
    await page.waitForTimeout(1500);
    const slow = page.locator('[data-testid="rev-presenter-slow"]');
    note(`SLOW_NOTE count=${await slow.count()}${await slow.count() ? " " + (await slow.innerText()).replace(/\s+/g, " ").trim() : ""}`);
    for (let round = 1; round <= 20; round += 1) {
      await page.waitForTimeout(3000);
      const status = await read();
      if (!status.includes("等待守护决策")) { note(`GUARDIAN_SETTLED round=${round} ${status}`); break; }
    }
    note(`AFTER_GUARDIAN ${await read()}`);
    note(`BUTTONS_GUARDIAN ${await buttons()}`);
    const modelNote = page.locator('[data-testid="rev-presenter-model-note"]');
    note(`MODEL_NOTE count=${await modelNote.count()}`);
  }
}

await page.screenshot({ path: OUT + "/presenter-event-card-25-phone.png", fullPage: false });
note(`SIM_HTTP ${JSON.stringify(sims)}`);
note(`ERRORS ${JSON.stringify(errors.slice(0, 3))}`);
await ctx.close();
await browser.close();
