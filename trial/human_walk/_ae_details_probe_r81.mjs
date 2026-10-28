// AE probe: answer the one question section 72 left open, in thirty seconds and without a journey.
// Is rev-quick-find-city inside a <details> that is actually open, and what is its own box?
// Everything printed is read off the DOM of the live page -- no guessing about the cause.
import { chromium } from "file:///D:/moodle/_cmdr_rescue_v3_1022/frontend/node_modules/playwright/index.mjs";
import fs from "node:fs";

const BASE = "http://127.0.0.1:14462";
const OUT = "D:/moodle/_cmdr_rescue_v3_1022/trial/results/20261026_gozero/ae-details-probe-r81.txt";
const started = Date.now();
const lines = [];
const note = (v) => { lines.push(v); fs.writeFileSync(OUT, lines.join(String.fromCharCode(10)) + String.fromCharCode(10), "utf8"); };
const elapsed = () => ((Date.now() - started) / 1000).toFixed(1);

const ctx = await chromium.launchPersistentContext("D:/moodle/_cmdr_v3_live_1022/_chrome_gozero_ae81", {
  channel: "chrome", headless: false, viewport: { width: 390, height: 844 }, deviceScaleFactor: 1,
});
const page = ctx.pages()[0] ?? await ctx.newPage();

await page.goto(`${BASE}/revolution`, { waitUntil: "domcontentloaded", timeout: 60000 });
await page.waitForTimeout(6000);
note(`COLD_HAS_EXPLORE ${await page.locator('[data-testid="rev-quick-explore"]').count()} t=${elapsed()}`);

const nav = await page.evaluate(() => Array.from(document.querySelectorAll("button"))
  .map((b) => (b.innerText || "").replace(/\s+/g, " ").trim()).filter(Boolean).slice(0, 40));
note(`NAV_BUTTONS ${JSON.stringify(nav)} t=${elapsed()}`);

for (const label of [/探索/, /手动探索地点/, /去选地点/, /先挑地点/]) {
  const key = page.getByRole("button", { name: label });
  if ((await key.count()) && (await key.first().isVisible().catch(() => false))) {
    await key.first().click().catch(() => undefined);
    note(`ENTERED_BY ${JSON.stringify(String(label))} t=${elapsed()}`);
    await page.waitForTimeout(4000);
    break;
  }
}
note(`EXPLORE_PANE ${await page.locator('[data-testid="rev-quick-explore"]').count()} AREA ${await page.locator('[data-testid="rev-quick-area"]').count()} t=${elapsed()}`);

const shape = await page.evaluate(() => {
  const details = document.querySelector('[data-testid="rev-quick-area-secondary"]');
  const key = document.querySelector('[data-testid="rev-quick-find-city"]');
  const box = (node) => {
    if (!node) return null;
    const r = node.getBoundingClientRect();
    const cs = getComputedStyle(node);
    return { w: Math.round(r.width), h: Math.round(r.height), top: Math.round(r.top),
      display: cs.display, visibility: cs.visibility, opacity: cs.opacity, height: cs.height, overflow: cs.overflow };
  };
  return {
    details: details ? { open: details.open, box: box(details), summary: box(details.querySelector("summary")) } : null,
    key: key ? { box: box(key), parentDisplay: getComputedStyle(key.parentElement).display,
      parentBox: box(key.parentElement), hiddenByAncestor: (() => {
        let node = key;
        while (node && node !== document.body) {
          const cs = getComputedStyle(node);
          if (cs.display === "none" || cs.visibility === "hidden" || Number(cs.opacity) === 0) return node.className || node.tagName;
          node = node.parentElement;
        }
        return null;
      })() } : null,
  };
});
note(`SHAPE ${JSON.stringify(shape)} t=${elapsed()}`);
await page.screenshot({ path: `D:/moodle/_cmdr_rescue_v3_1022/trial/results/20261026_gozero/ae-explore-390-r81.png` }).catch(() => undefined);
note(`ERROR_NONE t=${elapsed()}`);
await ctx.close();
