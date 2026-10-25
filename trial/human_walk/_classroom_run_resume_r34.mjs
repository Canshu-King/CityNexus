import { chromium } from "file:///D:/moodle/_cmdr_rescue_v3_1022/frontend/node_modules/playwright/index.mjs";
import fs from "node:fs";
const BASE = process.env.SIM_BASE || "http://127.0.0.1:14494";
const TAG = process.env.PROBE_TAG || "";
const TICKET = process.env.PAIR_TICKET || "";
const OUT = "D:/moodle/_cmdr_rescue_v3_1022/trial/results/20261022_v3_human_chrome";
const NL = String.fromCharCode(10);
const lines = [];
const note = (v) => { lines.push(v); fs.writeFileSync(OUT + `/classroom-run-resume-34${TAG}.txt`, lines.join(NL) + NL, "utf8"); };
const clean = (s) => String(s || "").replace(/\s+/g, " ").trim();

const browser = await chromium.launch({ headless: true });
const ctx = await browser.newContext({ viewport: { width: 430, height: 932 }, deviceScaleFactor: 1 });
await ctx.addInitScript(() => {
  if (!sessionStorage.getItem("__probe_booted")) {
    localStorage.clear(); sessionStorage.clear();
    sessionStorage.setItem("__probe_booted", "1");
  }
});
const page = await ctx.newPage();
const errors = [];
page.on("pageerror", (e) => errors.push(String(e).slice(0, 160)));

const read = async (label) => {
  const panel = page.locator('[data-testid="rev-presenter"]');
  const present = await panel.count();
  const banner = page.locator('[data-testid="rev-demo-error-banner"]');
  const bannerCount = await banner.count();
  const state = {
    present,
    status: present ? clean(await page.locator('[data-testid="rev-presenter-run"]').innerText().catch(() => "")) : "",
    message: present ? clean(await page.locator('[data-testid="rev-presenter-message"]').innerText().catch(() => "")) : "",
    history: present ? (await page.locator('[data-testid="rev-presenter-history"] li').allInnerTexts()).map(clean) : [],
    banner: bannerCount ? clean(await banner.first().innerText()) : "",
    tab: clean(await page.locator('[data-testid="rev-mobile-tab-trips"][aria-selected="true"]').count().then((n) => n ? "trips" : "")),
  };
  note(`${label} ${JSON.stringify(state)}`);
  return state;
};

await page.goto(`${BASE}/revolution#pair=${encodeURIComponent(TICKET)}`, { waitUntil: "networkidle", timeout: 60000 });
await page.waitForTimeout(6500);
const first = await read("FIRST");
await page.screenshot({ path: OUT + `/classroom-run-resume-34${TAG}-before.png`, fullPage: false });

await page.reload({ waitUntil: "networkidle", timeout: 60000 });
await page.waitForTimeout(6500);
const after = await read("AFTER_RELOAD");
await page.screenshot({ path: OUT + `/classroom-run-resume-34${TAG}-after.png`, fullPage: false });

await page.reload({ waitUntil: "networkidle", timeout: 60000 });
await page.waitForTimeout(6500);
const twice = await read("AFTER_SECOND_RELOAD");

note(`VERDICT first_present=${first.present} reload_present=${after.present} second_present=${twice.present} errors=${JSON.stringify(errors.slice(0, 3))}`);
await ctx.close();
await browser.close();
