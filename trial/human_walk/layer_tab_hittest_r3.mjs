/**
 * Layer-tab hit-test, r3 -- fixes a flaw r2 proved in the field.
 *
 * r2 picked the tab whose localStorage pointer matched the journey, and reported `present:false` for all three
 * layer tabs while walk-105 was drafting.  A per-tab dump (`_tab_probe_r4.mjs`) shows why: localStorage is
 * per-ORIGIN, so every tab on 14496 returns the same journey id -- the pointer identifies the journey, never the
 * tab.  The live walkthrough tab was the one holding the cockpit (3 layer tabs, a dock, 7 draft slots, 414x900);
 * r2 measured the other one.  r3 therefore requires the widget under test to exist in that tab and prints the
 * discriminator for every tab it looked at, so a wrong target cannot pass silently.
 */
import fs from "node:fs";
import path from "node:path";
import { createRequire } from "node:module";

const require = createRequire("D:/moodle/_cmdr_rescue_v3_1022/frontend/package.json");
const { chromium } = require("playwright");

const OUT = "D:/moodle/_cmdr_rescue_v3_1022/trial/results/20261022_v3_human_chrome";
const stream = fs.openSync(path.join(OUT, process.env.HIT_LOG || "layer-tab-hittest-3.txt"), "a");
const flat = (v) => String(v ?? "").replace(/\s+/g, " ").trim();
const say = (t) => { fs.writeSync(stream, t + "\n"); process.stdout.write(t + "\n"); };

const browser = await chromium.connectOverCDP("http://127.0.0.1:9335", { timeout: 120000 });
const context = browser.contexts()[0] ?? await browser.newContext();
const tabs = ["rev-mission-layer-map", "rev-mission-layer-timeline", "rev-mission-layer-agent"];

const qualified = [];
for (const [index, candidate] of context.pages().entries()) {
  const mark = await candidate.evaluate(() => ({
    cockpit: document.querySelectorAll('[data-testid^="rev-mission-layer-"]').length,
    dock: Boolean(document.querySelector(".rev-mission-chat-dock")),
    slots: document.querySelectorAll(".rev-goal-draft-slot").length,
    scrollY: Math.round(window.scrollY),
    shape: `${window.innerWidth}x${window.innerHeight}`,
    pointer: (() => { try { return String(localStorage.getItem("citynexus.revolution.firstlook.journey") || "(none)").slice(0, 12); } catch { return "(err)"; } })(),
  })).catch(() => null);
  say(`CANDIDATE_${index} url=${candidate.url()} mark=${JSON.stringify(mark)}`);
  if (mark && mark.cockpit === 3) qualified.push(candidate);
}
if (qualified.length !== 1) {
  say(`REFUSE qualifying_tabs=${qualified.length} -- localStorage 是按源的，两页同指针已经实测到（_tab_probe_r4），不能靠它猜哪一页`);
  await browser.close().catch(() => undefined);
  process.exit(0);
}
const page = qualified[0];

for (const mode of ["as_is", "after_scroll_into_view"]) {
  for (const testId of tabs) {
    if (mode === "after_scroll_into_view") {
      await page.locator(`[data-testid="${testId}"]`).first().scrollIntoViewIfNeeded({ timeout: 4000 }).catch(() => undefined);
      await page.waitForTimeout(400);
    }
    const info = await page.evaluate((id) => {
      const node = document.querySelector(`[data-testid="${id}"]`);
      if (!node) return { present: false };
      const box = node.getBoundingClientRect();
      const cx = Math.round(box.left + box.width / 2);
      const cy = Math.round(box.top + box.height / 2);
      const top = document.elementFromPoint(cx, cy);
      const chain = [];
      for (let walker = top, hop = 0; walker && hop < 3; hop += 1) {
        chain.push(walker.tagName.toLowerCase() + (walker.className ? "." + String(walker.className).trim().split(/\s+/).slice(0, 2).join(".") : ""));
        walker = walker.parentElement;
      }
      return { present: true, box: { x: Math.round(box.x), y: Math.round(box.y), w: Math.round(box.width), h: Math.round(box.height) },
        point: [cx, cy], covers_it: Boolean(top && !node.contains(top)),
        topmost: chain.join(" <- ") || "(nothing at that point)", scrollY: Math.round(window.scrollY) };
    }, testId).catch((e) => ({ error: flat(e.message).slice(0, 70) }));
    say(`MODE ${mode} ${testId} ${JSON.stringify(info)}`);
  }
}
say("NOTE 全程只读：不改视口、不点击、不动 storage；唯一动作是 scrollIntoView（会移页面滚动条，走查自己也会滚）");
await browser.close().catch(() => undefined);
