import { chromium } from "file:///D:/moodle/_cmdr_rescue_v3_1022/frontend/node_modules/playwright/index.mjs";
import fs from "node:fs";
const BASE = process.env.SIM_BASE || "http://10.12.35.143:14492";
const OUT = "D:/moodle/_cmdr_rescue_v3_1022/trial/results/20261022_v3_human_chrome";
const NL = String.fromCharCode(10);
const lines = [];
const started = Date.now();
const note = (v) => { lines.push(v); fs.writeFileSync(OUT + "/classroom-lan-path-27.txt", lines.join(NL) + NL, "utf8"); };
const mark = (s) => note(`STEP ${s} t=${((Date.now() - started) / 1000).toFixed(1)}s`);

const browser = await chromium.launch({ headless: true });
const ctx = await browser.newContext({ viewport: { width: 430, height: 932 }, deviceScaleFactor: 1 });
await ctx.addInitScript(() => {
  if (!sessionStorage.getItem("__probe_booted")) { localStorage.clear(); sessionStorage.clear(); sessionStorage.setItem("__probe_booted", "1"); }
});
const page = await ctx.newPage();
const errors = [];
page.on("pageerror", (e) => errors.push(String(e).slice(0, 160)));
note(`BASE ${BASE}`);

await page.goto(BASE + "/revolution", { waitUntil: "networkidle", timeout: 45000 }).catch((e) => note(`GOTO_ERROR ${String(e).slice(0, 120)}`));
await page.waitForTimeout(1400); mark("open");
await page.locator('[data-testid="rev-mobile-tab-trips"]').click();
await page.waitForTimeout(1000); mark("trips");
await page.locator('[data-testid="rev-demo-session"]').click();
await page.waitForTimeout(3600); mark("demo");

const clock = page.locator('[data-testid="rev-classroom-clock"]');
note(`CLOCK_VISIBLE ${await clock.isVisible().catch(() => false)}`);
note(`CLOCK_TEXT ${JSON.stringify((await clock.innerText().catch(() => "")).replace(/\s+/g, " ").slice(0, 200))}`);
await page.getByRole("button", { name: /行程守护/ }).first().click();
await page.waitForTimeout(2400);
mark("guardian");
const proposal = page.locator('[data-testid="rev-guardian-proposal"]');
note(`PROPOSAL_COUNT ${await proposal.count()}`);
if (await proposal.count()) {
  note(`PROPOSAL_TEXT ${JSON.stringify((await page.locator('[data-testid="rev-guardian-proposal-diff"]').innerText().catch(() => "")).replace(/\s+/g, " ").trim())}`);
}
const dot = page.locator('[data-testid="rev-map-traveller-state"]');
note(`BLUE_DOT count=${await dot.count()}`);
note(`DOT_STATE ${JSON.stringify((await dot.innerText().catch(() => "")).replace(/\s+/g, " ").slice(0, 160))}`);
const presenter = page.locator('[data-testid="rev-presenter"]');
note(`PRESENTER_COUNT ${await presenter.count()}（课堂后端没有 simulation 端点时应为 0）`);
note(`TITLE ${JSON.stringify(await page.title())}`);
await page.screenshot({ path: OUT + "/classroom-lan-27-phone.png", fullPage: false });
await page.screenshot({ path: OUT + "/classroom-lan-27-guardian.png", fullPage: false });
note(`ERRORS ${JSON.stringify(errors.slice(0, 3))}`);
await ctx.close();
await browser.close();
