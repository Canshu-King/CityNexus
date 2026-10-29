import { chromium } from "file:///D:/moodle/_cmdr_rescue_v3_1022/frontend/node_modules/playwright/index.mjs";
import fs from "node:fs";

const BASE = process.env.PAIR_BASE || "http://127.0.0.1:14495";
const OUT = "D:/moodle/_cmdr_rescue_v3_1022/trial/results/20261022_v3_human_chrome/console-blip-71.txt";
const TICKET = process.env.PAIR_TICKET || "";
const NL = String.fromCharCode(10);
const lines = [];
const note = (value) => { lines.push(value); fs.writeFileSync(OUT, lines.join(NL) + NL, "utf8"); };
const clean = (value) => String(value || "").replace(/\s+/g, " ").trim();

const browser = await chromium.launch({ headless: true });
const ctx = await browser.newContext({ viewport: { width: 390, height: 844 }, deviceScaleFactor: 1 });
const page = await ctx.newPage();
const errors = [];
page.on("pageerror", (error) => errors.push(String(error).slice(0, 160)));

await page.goto(`${BASE}/revolution#pair=${encodeURIComponent(TICKET)}`, { waitUntil: "networkidle", timeout: 60000 });
await page.waitForTimeout(4200);
if (!(await page.locator('[data-testid="rev-classroom-clock"]').count())) {
  await page.locator('[data-testid="rev-mobile-tab-trips"]').click().catch(() => {});
  await page.waitForTimeout(1200);
}
const start = page.getByRole("button", { name: /开演/ }).first();
if (await start.count()) { await start.scrollIntoViewIfNeeded().catch(() => {}); await start.click().catch(() => {}); }
await page.waitForTimeout(5000);
note(`RUN_OWNED ${await page.locator('[data-testid="rev-clock-run"]').count()}`);
note(`PRESENTER_BEFORE ${JSON.stringify(clean(await page.locator('[data-testid="rev-presenter-run"]').first().innerText().catch(() => "")))}`);

// Break the two read endpoints the panel polls, with an HTML gateway error.
const badGateway = (route) => route.fulfill({ status: 502, contentType: "text/html", body: "<html>bad gateway</html>" });
await page.route("**/simulation/runs/*/progress", badGateway);
await page.route("**/api/v1/plans/*", badGateway);
note("ROUTES_BROKEN progress+plans=502-html");
await page.waitForTimeout(13000);

note(`PRESENTER_VISIBLE ${await page.locator('[data-testid="rev-presenter"]').count()}`);
note(`PRESENTER_AFTER ${JSON.stringify(clean(await page.locator('[data-testid="rev-presenter-run"]').first().innerText().catch(() => "")))}`);
note(`ADVANCE_HINT ${await page.locator('[data-testid="rev-presenter-advance-hint"]').count()}`);
note(`MESSAGE ${JSON.stringify(clean(await page.locator('[data-testid="rev-presenter-message"]').first().innerText().catch(() => "")))}`);
await page.locator('[data-testid="rev-presenter"]').first().scrollIntoViewIfNeeded().catch(() => {});
await page.screenshot({ path: "D:/moodle/_cmdr_rescue_v3_1022/trial/results/20261022_v3_human_chrome/classroom-console-blip-71.png", fullPage: false });
note(`ERRORS ${JSON.stringify(errors.slice(0, 3))}`);
await ctx.close();
await browser.close();
