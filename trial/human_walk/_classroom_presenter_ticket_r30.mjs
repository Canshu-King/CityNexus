import { chromium } from "file:///D:/moodle/_cmdr_rescue_v3_1022/frontend/node_modules/playwright/index.mjs";
import fs from "node:fs";
const BASE = process.env.SIM_BASE || "http://127.0.0.1:14493";
const TICKET = process.env.PAIR_TICKET || "";
const OUT = "D:/moodle/_cmdr_rescue_v3_1022/trial/results/20261022_v3_human_chrome";
const NL = String.fromCharCode(10);
const lines = [];
const note = (v) => { lines.push(v); fs.writeFileSync(OUT + "/classroom-presenter-ticket-30.txt", lines.join(NL) + NL, "utf8"); };

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
note(`CLOCK_NEXT_DISABLED ${await page.locator('[data-testid="rev-clock-next"]').isDisabled().catch(() => "absent")}`);

if ((await statusText().catch(() => "")).includes("尚未开演")) {
  await panel.locator("button", { hasText: "开演" }).click();
  await page.waitForTimeout(2800);
  note(`AFTER_START ${await statusText()}`);
}
const advance = panel.locator("button", { hasText: "走到下一阶段" });
if (await advance.count()) {
  await advance.click();
  await page.waitForTimeout(2400);
  note(`AFTER_ADVANCE ${await statusText()}`);
}
note(`CLOCK_NEXT_DISABLED_AFTER ${await page.locator('[data-testid="rev-clock-next"]').isDisabled().catch(() => "absent")}`);
note(`HANDOFF ${JSON.stringify(await page.locator('[data-testid="rev-clock-handoff"]').innerText().catch(() => ""))}`);
note(`HISTORY ${JSON.stringify((await page.locator('[data-testid="rev-presenter-history"] li').allInnerTexts()).map((h) => h.replace(/\s+/g, " ").trim()))}`);
await page.screenshot({ path: OUT + "/classroom-presenter-ticket-30-phone.png", fullPage: false });
note(`SIM_HTTP ${JSON.stringify(sims)}`);
note(`ERRORS ${JSON.stringify(errors.slice(0, 3))}`);
await ctx.close();
await browser.close();
