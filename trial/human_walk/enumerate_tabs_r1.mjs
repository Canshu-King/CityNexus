/** Which of the open 14522 tabs actually holds a journey with a frozen, capped plan? Read-only. */
import fs from "node:fs";
import path from "node:path";
import { createRequire } from "node:module";

const require = createRequire("D:/moodle/_cmdr_rescue_v3_1022/frontend/package.json");
const { chromium } = require("playwright");

const SHOTS = "D:/moodle/_cmdr_rescue_v3_1022/trial/results/20261022_v3_human_chrome";
const stream = fs.openSync(path.join(SHOTS, "walk-116-log.txt"), "a");
const say = (t) => { fs.writeSync(stream, t + "\n"); };

const browser = await chromium.connectOverCDP("http://127.0.0.1:9335");
const context = browser.contexts()[0];
const pages = context.pages().filter((p) => p.url().includes("14522"));
say(`ENUM_START tabs=${pages.length} at ${new Date().toISOString()}`);
for (let i = 0; i < pages.length; i += 1) {
  const page = pages[i];
  let info = null;
  try {
    info = await page.evaluate(() => {
      const flatIn = (v) => String(v ?? "").replace(/\s+/g, " ").trim();
      const ptr = JSON.parse(localStorage.getItem("citynexus.revolution.firstlook.journey") || "null");
      const visible = (n) => n && n.getBoundingClientRect().width > 0;
      return {
        pointer: ptr ? flatIn(ptr.id).slice(0, 8) : null,
        owner: ptr ? flatIn(ptr.ownerTravelerId).slice(0, 8) : null,
        cockpit: Boolean(document.querySelector("[data-testid='rev-mission-cockpit']")),
        frozen_rows: document.querySelectorAll("[data-testid='rev-amap-research-frozen']").length,
        replan_buttons: [...document.querySelectorAll("button")].map((b) => flatIn(b.innerText)).filter((t) => /重新安排/.test(t)),
        body_has_cap_sentence: /超过你写的/.test(document.body.innerText || ""),
        text_head: flatIn(document.body.innerText).slice(0, 90),
      };
    });
  } catch (error) { info = { error: flatErr(error.message) }; }
  say(`TAB_${i} ${JSON.stringify(info)}`);
}
function flatErr(v) { return String(v ?? "").replace(/\s+/g, " ").slice(0, 80); }
say(`ENUM_END ${new Date().toISOString()}`);
process.exit(0);
