// Does the search field ever show text that is not the filter in force?
// The mobile screenshot showed a stale query in the box while the list was unfiltered.
import { createRequire } from "node:module";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";
const require = createRequire(import.meta.url);
const HERE = dirname(fileURLToPath(import.meta.url));
const { chromium } = require(
  resolve(join(HERE, "..", "..", "frontend", "node_modules", "playwright"), "."),
);

const LAB =
  "http://127.0.0.1:6199/iframe.html?id=controls-select--long-list-searchable-arm&viewMode=story";
const SEARCH = '[data-testid="lab-searchable-select-search"]';
const LIST = '[data-testid="lab-searchable-select-list"]';
const COUNT = '[data-testid="lab-searchable-select-count"]';

const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 390, height: 844 } });
await page.goto(LAB, { waitUntil: "domcontentloaded" });
await page.waitForTimeout(900);
await page.locator('[data-testid="lab-searchable-select"]').click();
await page.waitForTimeout(150);

const snap = async (label) => {
  const read = await page.evaluate(
    ([s, l, c]) => ({
      input_value: document.querySelector(s)?.value ?? null,
      painted: document.querySelector(l)?.querySelectorAll('[role="option"]').length ?? null,
      count: document.querySelector(c)?.textContent?.trim() ?? null,
    }),
    [SEARCH, LIST, COUNT],
  );
  console.log(label, JSON.stringify(read));
  return read;
};

await snap("opened          ");
await page.locator(SEARCH).fill("zzqx nothing matches this");
await page.waitForTimeout(200);
await snap("typed no-match  ");
await page.locator(SEARCH).fill("");
await page.waitForTimeout(200);
const cleared = await snap("cleared by fill ");

// Then the same scroll loop the ruler runs, and read the box again at the end.
for (let step = 0; step < 6; step += 1) {
  await page.evaluate((sel) => {
    const list = document.querySelector(sel);
    list.scrollTop = list.scrollTop + 500;
  }, LIST);
  await page.waitForTimeout(40);
}
const afterScroll = await snap("after scroll    ");
await page.screenshot({ path: "D:/moodle/_select_shots/lab_mobile_after_clear.png" });

const honest =
  cleared.input_value === "" && cleared.painted > 0 && afterScroll.input_value === "";
console.log(
  honest
    ? "VERDICT: the box always shows the filter in force"
    : "VERDICT: the box can disagree with the filter -- real defect",
);
await browser.close();
