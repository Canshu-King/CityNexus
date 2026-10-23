/**
 * Press 继续研究 and read what comes back -- the one half of the 503 story nobody has measured.
 *
 * walk-103's own log proves the screen tells the traveller the truth while the Agent's run sits at
 * FAILED_EXTERNAL / MODEL_HTTP_503 (walk-103-log.txt:15 onward, 16 dock readings), and the read-only affordance
 * probe found the retry button visible and enabled (resume-affordance-1.txt:4).  What is NOT measured is whether
 * a person pressing it recovers anything.  This does that one action: it selects the tab by the journey pointer
 * that tab's own localStorage holds -- so it cannot land on another walk's screen -- clicks the button a traveller
 * clicks, and writes down the screen's words as they change.  No API call, no seeded state, no DOM injection.
 */
import fs from "node:fs";
import path from "node:path";
import { createRequire } from "node:module";

const require = createRequire("D:/moodle/_cmdr_rescue_v3_1022/frontend/package.json");
const { chromium } = require("playwright");

const OUT = "D:/moodle/_cmdr_rescue_v3_1022/trial/results/20261022_v3_human_chrome";
const JOURNEY = process.env.PRESS_JOURNEY || "80fa5b58";
const stream = fs.openSync(path.join(OUT, process.env.PRESS_LOG || "press-resume-1.txt"), "a");
const flat = (v) => String(v ?? "").replace(/\s+/g, " ").trim();
const say = (t) => { fs.writeSync(stream, t + "\n"); process.stdout.write(t + "\n"); };
const read = async (locator, limit) => flat(await locator.innerText({ timeout: 6000 }).catch(() => "(unreadable)")).slice(0, limit);

const browser = await chromium.connectOverCDP("http://127.0.0.1:9335", { timeout: 120000 });
const context = browser.contexts()[0] ?? await browser.newContext();
const tabs = context.pages();
say(`TABS ${tabs.length} at ${new Date().toISOString()}`);

let page = null;
for (const candidate of tabs) {
  const pointer = await candidate.evaluate(() => {
    try { return window.localStorage.getItem("citynexus.revolution.firstlook.journey") || "(none)"; }
    catch { return "(unreadable)"; }
  }).catch(() => "(eval failed)");
  const marked = String(pointer).includes(JOURNEY);
  say(`TAB url=${candidate.url()} pointer=${flat(pointer).slice(0, 90)} match=${marked}`);
  if (marked && !page) page = candidate;
}
if (!page) { say(`NO_TAB_FOR_JOURNEY ${JOURNEY} -- refusing to press in someone else's screen`); process.exit(0); }

await page.bringToFront().catch(() => undefined);
const dock = page.locator('[data-testid="rev-dock-status"]').first();
const resume = page.getByRole("button", { name: /继续研究/ }).first();
const slots = () => page.locator(".rev-goal-draft-slot").count().catch(() => -1);
const busyNow = async () => /正在推进|正在研究|回复中/.test(flat(await page.locator("body").innerText({ timeout: 6000 }).catch(() => "")));

say(`BEFORE dock=${await read(dock, 200)}`);
say(`BEFORE resume visible=${await resume.isVisible().catch(() => false)} disabled=${await resume.isDisabled().catch(() => "(unreadable)")}`);
say(`BEFORE draft_slots=${await slots()} busy_pattern=${await busyNow()}`);
const shotBefore = path.join(OUT, "press-resume-before.png");
await page.screenshot({ path: shotBefore }).catch((e) => say(`SHOT_BEFORE_ERR ${flat(e.message).slice(0, 60)}`));

await resume.click({ timeout: 8000 }).catch((e) => say(`PRESS_ERR ${flat(e.message).slice(0, 90)}`));
say(`PRESSED_AT ${new Date().toISOString()}`);

for (let poll = 1; poll <= 32; poll += 1) {
  await page.waitForTimeout(15000);
  const count = await slots();
  const line = await read(dock, 190);
  say(`AFTER_${poll * 15}s dock=${line} slots=${count} busy=${await busyNow()}`);
  if (count > 0) { say(`RECOVERED slots=${count} at ${poll * 15}s`); break; }
  if (poll === 32) say("AFTER_TIMEOUT 8 minutes, no draft slots came back");
}
const shotAfter = path.join(OUT, "press-resume-after.png");
await page.screenshot({ path: shotAfter }).catch((e) => say(`SHOT_AFTER_ERR ${flat(e.message).slice(0, 60)}`));
say(`CARD ${await read(page.locator('[data-testid="rev-plan-workbench"]').first(), 300)}`);
say(`SHOT before=${fs.existsSync(shotBefore) ? fs.statSync(shotBefore).size : "missing"} after=${fs.existsSync(shotAfter) ? fs.statSync(shotAfter).size : "missing"}`);
await browser.close().catch(() => undefined);
