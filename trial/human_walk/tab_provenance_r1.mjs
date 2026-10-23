/**
 * Which tab is which -- and what does each one actually show?
 *
 * Four walks share one automation profile and each leaves its tab behind, so a reading taken from "the last
 * page" cannot say whose screen it is.  This walks every open tab, prints the journey pointer that tab's own
 * localStorage holds, and the first line of what the traveller sees, so a claim about a screen can carry the
 * tab it came from.
 */
import fs from "node:fs";
import path from "node:path";
import { createRequire } from "node:module";

const require = createRequire("D:/moodle/_cmdr_rescue_v3_1022/frontend/package.json");
const { chromium } = require("playwright");

const OUT = "D:/moodle/_cmdr_rescue_v3_1022/trial/results/20261022_v3_human_chrome";
const stream = fs.openSync(path.join(OUT, process.env.PROBE_LOG || "tab-provenance-1.txt"), "a");
const flat = (v) => String(v ?? "").replace(/\s+/g, " ").trim();
const say = (t) => { fs.writeSync(stream, t + "\n"); process.stdout.write(t + "\n"); };

const browser = await chromium.connectOverCDP("http://127.0.0.1:9335", { timeout: 120000 });
const context = browser.contexts()[0] ?? await browser.newContext();
const pages = context.pages();
say(`TABS_AT ${new Date().toISOString()} count=${pages.length}`);
for (let index = 0; index < pages.length; index += 1) {
  const tab = pages[index];
  const pointer = await tab.evaluate(() => {
    try {
      const raw = window.localStorage.getItem("citynexus.revolution.firstlook.journey");
      if (!raw) return "(no pointer)";
      const parsed = JSON.parse(raw);
      return String(parsed.id ?? "(no id)") + " status=" + String(parsed.status ?? "?");
    } catch (error) { return "(unreadable)"; }
  }).catch(() => "(evaluate failed)");
  const bearer = await tab.evaluate(() => {
    try { return window.sessionStorage.getItem("citynexus.traveler.bearer") ? "present" : "absent"; }
    catch (error) { return "(unreadable)"; }
  }).catch(() => "(evaluate failed)");
  const body = flat(await tab.locator("body").innerText({ timeout: 5000 }).catch(() => "(unreadable)"));
  say(`TAB_${index} url=${tab.url()} pointer=${pointer} bearer_in_this_tab=${bearer}`);
  say(`TAB_${index} SCREEN ${body.slice(0, 220)}`);
  say(`TAB_${index} HAS_WIZARD=${/从一句话开始/.test(body)} HAS_MISSION=${/地图\s*日程\s*对话|你的旅行搭档/.test(body)} `
    + `HAS_NO_RESTORE=${/旧行程无法恢复/.test(body)} DRAFT_SLOTS=${await tab.locator(".rev-goal-draft-slot").count().catch(() => -1)}`);
}
await browser.close().catch(() => undefined);
