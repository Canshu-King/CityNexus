/**
 * walk-116: send the capped sentence, wait for the freeze to land, then press 「根据路线重新安排」 and read whether the
 * new revision still honours the cap. Every click is a real click on a rendered control; every reading is rendered text.
 */
import fs from "node:fs";
import path from "node:path";
import { createRequire } from "node:module";

const require = createRequire("D:/moodle/_cmdr_rescue_v3_1022/frontend/package.json");
const { chromium } = require("playwright");

const SHOTS = "D:/moodle/_cmdr_rescue_v3_1022/trial/results/20261022_v3_human_chrome";
const STORY = "北京玩两天，两个人。每段步行不超过1公里，远的请改坐地铁并写明线路和站名。节奏：轻松少走";
const STREAM = fs.openSync(path.join(SHOTS, "walk-116-log.txt"), "a");
const say = (t) => { fs.writeSync(STREAM, t + "\n"); };

const browser = await chromium.connectOverCDP("http://127.0.0.1:9335");
const context = browser.contexts()[0];
const candidates = context.pages().filter((p) => p.url().includes("14522"));

let page = null;
for (const candidate of candidates) {
  const has = await candidate.evaluate(() => [...document.querySelectorAll("button")]
    .some((b) => /根据路线重新安排/.test(b.innerText || ""))).catch(() => false);
  if (has && !page) page = candidate;
}
if (!page) { say("NO_TAB_WITH_REPLAN"); process.exit(0); }
page.setDefaultTimeout(20000);
say(`RUN_START ${new Date().toISOString()}`);

const readState = async (tag) => {
  const s = await page.evaluate(() => {
    const flatIn = (v) => String(v ?? "").replace(/\s+/g, " ").trim();
    const dock = document.querySelector("[data-testid='rev-mission-chat-dock']");
    const ta = dock ? dock.querySelector("textarea") : null;
    return {
      dock_present: Boolean(dock),
      dock_value: ta ? flatIn(ta.value).slice(0, 80) : null,
      send_buttons: dock ? [...dock.querySelectorAll("button")].map((b) => flatIn(b.innerText)).slice(0, 6) : [],
      frozen_rows: document.querySelectorAll("[data-testid='rev-amap-research-frozen']").length,
      band: (() => { const el = [...document.querySelectorAll("p,div")].find((n) => /转场已核实/.test(n.innerText || "")); return el ? flatIn(el.innerText).slice(0, 180) : "(absent)"; })(),
      cap_sentence_on_screen: /超过你写的/.test(document.body.innerText || ""),
      replan_visible: [...document.querySelectorAll("button")].filter((b) => /根据路线重新安排/.test(b.innerText || "")).length,
      body_head: flatIn(document.body.innerText).slice(0, 120),
    };
  });
  say(`${tag} ${JSON.stringify(s)}`);
  return s;
};

// 1) snapshot, then send the sentence through the dock's own send button
const start = await readState("STEP_01_STATE");
if (!start.dock_present) { say("PROBE_FAILED no_dock"); process.exit(0); }
await page.locator("[data-testid='rev-mission-chat-dock'] textarea").fill(STORY);
await page.waitForTimeout(700);
say(`STEP_02_TYPED ${JSON.stringify(await page.evaluate(() => {
  const flatIn = (v) => String(v ?? "").replace(/\s+/g, " ").trim();
  const ta = document.querySelector("[data-testid='rev-mission-chat-dock'] textarea");
  return ta ? flatIn(ta.value).slice(0, 90) : null;
}))}`);
const sent = await page.evaluate(() => {
  const flatIn = (v) => String(v ?? "").replace(/\s+/g, " ").trim();
  const dock = document.querySelector("[data-testid='rev-mission-chat-dock']");
  const b = [...dock.querySelectorAll("button")].find((x) => /发送/.test(x.innerText || "") && !x.disabled);
  if (!b) return { found: false };
  const box = b.getBoundingClientRect();
  const hit = document.elementFromPoint(box.left + box.width / 2, box.top + box.height / 2);
  b.click();
  return { found: true, centre_hit_is_button: hit === b || b.contains(hit), label: flatIn(b.innerText) };
});
say(`STEP_03_SENT ${JSON.stringify(sent)} at ${new Date().toISOString()}`);

