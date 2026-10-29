/**
 * What does the traveller see six minutes after pressing 开始研究 and nothing arriving?
 *
 * walk-99 pressed the button (STEP_04B pressed=true), the dock never reported busy, and the instrument's wait
 * loop only writes `WAIT_*s busy=false` -- it never reads the screen while it waits.  That is a ruler that
 * swallows the very thing being asked, so this attaches to the same tab and writes down what is on it.
 */
import fs from "node:fs";
import path from "node:path";
import { createRequire } from "node:module";

const require = createRequire("D:/moodle/_cmdr_rescue_v3_1022/frontend/package.json");
const { chromium } = require("playwright");

const OUT = "D:/moodle/_cmdr_rescue_v3_1022/trial/results/20261022_v3_human_chrome";
const stream = fs.openSync(path.join(OUT, process.env.PROBE_LOG || "stalled-research-screen-1.txt"), "a");
const flat = (v) => String(v ?? "").replace(/\s+/g, " ").trim();
const say = (t) => { fs.writeSync(stream, t + "\n"); process.stdout.write(t + "\n"); };

const browser = await chromium.connectOverCDP("http://127.0.0.1:9335", { timeout: 120000 });
const context = browser.contexts()[0] ?? await browser.newContext();
const matching = context.pages().filter((candidate) => (candidate.url() || "").includes(process.env.PROBE_URL_PART || "/revolution"));
const page = matching[matching.length - 1];
if (!page) { say("NO_REVOLUTION_TAB"); process.exit(0); }
say(`TABS ${JSON.stringify(context.pages().map((candidate) => candidate.url())).slice(0, 400)}`);
await page.bringToFront().catch((e) => say(`FRONT_ERR ${flat(e.message).slice(0, 60)}`));
await page.waitForTimeout(1500);
say(`READ_AT ${new Date().toISOString()} url=${page.url()}`);
const body = flat(await page.locator("body").innerText({ timeout: 8000 }).catch(() => "(unreadable)"));
say(`SCREEN ${body.slice(0, 900)}`);
say(`DRAFT_SLOTS=${await page.locator(".rev-goal-draft-slot").count().catch(() => -1)} `
  + `VARIANT_CARDS=${await page.locator(".rev-goal-variant-card").count().catch(() => -1)} `
  + `DEPARTURE_VISIBLE=${await page.locator(".rev-v3-departure").first().isVisible().catch(() => false)}`);
const dock = page.locator(".rev-mission-chat-dock");
say(`DOCK ${flat(await dock.innerText({ timeout: 5000 }).catch(() => "(unreadable)")).slice(0, 400)}`);
const shot = path.join(OUT, process.env.PROBE_SHOT || "stalled-screen-r2.png");
await page.screenshot({ path: shot, fullPage: false }).catch((e) => say(`SHOT_ERR ${flat(e.message).slice(0, 60)}`));
if (fs.existsSync(shot)) say(`SHOT ${path.basename(shot)} bytes=${fs.statSync(shot).size}`);
await browser.close().catch(() => undefined);
