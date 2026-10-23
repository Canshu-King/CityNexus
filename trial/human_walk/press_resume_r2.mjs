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
const stream = fs.openSync(path.join(OUT, process.env.PRESS_LOG || "press-resume-2.txt"), "a");
const flat = (v) => String(v ?? "").replace(/\s+/g, " ").trim();
const say = (t) => { fs.writeSync(stream, t + "\n"); process.stdout.write(t + "\n"); };
const read = async (locator, limit) => flat(await locator.innerText({ timeout: 6000 }).catch(() => "(unreadable)")).slice(0, limit);

const browser = await chromium.connectOverCDP("http://127.0.0.1:9335", { timeout: 120000 });
const context = browser.contexts()[0] ?? await browser.newContext();
const tabs = context.pages();
say(`TABS ${tabs.length} at ${new Date().toISOString()}`);

// r2 fixes a selection flaw r1 shared with the hit-test: localStorage is per-ORIGIN, so every tab on the same
// host reports the same journey id -- `_tab_probe_r4.mjs` measured two tabs both returning 6498b977, one holding
// the live cockpit and one holding the welcome form.  A press must not be aimed by that.  So a tab qualifies only
// when it has the chat dock AND a visible 继续研究 button, and if more than one qualifies this instrument refuses
// to click anything: pressing in the wrong tab would corrupt a walk I am not running.
let page = null;
const qualified = [];
for (const candidate of tabs) {
  const mark = await candidate.evaluate(() => {
    const dock = Boolean(document.querySelector(".rev-mission-chat-dock"));
    const resume = [...document.querySelectorAll("button")].some((b) => /继续研究/.test(b.textContent || ""));
    let pointer = "(unreadable)";
    try { pointer = String(window.localStorage.getItem("citynexus.revolution.firstlook.journey") || "(none)"); } catch { /* private mode */ }
    return { dock, resume, pointer: pointer.slice(0, 60) };
  }).catch(() => null);
  const marked = Boolean(mark) && mark.pointer.includes(JOURNEY);
  const ok = Boolean(mark) && marked && mark.dock && mark.resume;
  say(`TAB url=${candidate.url()} pointer=${mark ? mark.pointer : "(no mark)"} dock=${mark ? mark.dock : "?"} resume_button=${mark ? mark.resume : "?"} journey_match=${marked} QUALIFIES=${ok}`);
  if (ok) qualified.push(candidate);
}
if (qualified.length !== 1) {
  say(`REFUSE_TO_PRESS qualifying_tabs=${qualified.length} -- 要么没人处于可重试态，要么有两个页面都说自己是这一趟，按错就污染别人的走查`);
  process.exit(0);
}
page = qualified[0];
if (process.env.PRESS_DRY === "1") {
  say("DRY_RUN: 选页与按钮都找到了，这一趟不点击（走查还在用这一页时不许按）");
  await browser.close().catch(() => undefined);
  process.exit(0);
}

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
