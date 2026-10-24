/** Press 同行决策 and read what the collective door shows a single traveller. */
import fs from "node:fs";
import path from "node:path";
import { createRequire } from "node:module";
const require = createRequire("D:/moodle/_cmdr_rescue_v3_1022/frontend/package.json");
const { chromium } = require("playwright");
const SHOTS = "D:/moodle/_cmdr_rescue_v3_1022/trial/results/20261022_v3_human_chrome";
const flat = (v) => String(v ?? "").replace(/\s+/g, " ").trim();
const stream = fs.openSync(path.join(SHOTS, "walk-43-log.txt"), "a");
const say = (t) => { fs.writeSync(stream, t + "\n"); process.stdout.write(t + "\n"); };
const browser = await chromium.connectOverCDP("http://127.0.0.1:9335");
const context = browser.contexts()[0];
let page = null;
for (const candidate of context.pages()) {
  const ok = await candidate.evaluate(() => location.href.includes("14381")
    && Boolean(window.sessionStorage.getItem("citynexus.traveler.bearer"))).catch(() => false);
  if (ok) { page = candidate; break; }
}
if (!page) { say("NO_LIVE_TAB"); process.exit(0); }
page.setDefaultTimeout(8000);
const cdp = await context.newCDPSession(page);
const shot = async (name) => {
  for (let attempt = 1; attempt <= 3; attempt += 1) {
    try {
      const deadline = new Promise((_, reject) => setTimeout(() => reject(new Error("no frame")), 15000));
      const capture = await Promise.race([cdp.send("Page.captureScreenshot", { format: "png" }), deadline]);
      fs.writeFileSync(path.join(SHOTS, name), Buffer.from(capture.data, "base64"));
      say(`SHOT ${name} bytes=${fs.statSync(path.join(SHOTS, name)).size}`); return;
    } catch (error) { say(`SHOT_RETRY ${flat(error.message).slice(0, 24)}`); await new Promise((r) => setTimeout(r, 3000)); }
  }
};
say(`WALK43B_START ${new Date().toISOString()} the 同行决策 door, pressed by hand`);
const before = await page.evaluate(() => {
  const button = [...document.querySelectorAll("button")].find((n) => (n.innerText || "").includes("同行决策"));
  if (!button) return null;
  button.scrollIntoView({ block: "center" });
  const box = button.getBoundingClientRect();
  const hit = document.elementFromPoint(box.left + box.width / 2, box.top + box.height / 2);
  return { box: { x: Math.round(box.x), y: Math.round(box.y), w: Math.round(box.width), h: Math.round(box.height) },
    hit_is_button: hit ? (hit === button || button.contains(hit)) : false,
    hit_topmost: hit ? hit.tagName + "." + String(hit.className).slice(0, 30) : "OUT_OF_VIEWPORT" };
});
say("ENTRY " + JSON.stringify(before));
if (!before) process.exit(0);
await shot("human-221-collective-entry-on-screen.png");
await page.getByText("同行决策", { exact: false }).first().click({ timeout: 6000 }).catch((e) => say("CLICK_ERR " + flat(e.message).slice(0, 60)));
await page.waitForTimeout(3500);
const panel = await page.evaluate(() => {
  const dialog = document.querySelector("[role='dialog'], .rev-modal, [data-testid*='consent'], [data-testid*='collective'], [data-testid*='member']");
  const scope = dialog || document.body;
  return { dialog_found: Boolean(dialog), testids: [...document.querySelectorAll("[data-testid]")].map((n) => n.getAttribute("data-testid"))
      .filter((id) => /consent|collective|member|decision|share/i.test(id)).slice(0, 8),
    text: scope.innerText.replace(/\s+/g, " ").trim().slice(0, 460) };
});
say("COLLECTIVE_PANEL " + JSON.stringify(panel));
await shot("human-222-collective-panel-open.png");
say(`WALK43B_END ${new Date().toISOString()}`);
process.exit(0);