// 2) wait for the research + freeze to land (poll, log every tick)
let landed = false;
for (let tick = 1; tick <= 36; tick += 1) {
  await page.waitForTimeout(10000);
  const now = await readState(`POLL_${tick}_${(tick * 10)}s`);
  if (now.frozen_rows > 0 || now.cap_sentence_on_screen) { landed = true; break; }
}
say(`STEP_04_LANDED ${landed} at ${new Date().toISOString()}`);
if (!landed) { say("PROBE_STOP no_frozen_rows_within_6min"); process.exit(0); }

// 3) the one real action
const gate = await page.evaluate(() => {
  const flatIn = (v) => String(v ?? "").replace(/\s+/g, " ").trim();
  const b = [...document.querySelectorAll("button")].find((n) => /根据路线重新安排/.test(n.innerText || ""));
  if (!b) return { found: false };
  b.scrollIntoView({ block: "center" });
  const box = b.getBoundingClientRect();
  const hit = document.elementFromPoint(box.left + box.width / 2, box.top + box.height / 2);
  return { found: true, disabled: b.disabled, centre_hit_is_button: hit === b || b.contains(hit) };
});
say(`STEP_05_GATE ${JSON.stringify(gate)}`);
if (!gate.found) { say("PROBE_STOP no_replan_button"); process.exit(0); }
await page.getByRole("button", { name: /根据路线重新安排/ }).first().click();
say(`STEP_06_PRESSED ${new Date().toISOString()}`);
await page.waitForTimeout(9000);
const diff = await page.evaluate(() => {
  const flatIn = (v) => String(v ?? "").replace(/\s+/g, " ").trim();
  const el = document.querySelector("[data-testid='rev-v3-replan-diff']");
  if (el) return { testid: true, text: flatIn(el.innerText).slice(0, 900) };
  const any = [...document.querySelectorAll("div,section")].find((n) => /改动|差异|换成|保留/.test(n.innerText || "") && (n.innerText || "").length > 60);
  return { testid: false, text: any ? flatIn(any.innerText).slice(0, 900) : "(no diff block)" };
});
say(`STEP_07_DIFF ${JSON.stringify(diff)}`);

// 4) apply, then read the new revision
const applied = await page.evaluate(() => {
  const flatIn = (v) => String(v ?? "").replace(/\s+/g, " ").trim();
  const b = [...document.querySelectorAll("button")].find((n) => /应用|按这版|确认这版|就这么排/.test(n.innerText || "") && !n.disabled);
  if (!b) return { found: false, labels: [...document.querySelectorAll("button")].map((x) => flatIn(x.innerText)).slice(0, 30) };
  const label = flatIn(b.innerText);
  b.click();
  return { found: true, label };
});
say(`STEP_08_APPLY ${JSON.stringify(applied)}`);
await page.waitForTimeout(12000);
const after = await readState("STEP_09_AFTER");
say(`STEP_09_CHECK cap_kept=${after.frozen_rows > 0 && after.cap_sentence_on_screen}`);

try {
  const cdp = await context.newCDPSession(page);
  const cap = await cdp.send("Page.captureScreenshot", { format: "png" });
  const name = "walk116-after-replan.png";
  fs.writeFileSync(path.join(SHOTS, name), Buffer.from(cap.data, "base64"));
  say(`SHOT ${name} bytes=${fs.statSync(path.join(SHOTS, name)).size}`);
} catch (error) { say("SHOT_ERR " + String(error.message).slice(0, 70)); }
say(`RUN_END ${new Date().toISOString()}`);
process.exit(0);
