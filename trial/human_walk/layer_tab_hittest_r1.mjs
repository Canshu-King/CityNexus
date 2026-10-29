/**
 * Who is sitting on top of the layer switcher?
 *
 * walk-103 hit it for real: `LAYER_BLOCKED rev-mission-layer-timeline attempt=1 {... "hit_test":
 * "div.rev-firstlook-brand", "covers_it": true ...}` (trial/results/20261022_v3_human_chrome/walk-103-log.txt:54),
 * so the traveller's first press on 日程 did nothing and the instrument had to press again.  This measures the
 * same thing deliberately: for each layer tab, in three viewport shapes, take the tab's own box and ask the page
 * which element is actually at its centre.  Read-only -- it clicks nothing, so it cannot move the app's state.
 */
import fs from "node:fs";
import path from "node:path";
import { createRequire } from "node:module";

const require = createRequire("D:/moodle/_cmdr_rescue_v3_1022/frontend/package.json");
const { chromium } = require("playwright");

const OUT = "D:/moodle/_cmdr_rescue_v3_1022/trial/results/20261022_v3_human_chrome";
const stream = fs.openSync(path.join(OUT, process.env.HIT_LOG || "layer-tab-hittest-1.txt"), "a");
const JOURNEY = process.env.HIT_JOURNEY || "80fa5b58";
const flat = (v) => String(v ?? "").replace(/\s+/g, " ").trim();
const say = (t) => { fs.writeSync(stream, t + "\n"); process.stdout.write(t + "\n"); };

const browser = await chromium.connectOverCDP("http://127.0.0.1:9335", { timeout: 120000 });
const context = browser.contexts()[0] ?? await browser.newContext();
let page = null;
for (const candidate of context.pages()) {
  const pointer = await candidate.evaluate(() => {
    try { return window.localStorage.getItem("citynexus.revolution.firstlook.journey") || "(none)"; }
    catch { return "(unreadable)"; }
  }).catch(() => "(eval failed)");
  if (String(pointer).includes(JOURNEY)) { page = candidate; say(`USING_TAB pointer=${flat(pointer).slice(0, 80)}`); }
}
if (!page) { say(`NO_TAB_FOR_JOURNEY ${JOURNEY} -- refusing to measure someone else's screen`); process.exit(0); }

const tabs = ["rev-mission-layer-map", "rev-mission-layer-timeline", "rev-mission-layer-agent"];
for (const shape of [[360, 780], [390, 844], [430, 932]]) {
  await page.setViewportSize({ width: shape[0], height: shape[1] }).catch((e) => say(`RESIZE_ERR ${flat(e.message).slice(0, 60)}`));
  await page.waitForTimeout(1200);
  for (const testId of tabs) {
    const info = await page.evaluate((id) => {
      const node = document.querySelector(`[data-testid="${id}"]`);
      if (!node) return { present: false };
      const box = node.getBoundingClientRect();
      const cx = Math.round(box.left + box.width / 2);
      const cy = Math.round(box.top + box.height / 2);
      const top = document.elementFromPoint(cx, cy);
      const chain = [];
      let walker = top;
      for (let hop = 0; walker && hop < 3; hop += 1) {
        chain.push(walker.tagName.toLowerCase() + (walker.className ? "." + String(walker.className).trim().split(/\s+/).slice(0, 2).join(".") : ""));
        walker = walker.parentElement;
      }
      return {
        present: true,
        box: { x: Math.round(box.x), y: Math.round(box.y), w: Math.round(box.width), h: Math.round(box.height) },
        point: [cx, cy],
        is_self_or_child: Boolean(top && node.contains(top)),
        topmost: chain.join(" <- ") || "(nothing at that point)",
      };
    }, testId).catch((e) => ({ error: flat(e.message).slice(0, 70) }));
    say(`SHAPE ${shape[0]}x${shape[1]} ${testId} ${JSON.stringify(info)}`);
  }
}
await page.setViewportSize({ width: 390, height: 844 }).catch(() => undefined);
await browser.close().catch(() => undefined);
