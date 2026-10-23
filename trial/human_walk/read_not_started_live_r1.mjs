/**
 * Read the departed journey's own screen after the "not started yet" wording landed.
 *
 * walk-89 left a journey ACTIVE on the same canary stack with its first stop dated 5 December; before this
 * change that screen said 正在进行 / 现在的行程 / 下一站.  This opens the app the way a person would from
 * the tab bar, goes to 我的旅程, opens the trip, and reads the live card's kicker, title and lede.
 * Nothing is seeded: whatever the shell has stored for this browser profile is what it restores.
 */
import fs from "node:fs";
import path from "node:path";
import { createRequire } from "node:module";

const require = createRequire("D:/moodle/_cmdr_rescue_v3_1022/frontend/package.json");
const { chromium } = require("playwright");

const SHOTS = "D:/moodle/_cmdr_rescue_v3_1022/trial/results/20261022_v3_human_chrome";
const WEB = process.env.READ_BASE || "http://127.0.0.1:14496/revolution";
const OUT = process.env.READ_LOG || "read-not-started-live-1.txt";
const PREFIX = process.env.READ_SHOT_PREFIX || "notstarted";
const stream = fs.openSync(path.join(SHOTS, OUT), "a");
const flat = (v) => String(v ?? "").replace(/\s+/g, " ").trim();
const say = (line) => { fs.writeSync(stream, line + "\n"); process.stdout.write(line + "\n"); };

const browser = await chromium.connectOverCDP("http://127.0.0.1:9335", { timeout: 150000, slowMo: 0 });
const contexts = browser.contexts();
const urls = contexts.flatMap((candidate) => candidate.pages().map((openPage) => openPage.url()));
say(`CONTEXTS=${contexts.length} PAGES=${urls.length} URLS=${JSON.stringify(urls).slice(0, 400)}`);
const context = contexts[0] ?? await browser.newContext();
const existing = context.pages().find((candidate) => (candidate.url() || "").includes("/revolution"));
say(`USING=${existing ? "existing-revolution-tab" : "new-page"}`);
const page = existing ?? await context.newPage();
await page.setViewportSize({ width: 430, height: 932 });

const shot = async (name) => {
  const file = path.join(SHOTS, `${PREFIX}-${name}.png`);
  await page.screenshot({ path: file }).catch(() => undefined);
  say(`SHOT ${name}.png bytes=${fs.existsSync(file) ? fs.statSync(file).size : 0}`);
};
const read = async (locator, max = 600) => flat((await locator.first().innerText().catch(() => ""))).slice(0, max);

say(`READ_START ${new Date().toISOString()} ${WEB}`);
await page.goto(WEB, { waitUntil: "networkidle" });
await page.waitForTimeout(4000);
say(`LANDING ${await read(page.locator("main, .cn-shell, body"), 420)}`);

const tripTab = page.getByRole("button", { name: /我的旅程/ });
say(`TRIP_TAB_VISIBLE=${await tripTab.first().isVisible().catch(() => false)}`);
if (await tripTab.first().isVisible().catch(() => false)) {
  await tripTab.first().click({ timeout: 8000 }).catch((error) => say(`TAB_ERR ${flat(error.message).slice(0, 60)}`));
  await page.waitForTimeout(3000);
}
const openTrip = page.getByRole("button", { name: /打开|继续|查看行程/ }).first();
say(`OPEN_TRIP_BUTTON=${await openTrip.isVisible().catch(() => false)}`);
if (await openTrip.isVisible().catch(() => false)) {
  await openTrip.click({ timeout: 8000 }).catch(() => undefined);
  await page.waitForTimeout(3500);
}
const live = page.getByTestId("live-recovery");
say(`LIVE_CARD_VISIBLE=${await live.first().isVisible().catch(() => false)}`);
say(`LIVE_KICKER ${await read(live.locator(".v8-kicker"), 120)}`);
say(`LIVE_TITLE ${await read(live.locator("h1"), 120)}`);
say(`LIVE_NEXT ${await read(live.getByTestId("live-next"), 220)}`);
await shot("01-live-card");
say(`LIVE_WHOLE ${await read(live, 900)}`);
await page.close().catch(() => undefined);
process.exit(0);
