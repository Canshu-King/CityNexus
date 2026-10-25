import { chromium } from "file:///D:/moodle/_cmdr_rescue_v3_1022/frontend/node_modules/playwright/index.mjs";
import fs from "node:fs";
const BASE = "http://127.0.0.1:14493";
const OUT = "D:/moodle/_cmdr_rescue_v3_1022/trial/results/20261022_v3_human_chrome";
const NL = String.fromCharCode(10);
const lines = [];
const note = (v) => { lines.push(v); fs.writeFileSync(OUT + "/classroom-presenter-start-24.txt", lines.join(NL) + NL, "utf8"); };

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
note(`BUTTONS_BEFORE ${await buttons()}`);

const handoff = page.locator('[data-testid="rev-clock-handoff"]');
note(`CLOCK_HANDOFF count=${await handoff.count()}${await handoff.count() ? " " + (await handoff.innerText()).replace(/\s+/g, " ").trim() : ""}`);
note(`CLOCK_NEXT_DISABLED ${await page.locator('[data-testid="rev-clock-next"]').isDisabled().catch(() => "absent")}`);

if ((await read()).includes("尚未开演")) {
  await panel.locator("button", { hasText: "开演" }).click();
  await page.waitForTimeout(2600);
  note(`AFTER_START ${await read()}`);
  note(`BUTTONS_RUNNING ${await buttons()}`);
} else {
  note("START_SKIPPED run already exists");
}

for (let round = 1; round <= 10; round += 1) {
  const status = await read();
  if (!status.includes("模拟进行中")) { note(`ADVANCE_STOP round=${round} status=${status}`); break; }
  await panel.locator("button", { hasText: "走到下一阶段" }).click();
  await page.waitForTimeout(2200);
  note(`AFTER_ADVANCE_${round} ${await read()}`);
}

note(`HISTORY ${JSON.stringify((await page.locator('[data-testid="rev-presenter-history"] li').allInnerTexts()).map((h) => h.replace(/\s+/g, " ").trim()))}`);
const done = page.locator('[data-testid="rev-presenter-done"]');
note(`DONE_NOTE count=${await done.count()}${await done.count() ? " " + (await done.innerText()).replace(/\s+/g, " ").trim() : ""}`);
note(`BUTTONS_FINAL ${await buttons()}`);
await page.screenshot({ path: OUT + "/presenter-finish-24-phone.png", fullPage: false });
note(`SIM_HTTP ${JSON.stringify(sims)}`);
note(`ERRORS ${JSON.stringify(errors.slice(0, 3))}`);
await ctx.close();
await browser.close();
