import { chromium } from "file:///D:/moodle/_cmdr_rescue_v3_1022/frontend/node_modules/playwright/index.mjs";
import fs from "node:fs";
const BASE = "http://127.0.0.1:14492";
const OUT = "D:/moodle/_cmdr_rescue_v3_1022/trial/results/20261022_v3_human_chrome";
const NL = String.fromCharCode(10);
const lines = [];
const note = (v) => { lines.push(v); fs.writeFileSync(OUT + "/classroom-ai-state-44.txt", lines.join(NL) + NL, "utf8"); };
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
await page.waitForTimeout(3500);
const runtime = await page.evaluate(async () => {
  try {
    const answer = await fetch("/api/v1/agent/runtime-status", { headers: { Accept: "application/json" } });
    const body = await answer.json();
    return { status: answer.status, ai_state: body.ai_state, runtime_identity: body.runtime_identity };
  } catch (error) {
    return { status: 0, error: String(error).slice(0, 80) };
  }
});
note(`RUNTIME ${JSON.stringify(runtime)}`);
note(`HEADER_TITLE ${JSON.stringify(clean(await page.locator('[data-testid="revolution-agent-runtime"] summary').innerText().catch(() => "")))}`);
note(`AI_SERVICE_LINE ${JSON.stringify(clean((await page.evaluate(() => document.body.innerText)).split("AI 服务")[1]?.split(NL)[0] || ""))}`);
await page.screenshot({ path: OUT + "/classroom-ai-state-44-home.png", fullPage: false });
await page.locator('[data-testid="rev-mobile-tab-trips"]').click();
await page.waitForTimeout(1200);
note(`AFTER_TRIPS_TITLE ${JSON.stringify(clean(await page.locator('[data-testid="revolution-agent-runtime"] summary').innerText().catch(() => "")))}`);
await page.screenshot({ path: OUT + "/classroom-ai-state-44-trips.png", fullPage: false });
note(`ERRORS ${JSON.stringify(errors.slice(0, 3))}`);
await ctx.close();
await browser.close();
