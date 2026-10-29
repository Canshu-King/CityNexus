/** Bring the selected card's heading into view (start of card, clear of the sticky header) and
 * capture 390x844 / 430x932. */
import { createRequire } from "node:module";
import fs from "node:fs";
const require = createRequire("D:/moodle/_cmdr_rescue_v3_1022/frontend/package.json");
const { chromium } = require("playwright");
const DIR = "D:/moodle/_cmdr_rescue_v3_1022/trial/results/20261022_v3_human_chrome";
const log = [];
const emit = (s) => { log.push(s); fs.writeFileSync(DIR + "/pw-capture-selected-4.txt", log.join("\n") + "\n"); };
const browser = await chromium.connectOverCDP("http://127.0.0.1:9335");
const ctx = browser.contexts()[0];
const pages = ctx.pages().filter((p) => (p.url() || "").includes("14461"));
let page = null;
for (const p of pages) {
  try {
    if (await p.evaluate(() => [...document.querySelectorAll("[data-testid='rev-plan-option']")].some((n) => n.innerText.includes("已选用")))) { page = p; break; }
  } catch {}
}
if (!page) { emit("NO_PAGE"); console.log(log.join("\n")); await browser.close(); process.exit(0); }
const bringTop = () => page.evaluate(() => {
  const flat = (v) => String(v ?? "").replace(/\s+/g, " ").trim();
  const card = [...document.querySelectorAll("[data-testid='rev-plan-option']")].find((n) => flat(n.innerText).includes("已选用"));
  if (!card) return { found: false };
  card.scrollIntoView({ block: "start" });
  window.scrollBy(0, -300);
  return { found: true, head: flat(card.innerText).slice(0, 60), top: Math.round(card.getBoundingClientRect().top) };
});
await page.setViewportSize({ width: 390, height: 844 });
await page.waitForTimeout(1200);
emit(`M390 ${JSON.stringify(await page.evaluate(() => ({ w: innerWidth, h: innerHeight, dpr: devicePixelRatio })))}`);
emit(`B390 ${JSON.stringify(await bringTop())}`);
await page.waitForTimeout(700);
await page.screenshot({ path: DIR + "/walk-final-390.png", animations: "disabled", timeout: 60000 });
emit(`SHOT390 ${fs.statSync(DIR + "/walk-final-390.png").size}`);
await page.setViewportSize({ width: 430, height: 932 });
await page.waitForTimeout(1200);
emit(`M430 ${JSON.stringify(await page.evaluate(() => ({ w: innerWidth, h: innerHeight, dpr: devicePixelRatio })))}`);
emit(`B430 ${JSON.stringify(await bringTop())}`);
await page.waitForTimeout(700);
await page.screenshot({ path: DIR + "/walk-final-430.png", animations: "disabled", timeout: 60000 });
emit(`SHOT430 ${fs.statSync(DIR + "/walk-final-430.png").size}`);
await browser.close();
console.log(log.join("\n"));
