// Dumps the POI-import screen's rendered text for one generation. Lives OUTSIDE the repo tree so it
// can be run against two different checkouts without a branch switch eating the script.
const path = require("path");
const fs = require("fs");
const NM = "D:/moodle/_qoder_newlane_ord0496/frontend/node_modules";
const { chromium } = require(path.join(NM, "playwright"));

const [ , , baseUrl, outPath, journeyId ] = process.argv;

(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 390, height: 844 } });
  await page.addInitScript(([id]) => {
    localStorage.setItem("citynexus.v8.journey_id", id);
    localStorage.setItem("citynexus.locale", "zh-CN");
  }, [journeyId]);
  await page.goto(`${baseUrl}/v8/import`, { waitUntil: "domcontentloaded", timeout: 60000 });
  try {
    await page.waitForSelector('[data-testid="poi-import"]', { timeout: 60000 });
  } catch (error) {
    // Never fail without a reading: what IS on the glass, and who answered the API.
    const text = await page.evaluate(() => document.body.innerText).catch(() => "");
    fs.writeFileSync(outPath.replace(/\.txt$/, ".failed.txt"),
      `selector never appeared\nurl: ${page.url()}\n\n${text}\n`, "utf-8");
    throw error;
  }
  await page.waitForLoadState("networkidle").catch(() => {});
  const text = await page.evaluate(() => document.body.innerText);
  const label = await page.locator(".v8-evidence-label").innerText();
  fs.writeFileSync(outPath, text, "utf-8");
  fs.writeFileSync(outPath.replace(/\.txt$/, ".label.txt"), label, "utf-8");
  console.log(JSON.stringify({ out: outPath, characters: text.length, label }));
  await browser.close();
})().catch((error) => {
  console.error("DUMP_FAILED", error.message);
  process.exit(1);
});
