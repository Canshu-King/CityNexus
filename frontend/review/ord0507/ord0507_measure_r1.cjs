/* ORD-0507: take the BEFORE readings off the production bundle at both shipped locales.
   Judgement reads innerText only -- a data attribute is not what a traveller sees. */
const { chromium } = require("D:/moodle/_qoder_rel_ord0447_wt/frontend/node_modules/playwright");

const PREVIEW = "http://127.0.0.1:61158";
const fs = require("fs");
const seed = JSON.parse(fs.readFileSync("D:/moodle/_qoder_rel_ord0447_wk/ord0507_seed.json", "utf8"));

function isMachineWord(text) {
  /* dotted or snake_case server tokens, and any raw uppercase enum, are what must not reach prose */
  return {
    dotted: (text.match(/\b[a-z]+(\.[a-z_]+)+\b/g) || []),
    snake: (text.match(/\b[a-z]+_[a-z_]+\b/g) || []),
    upper: (text.match(/(^|[^A-Za-z0-9_])[A-Z][A-Z0-9_]{3,}(?![A-Za-z0-9_])/g) || []),
  };
}

(async () => {
  const browser = await chromium.launch();
  const out = [];
  for (const locale of ["zh-CN", "en"]) {
    const page = await browser.newPage({ viewport: { width: 1280, height: 900 } });
    await page.addInitScript(
      ([id, value]) => {
        localStorage.clear();
        localStorage.setItem("citynexus.v8.journey_id", id);
        localStorage.setItem("citynexus.locale", value);
      },
      [seed.journey_id, locale],
    );
    const record = { locale, journeyId: seed.journey_id };

    await page.goto(`${PREVIEW}/v8/access`, { waitUntil: "networkidle" });
    /* The panel asks for its own pick: localStorage's journey id is not enough, so a reading taken
       without choosing measures an empty screen rather than the product. */
    const picker = page.getByTestId("access-journey-picker");
    record.picker_present = (await picker.count()) > 0;
    if (record.picker_present) {
      await picker.selectOption(seed.journey_id);
      await page.waitForTimeout(1200);
    }
    const rows = await page.locator(".cn-access-activity-row").all();
    record.activity_rows = [];
    for (const row of rows) {
      const what = await row.locator(".cn-access-what").innerText();
      record.activity_rows.push({ what, machine_words: isMachineWord(what) });
    }
    record.activity_row_count = record.activity_rows.length;

    await page.goto(`${PREVIEW}/v8/hub`, { waitUntil: "networkidle" });
    const clock = page.getByTestId("today-clock-source");
    record.clock_present = (await clock.count()) > 0;
    if (record.clock_present) {
      record.clock_text = (await clock.innerText()).replace(/\s+/g, " ").trim();
      record.clock_parenthesised_clause = /[（(][^）)]*[。.]|\([^)]*\.\s*[^)]*\)/.test(record.clock_text)
        ? "YES: a full sentence sits inside the brackets"
        : "NO";
    }
    const simJourney = page.getByTestId("sim-journey");
    record.today_sim_journey_present = (await simJourney.count()) > 0;
    if (record.today_sim_journey_present) {
      record.today_sim_journey_text = (await simJourney.first().innerText()).replace(/\s+/g, " ").trim();
    }
    record.today_html_lang = await page.evaluate(() => document.documentElement.lang || "none");
    await page.close();
    out.push(record);
  }
  await browser.close();
  const text = JSON.stringify(out, null, 2);
  fs.writeFileSync("D:/moodle/_qoder_rel_ord0447_wk/ord0507_before_readings.json", text);
  console.log(text);
})();
