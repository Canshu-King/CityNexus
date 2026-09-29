/* ORD-0435 counter-word check (lane dt, be19052c) -- the third thing the commander asked for.
 *
 * "只选一个与选两个时计数句的单复数形各自逐字": tick one card, read every sentence on the batch bar
 * verbatim; tick a second, read them again. Both locales. Nothing here judges a shape -- it prints
 * what the screen actually says, so the singular/plural question can be answered with bytes rather
 * than with a claim about the dictionary.
 *
 * Why the bar and not the dictionary file: a key can carry a `_pl`/`_sg` pair and still render one
 * form, and a single key can render two forms if the sentence itself declines. Only the rendered
 * string settles it.
 */
const { chromium } = require("D:/moodle/CityNexus/frontend/node_modules/playwright");
const fs = require("fs");

const BASE = process.argv[2] || "http://127.0.0.1:4835";
const OUT = process.argv[3] || "D:/moodle/_qoder_b_ord0435b_20260929/review/ord0435";
fs.mkdirSync(OUT, { recursive: true });

const S = {
  goal: '[data-testid="v13-discovery-goal"]',
  submit: '[data-testid="v13-discover-submit"]',
  mode: 'select[aria-label]',
  cards: "article.v8-stay-card",
  bar: '[data-testid="v13-discovery-batch-bar"]',
  count: '[data-testid="v13-discovery-picked-count"]',
  target: '[data-testid="v13-discovery-batch-target"]',
  note: '[data-testid="v13-discovery-batch-note"]',
  empty: '[data-testid="v13-discovery-batch-empty"]',
  tick: '[data-testid="v13-pick-candidate"]',
  finish: '[data-testid="v13-discovery-finish-batch"]',
  fresh: '[data-testid="v13-discovery-new-batch"]',
};

async function arm(browser, locale, journeyId) {
  const ctx = await browser.newContext({ locale, viewport: { width: 390, height: 844 } });
  await ctx.addInitScript((seed) => {
    localStorage.clear();
    localStorage.setItem("citynexus.locale", seed.locale);
    localStorage.setItem("citynexus.v8.journey_id", seed.journey);
  }, { locale, journey: journeyId });
  const warm = await ctx.newPage();
  await warm.goto(BASE + "/v8/hub", { waitUntil: "load" });
  await warm.waitForSelector('[data-testid="today-hero"]', { timeout: 180_000 }).catch(() => {});
  await warm.close();

  const page = await ctx.newPage();
  await page.goto(BASE + "/v8/discover", { waitUntil: "load" });
  await page.waitForSelector(S.goal, { timeout: 150_000 }).catch(() => {});
  await page.locator(S.goal).fill(locale.startsWith("zh") ? "河边适合散步咖啡" : "riverside walk and coffee");
  await page.locator(S.mode).first().selectOption("replay");
  await page.locator(S.submit).click();
  await page.waitForSelector(S.cards, { timeout: 150_000 }).catch(() => {});
  await page.waitForTimeout(1200);

  const read = async () => ({
    count: (await page.locator(S.count).innerText().catch(() => null))?.replace(/\s+/g, " ") ?? null,
    target: (await page.locator(S.target).innerText().catch(() => null))?.replace(/\s+/g, " ") ?? null,
    note: (await page.locator(S.note).count())
      ? (await page.locator(S.note).innerText()).replace(/\s+/g, " ")
      : null,
    empty: (await page.locator(S.empty).count())
      ? (await page.locator(S.empty).innerText()).replace(/\s+/g, " ")
      : null,
    bar_text: (await page.locator(S.bar).innerText().catch(() => null))?.replace(/\s+/g, " ") ?? null,
    ticks_checked: await page.locator(`${S.tick}[aria-checked="true"]`).count(),
    finish_label: (await page.locator(S.finish).innerText().catch(() => null))?.replace(/\s+/g, " ") ?? null,
    fresh_label: (await page.locator(S.fresh).innerText().catch(() => null))?.replace(/\s+/g, " ") ?? null,
  });

  const out = { locale, cards: await page.locator(S.cards).count() };
  out.zero = await read();
  await page.locator(S.tick).nth(0).click();
  await page.waitForTimeout(400);
  out.one = await read();
  await page.locator(S.tick).nth(1).click();
  await page.waitForTimeout(400);
  out.two = await read();
  await page.screenshot({ path: `${OUT}/counter_${locale}_two.png`, fullPage: false });
  out.differ_between_one_and_two = out.one.count !== out.two.count;
  out.count_forms = { one: out.one.count, two: out.two.count };
  await ctx.close();
  return out;
}

(async () => {
  const scene = await (await fetch(BASE + "/api/v1/demo/scene")).json();
  const journeyId = String(scene.journey_id ?? "");
  if (journeyId.length < 8) throw new Error("stage named no journey");
  const browser = await chromium.launch();
  const zh = await arm(browser, "zh-CN", journeyId);
  const en = await arm(browser, "en", journeyId);
  await browser.close();
  fs.writeFileSync(`${OUT}/counter_words.json`, JSON.stringify({ base: BASE, journey_id: journeyId, zh, en }, null, 1), "utf-8");
  console.log(JSON.stringify({ zh: { one: zh.one.count, two: zh.two.count, note_one: zh.one.note, note_two: zh.two.note }, en: { one: en.one.count, two: en.two.count, note_one: en.one.note, note_two: en.two.note } }, null, 1));
})();
