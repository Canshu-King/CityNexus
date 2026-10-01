/* ORD-0507 item 1: read what /v8/access actually paints, at a given bundle, in both shipped locales.
   Judgement is innerText of the row -- a data attribute is not what a traveller sees. */
const { chromium } = require("D:/moodle/_qoder_rel_ord0447_wt/frontend/node_modules/playwright");
const fs = require("fs");

const BASE = process.argv[2];
const PHASE = process.argv[3];
const seed = JSON.parse(fs.readFileSync("D:/moodle/_qoder_rel_ord0447_wk/ord0507_seed.json", "utf8"));

// a server action name is dotted or snake_case; none of those may sit in a sentence
const MACHINE = /\b[a-z]+[._][a-z0-9_.]+\b/;

(async () => {
  const browser = await chromium.launch();
  const out = { phase: PHASE, bundle: BASE, journeyId: seed.journey_id, locales: [] };
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
    const rec = { locale };
    await page.goto(`${BASE}/v8/access`, { waitUntil: "networkidle" });
    const picker = page.getByTestId("access-journey-picker");
    rec.picker_present = (await picker.count()) > 0;
    if (rec.picker_present) {
      await picker.selectOption(seed.journey_id);
      await page.waitForTimeout(1500);
    }
    const rows = await page.locator(".cn-access-activity-row").all();
    rec.rows = [];
    for (const row of rows) {
      const what = row.locator(".cn-access-what");
      const visible = (await what.innerText()).replace(/\s+/g, " ").trim();
      const fold = what.locator("details[data-testid='access-activity-technical']");
      const foldPresent = (await fold.count()) > 0;
      let raw = null;
      if (foldPresent) {
        await fold.locator("summary").click();
        raw = (await what.locator('[data-testid="access-activity-raw"]').innerText())
          .replace(/\s+/g, " ").trim();
      }
      rec.rows.push({
        visible_sentence: visible,
        machine_word_in_visible_sentence: MACHINE.test(visible),
        technical_fold_count: foldPresent ? 1 : 0,
        raw_inside_fold: raw,
      });
    }
    rec.row_count = rec.rows.length;
    // the announced layer too: a collapsed fold's text is in the DOM, so the painted layer is the one
    // that may not carry the token
    rec.html_lang = await page.evaluate(() => document.documentElement.lang || "none");
    await page.close();
    out.locales.push(rec);
  }
  await browser.close();
  const file = `D:/moodle/_qoder_rel_ord0447_wk/ord0507_access_${PHASE}.json`;
  fs.writeFileSync(file, JSON.stringify(out, null, 2));
  console.log(JSON.stringify(out, null, 2));
})();
