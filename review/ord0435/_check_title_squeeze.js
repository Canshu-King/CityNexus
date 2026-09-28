/* Does the tick control I added squeeze the card title into the eligibility badge?
 * Measured in the same place the four-cell gauge already reaches: the first result card at 390x844.
 * Reports the three boxes, the h3/badge overlap area, and how many line boxes the title is broken
 * into (Range.getClientRects is the only thing that sees a wrap). */
const { chromium } = require("D:/moodle/CityNexus/frontend/node_modules/playwright");

const BASE = process.argv[2] || "http://127.0.0.1:4835";
const OUT = process.argv[3] || "D:/moodle/_qoder_b_ord0435b_20260929/review/ord0435";

(async () => {
  const browser = await chromium.launch();
  const ctx = await browser.newContext({ locale: "zh-CN", viewport: { width: 390, height: 844 } });
  await ctx.addInitScript(() => {
    localStorage.clear();
    localStorage.setItem("citynexus.locale", "zh-CN");
    localStorage.setItem("citynexus.v8.journey_id", "22222222-2222-4222-8222-222222222222");
  });
  const page = await ctx.newPage();
  await page.goto(BASE + "/v8/hub", { waitUntil: "load" });
  await page.waitForSelector('[data-testid="today-hero"]', { timeout: 180_000 }).catch(() => {});
  await page.goto(BASE + "/v8/discover", { waitUntil: "load" });
  await page.waitForSelector('[data-testid="v13-discovery-goal"]', { timeout: 150_000 }).catch(() => {});
  await page.locator('[data-testid="v13-discovery-goal"]').fill("河边适合散步咖啡");
  await page.locator("select[aria-label]").first().selectOption("replay");
  await page.locator('[data-testid="v13-discover-submit"]').click();
  await page.waitForSelector("article.v8-stay-card", { timeout: 150_000 }).catch(() => {});
  await page.waitForTimeout(1000);

  const reading = await page.evaluate(() => {
    const card = document.querySelector("article.v8-stay-card");
    if (!card) return { error: "NO_CARD" };
    const h3 = card.querySelector("h3");
    const label = card.querySelector(".v8-selected-label");
    const tick = card.querySelector('[data-testid="v13-pick-candidate"]');
    const r = (el) => {
      if (!el) return null;
      const b = el.getBoundingClientRect();
      return { x: Math.round(b.left), y: Math.round(b.top), w: Math.round(b.width), h: Math.round(b.height) };
    };
    const overlap = (a, c) => {
      const w = Math.min(a.right, c.right) - Math.max(a.left, c.left);
      const hh = Math.min(a.bottom, c.bottom) - Math.max(a.top, c.top);
      return w > 0 && hh > 0 ? Math.round(w * hh) : 0;
    };
    const hb = h3.getBoundingClientRect();
    const lb = label.getBoundingClientRect();
    const cb = card.getBoundingClientRect();
    return {
      card_box: r(card),
      card_width: Math.round(cb.width),
      h3_box: r(h3),
      badge_box: r(label),
      tick_box: r(tick),
      h3_badge_overlap_area: overlap(hb, lb),
      h3_line_boxes: h3.getClientRects().length,
      h3_text: (h3.textContent || "").replace(/\s+/g, " ").slice(0, 60),
      tick_width: tick ? Math.round(tick.getBoundingClientRect().width) : null,
      space_taken_by_tick_pct: tick ? Math.round((tick.getBoundingClientRect().width / cb.width) * 100) : null,
    };
  });
  console.log(JSON.stringify(reading, null, 1));

  const box = await page.locator("article.v8-stay-card").first().boundingBox();
  if (box) {
    await page.locator("article.v8-stay-card").first().scrollIntoViewIfNeeded();
    const after = await page.locator("article.v8-stay-card").first().boundingBox();
    await page.screenshot({
      path: OUT + "/card_row_zoom_" + (process.argv[4] || "now") + ".png",
      clip: { x: 0, y: Math.max(0, Math.round(after.y)), width: 390, height: Math.min(300, Math.round(after.height)) },
    });
  }
  await browser.close();
})();
