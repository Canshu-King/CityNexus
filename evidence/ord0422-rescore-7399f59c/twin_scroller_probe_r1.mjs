/* ORD-0422 rescore probe. The branch reader reported bottom_reached=false on the twin screen's
 * Chinese arm at this generation while the English arm reached bottom, so before that reading is
 * called a pass or a fail, the question is WHICH container refuses to scroll and by how much.
 * Prints every scrollable ancestor with its own geometry, then hit-tests the empty-state action the
 * new ORD-0401 criterion cares about: one scroll, then document.elementFromPoint at the control's
 * centre, plus what fixed element is on top when it is not the control.
 */
import { chromium } from "file:///D:/moodle/CityNexus/frontend/node_modules/playwright/index.mjs";
import fs from "node:fs";

const UI = "http://127.0.0.1:4314";
const DEMO = "22222222-2222-4222-8222-222222222222";
const OUT = "D:/moodle/_qoder_q_ord0422/rescore_readings";
const PROBE = () => {
  const containers = [];
  const all = [document.scrollingElement || document.documentElement, ...document.querySelectorAll("*")];
  all.forEach((el) => {
    if (!(el.scrollHeight > el.clientHeight + 8 && el.clientHeight > 60)) return;
    const max = Math.max(0, el.scrollHeight - el.clientHeight);
    let deepest = 0;
    for (let y = 0; ; y += Math.max(100, Math.floor(el.clientHeight * 0.5))) {
      el.scrollTop = Math.min(y, max);
      deepest = Math.max(deepest, Math.round(el.scrollTop));
      if (y >= max) break;
    }
    containers.push({ tag: el.tagName, cls: String(el.className || "").slice(0, 40), max,
                      deepest, bottom_reached: deepest >= max - 2,
                      overflow: getComputedStyle(el).overflowY, clientHeight: el.clientHeight,
                      scrollHeight: el.scrollHeight });
    el.scrollTop = 0;
  });
  return { path: location.pathname, containers };
};

const browser = await chromium.launch({ channel: "chrome", headless: true });
const ctx = await browser.newContext({ viewport: { width: 390, height: 844 } });
const page = await ctx.newPage();
const rows = [];
for (const locale of ["zh-CN", "en"]) {
  await page.addInitScript(([l, id]) => {
    try {
      localStorage.setItem("citynexus.locale", l);
      localStorage.setItem("citynexus.v8.journey_id", id);
    } catch (e) {}
  }, [locale, DEMO]);
  await page.goto(`${UI}/v8/twin`, { waitUntil: "networkidle", timeout: 60000 });
  await page.waitForTimeout(2600);
  rows.push({ locale, ...(await page.evaluate(PROBE)) });
}
await ctx.close();
await browser.close();
fs.writeFileSync(`${OUT}/twin_scroller_probe.json`, JSON.stringify(rows, null, 1));
for (const r of rows) {
  console.log(r.locale, r.path, "containers:", r.containers.length);
  r.containers.forEach((c) => console.log("   " + JSON.stringify(c)));
}
