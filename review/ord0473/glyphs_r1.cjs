/* ORD-0473: the toggle's own rendered glyph and accessible name, read through the accessibility tree
   and the computed ::after -- if the "×" rule did not apply, the control would go blank on a phone. */
const { chromium } = require("D:\\moodle\\CityNexus\\frontend\\node_modules\\playwright");
const fs = require("fs");
const BASE = process.argv[2], OUT = process.argv[3];
(async () => {
  const browser = await chromium.launch();
  const ctx = await browser.newContext({ viewport: { width: 390, height: 844 }, deviceScaleFactor: 1, isMobile: true, hasTouch: true });
  const page = await ctx.newPage();
  await page.goto(BASE + "/v8/hub", { waitUntil: "load" });
  await page.waitForTimeout(4000);
  if (await page.locator('[data-testid="trial-setup"]').count()) {
    await page.locator('[data-testid="trial-tianjin-demo"]').click({ timeout: 10000 }).catch(() => {});
    await page.waitForTimeout(4000);
  }
  const read = async (label) => {
    const g = await page.evaluate(() => {
      const m = document.querySelector(".v8-mobile-menu");
      const cs = getComputedStyle(m, "::after");
      const r = m.getBoundingClientRect();
      return { glyph: cs.content, glyph_font_size: cs.fontSize, label_text: m.innerText, expanded: m.getAttribute("aria-expanded"),
               aria_label: m.getAttribute("aria-label"), box: { x: Math.round(r.x), y: Math.round(r.y), w: Math.round(r.width), h: Math.round(r.height) } };
    });
    return { step: label, ...g };
  };
  const press = async () => {
    let err = null;
    try { await page.locator("button.v8-mobile-menu").first().click({ timeout: 6000 }); }
    catch (e) { err = String(e).split("\n")[0].slice(0, 120); }
    await page.waitForTimeout(900);
    return err;
  };
  const rec = [];
  rec.push(Object.assign({ press_error: null }, await read("closed")));
  rec.push(Object.assign({ press_error: await press() }, await read("open")));
  rec.push(Object.assign({ press_error: await press() }, await read("closed_again")));
  fs.writeFileSync(OUT, JSON.stringify(rec, null, 1));
  await browser.close();
})();
