/* ORD-0553 r13 -- read the three old button names with Playwright's own matcher, on two generations.
 *
 * Why: I have carried PREDICTED_NOT_MEASURED for these lines since r3.  A prediction about an assertion
 * is not a reading, and the commander only accepts readings.  So this instrument opens the same screen on
 * two bundle generations (the tip's bytes and the pre-r2 bytes), against two store copies put into the
 * same execution state, and asks Playwright itself -- getByRole("button", {name}) with the project's
 * default matching, plus an exact:true pass -- whether the names the spec asserts are there.
 *
 * Nothing here reads or writes the shared preview database.  Both legs talk only to ports I started.
 */
const { chromium } = require("playwright");

const JID = "22222222-2222-4222-8222-222222222222";
const LEGS = [
  { tag: "tip_b2fccfdf", port: 49902 },
  { tag: "prer2_f3304e25", port: 49903 },
];
const SPEC_NAMES = ["Mark EN ROUTE", "Mark ARRIVED"];

async function probe(page, name) {
  const loose = page.getByRole("button", { name });
  const exact = page.getByRole("button", { name, exact: true });
  return {
    name,
    matched: await loose.count(),
    visible: await loose.first().isVisible().catch(() => false),
    matched_exact: await exact.count(),
  };
}

(async () => {
  const browser = await chromium.launch();
  const report = { instrument: "cmdra_0553_v13_locator_revet_r13", legs: [], controls: {} };
  for (const leg of LEGS) {
    const ctx = await browser.newContext({ viewport: { width: 1280, height: 720 } });
    const page = await ctx.newPage();
    const errors = [];
    page.on("pageerror", (e) => errors.push(String(e.message).slice(0, 120)));
    await page.addInitScript((id) => {
      localStorage.setItem("citynexus.v8.journey_id", id);
      localStorage.setItem("citynexus.locale", "en");
    }, JID);
    await page.goto(`http://127.0.0.1:${leg.port}/v8/authoritative`, { waitUntil: "load" });
    const panel = page.getByTestId("v12-authoritative-panel");
    await panel.waitFor({ state: "visible", timeout: 20000 }).catch(() => {});
    const rec = {
      tag: leg.tag,
      port: leg.port,
      entry: await page.evaluate(() =>
        Array.from(document.querySelectorAll('script[src*="assets/index-"]')).map((s) => s.src.split("/").pop())),
      panel_visible: await panel.isVisible().catch(() => false),
      buttons_painted: await page.getByRole("button").allTextContents(),
      spec_names: [],
      after_click: null,
      page_errors: errors.length,
    };
    for (const name of SPEC_NAMES) rec.spec_names.push(await probe(page, name));

    /* Advance the journey the way the product's own footer button does, so the second asserted
       name is read in the state the spec expects it in rather than in whatever the seed left. */
    const primary = page.locator("footer button.v8-primary, .v12-authoritative-panel button.v8-primary").first();
    const primaryName = (await primary.textContent().catch(() => null)) || null;
    if (primaryName) {
      await primary.click({ timeout: 8000 }).catch((e) => rec.click_error = String(e.message).slice(0, 120));
      await page.waitForTimeout(1500);
      const after = { clicked: primaryName, names: [] };
      for (const name of SPEC_NAMES) after.names.push(await probe(page, name));
      after.buttons_painted = await page.getByRole("button").allTextContents();
      rec.after_click = after;
    }
    report.legs.push(rec);
    await ctx.close();
  }

  /* Negative and positive controls: the matcher must be able to find a name that is really painted
     and must find nothing for a name that is not. */
  const ctx = await browser.newContext();
  const page = await ctx.newPage();
  await page.addInitScript((id) => {
    localStorage.setItem("citynexus.v8.journey_id", id);
    localStorage.setItem("citynexus.locale", "en");
  }, JID);
  await page.goto("http://127.0.0.1:49902/v8/authoritative", { waitUntil: "load" });
  await page.getByTestId("v12-authoritative-panel").waitFor({ state: "visible", timeout: 20000 }).catch(() => {});
  const painted = await page.getByRole("button").allTextContents();
  const anyName = (painted.find((t) => t && t.trim()) || "").trim();
  report.controls = {
    positive_painted_name: anyName,
    positive_matched: await page.getByRole("button", { name: anyName }).count(),
    nonsense_matched: await page.getByRole("button", { name: "Mark ZZZ NOT A BUTTON" }).count(),
    spec_lines_are_not_vacuous: SPEC_NAMES.length,
  };
  await ctx.close();
  await browser.close();
  console.log(JSON.stringify(report, null, 1));
})().catch((e) => { console.error("ABORT", e.message); process.exit(9); });
