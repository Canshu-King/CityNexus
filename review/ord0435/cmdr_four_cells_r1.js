/* ORD-0435 — the four cells the commander could not reach on its own machine (lane dt, be19052c).
 *
 * Ledger `D:/moodle/CITYNEXUS_AGENT_CONTROL.md:17134` (CMDR 06:44) judged the order
 * `LANDED · SCREEN_NOT_ACCEPTED` and named exactly four cells it did not measure:
 *   C1 does the batch bar appear at all;
 *   C2 does the count text move when a card is ticked;
 *   C3 does the bar press into the bottom-nav band (its `.v8-mobile-nav` top edge is at 768 px);
 *   C4 does the bar carry a machine token.
 * Each cell is answered twice per locale, on the pre-change bytes and on the post-change bytes.
 *
 * Three rules this instrument exists to obey, all learned from failures already in the ledger:
 *   - run a discovery first. The panel renders no result area, and so no bar, until the goal
 *     textarea holds >= 3 characters and 探索并组合 has answered;
 *   - never tick "a visible button". The tick is `[data-testid="v13-pick-candidate"]`, and the first
 *     version of the commander's gauge struck the top-bar hamburger instead;
 *   - an absent bar is not a clean measurement. C3 and C4 answer `NOT_MEASURED_BAR_ABSENT` when the
 *     bar is not there, never "0 overlap" -- that is the empty-denominator false green the commander
 *     named against its own instrument. C3 additionally hit-tests the bar's own centre after
 *     scrolling it into the viewport, because a bounding box that merely misses the nav on a
 *     2,000 px page says nothing about a thumb.
 */
const { chromium } = require("D:/moodle/CityNexus/frontend/node_modules/playwright");
const fs = require("fs");

const BASE = process.argv[2] || "http://127.0.0.1:4835";
const OUT = process.argv[3] || "D:/moodle/_qoder_b_ord0435b_20260929/review/ord0435";
const SIDE = process.argv[4] || "unknown";
fs.mkdirSync(OUT, { recursive: true });

const SEL = {
  console: '[data-testid="v13-discovery"]',
  goal: '[data-testid="v13-discovery-goal"]',
  submit: '[data-testid="v13-discover-submit"]',
  mode: 'select[aria-label]',
  cards: "article.v8-stay-card",
  bar: '[data-testid="v13-discovery-batch-bar"]',
  count: '[data-testid="v13-discovery-picked-count"]',
  tick: '[data-testid="v13-pick-candidate"]',
  finish: '[data-testid="v13-discovery-finish-batch"]',
  fresh: '[data-testid="v13-discovery-new-batch"]',
  nav: "nav.v8-mobile-nav",
};

/* A machine token is the shape the ledger keeps arguing about: SCREAMING_SNAKE. Enumerating what is
   actually inside the bar is the only honest way to answer "does it carry one". */
const TOKEN_RE = /\b[A-Z][A-Z0-9]{1,}(?:_[A-Z0-9]+)+\b/g;

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
  await page.waitForSelector(SEL.goal, { timeout: 150_000 }).catch(() => {});

  const out = { locale, reached: new URL(page.url()).pathname, console_present: 0, cards: 0 };
  out.console_present = await page.locator(SEL.console).count();
  if (!out.console_present || !(await page.locator(SEL.goal).count())) {
    out.error = "CONSOLE_NOT_MOUNTED";
    await ctx.close();
    return out;
  }

  /* Rule one: a discovery has to actually run, or there is no bar to measure. */
  await page.locator(SEL.goal).fill(locale.startsWith("zh") ? "河边适合散步咖啡" : "riverside walk and coffee");
  await page.locator(SEL.mode).first().selectOption("replay").catch(() => {});
  await page.locator(SEL.submit).click();
  await page
    .waitForSelector(SEL.cards, { timeout: 150_000 })
    .catch(() => {});
  await page.waitForTimeout(1200);
  out.cards = await page.locator(SEL.cards).count();
  if (!out.cards) {
    out.error = "NO_RESULT_CARDS";
    out.error_text = (await page.locator('[data-testid="v13-discovery-error"]').count())
      ? (await page.locator('[data-testid="v13-discovery-error"]').innerText()).replace(/\s+/g, " ").slice(0, 200)
      : null;
    await ctx.close();
    return out;
  }

  /* ---- C1 ---- */
  const bar = page.locator(SEL.bar);
  out.C1_batch_bar = {
    present: (await bar.count()) > 0,
    nodes: await bar.count(),
    denominator: `${out.cards} result cards on screen`,
  };

  /* ---- C2 ---- */
  const countText = async () =>
    (await bar.count()) && (await page.locator(SEL.count).count())
      ? (await page.locator(SEL.count).innerText()).replace(/\s+/g, " ")
      : "NOT_MEASURED_BAR_ABSENT";
  out.C2_count_text = { before_tick: await countText() };
  if (await page.locator(SEL.tick).count()) {
    await page.locator(SEL.tick).first().click();
    await page.waitForTimeout(400);
    out.C2_count_text.after_first_tick = await countText();
    out.C2_count_text.ticks_on_screen = await page.locator(SEL.tick).count();
    out.C2_count_text.checked_now = await page.locator(`${SEL.tick}[aria-checked="true"]`).count();
    await page.locator(SEL.tick).first().click();
    await page.waitForTimeout(300);
    out.C2_count_text.after_untick = await countText();
    out.C2_count_text.changed =
      out.C2_count_text.before_tick !== out.C2_count_text.after_first_tick;
  } else {
    out.C2_count_text.after_first_tick = "NOT_MEASURED_NO_TICK_CONTROL";
    out.C2_count_text.changed = "NOT_MEASURED_NO_TICK_CONTROL";
  }

  /* ---- C3: scroll the bar into the viewport, then hit-test it against the real nav edge ---- */
  if (out.C1_batch_bar.present) {
    await bar.scrollIntoViewIfNeeded();
    await page.evaluate(() => {
      const el = document.querySelector('[data-testid="v13-discovery-batch-bar"]');
      el?.scrollIntoView({ block: "center" });
    });
    await page.waitForTimeout(400);
    out.C3_nav_band = await page.evaluate((s) => {
      const rect = (sel) => {
        const el = document.querySelector(sel);
        if (!el) return null;
        const r = el.getBoundingClientRect();
        return { top: Math.round(r.top), bottom: Math.round(r.bottom), height: Math.round(r.height), left: Math.round(r.left), right: Math.round(r.right) };
      };
      const bar = rect('[data-testid="v13-discovery-batch-bar"]');
      const nav = rect("nav.v8-mobile-nav");
      const press = (box) => (box && nav ? Math.max(0, box.bottom - nav.top) : null);
      const centreHit = (box) => {
        if (!box) return null;
        const hit = document.elementFromPoint((box.left + box.right) / 2, (box.top + box.bottom) / 2);
        if (!hit) return "NO_ELEMENT_AT_CENTRE";
        const barEl = document.querySelector('[data-testid="v13-discovery-batch-bar"]');
        if (barEl && barEl.contains(hit)) return "HITS_OWN_BAR";
        return `HITS_${hit.tagName.toLowerCase()}${hit.closest("nav.v8-mobile-nav") ? "_INSIDE_MOBILE_NAV" : ""}`;
      };
      const finish = rect('[data-testid="v13-discovery-finish-batch"]');
      const fresh = rect('[data-testid="v13-discovery-new-batch"]');
      return {
        bar,
        nav,
        nav_top_measured_px: nav ? nav.top : "NO_NAV_ELEMENT",
        bar_presses_nav_px: press(bar),
        finish_presses_nav_px: press(finish),
        fresh_presses_nav_px: press(fresh),
        bar_centre_hit: centreHit(bar),
        finish_centre_hit: centreHit(finish),
        fresh_centre_hit: centreHit(fresh),
        viewport: { w: window.innerWidth, h: window.innerHeight },
      };
    }, null);
    await page.screenshot({ path: `${OUT}/${SIDE}_${locale}_C3_bar_in_view.png` });
  } else {
    out.C3_nav_band = {
      bar: null,
      nav_top_measured_px: await page.evaluate(() => {
        const el = document.querySelector("nav.v8-mobile-nav");
        return el ? Math.round(el.getBoundingClientRect().top) : "NO_NAV_ELEMENT";
      }),
      bar_presses_nav_px: "NOT_MEASURED_BAR_ABSENT",
      bar_centre_hit: "NOT_MEASURED_BAR_ABSENT",
    };
  }

  /* ---- C4 ---- */
  if (out.C1_batch_bar.present) {
    const barText = (await bar.innerText()).replace(/\s+/g, " ");
    const tokens = Array.from(new Set(barText.match(TOKEN_RE) ?? []));
    out.C4_machine_tokens = { text: barText.slice(0, 300), tokens, token_count: tokens.length };
  } else {
    out.C4_machine_tokens = {
      text: "NOT_MEASURED_BAR_ABSENT",
      tokens: "NOT_MEASURED_BAR_ABSENT",
      token_count: "NOT_MEASURED_BAR_ABSENT",
    };
  }

  await page.screenshot({ path: `${OUT}/${SIDE}_${locale}_full.png`, fullPage: true });
  await ctx.close();
  return out;
}

(async () => {
  const scene = await (await fetch(BASE + "/api/v1/demo/scene")).json();
  const journeyId = String(scene.journey_id ?? "");
  if (journeyId.length < 8) throw new Error("stage named no journey: " + JSON.stringify(scene).slice(0, 200));
  const browser = await chromium.launch();
  const zh = await arm(browser, "zh-CN", journeyId);
  const en = await arm(browser, "en", journeyId);
  await browser.close();
  const report = { side: SIDE, base: BASE, journey_id: journeyId, zh, en };
  fs.writeFileSync(`${OUT}/four_cells_${SIDE}.json`, JSON.stringify(report, null, 1), "utf-8");
  for (const a of [zh, en]) {
    console.log(
      JSON.stringify(
        {
          locale: a.locale,
          cards: a.cards,
          C1: a.C1_batch_bar,
          C2: a.C2_count_text,
          C3: {
            nav_top: a.C3_nav_band?.nav_top_measured_px,
            bar_presses: a.C3_nav_band?.bar_presses_nav_px,
            finish_presses: a.C3_nav_band?.finish_presses_nav_px,
            bar_hit: a.C3_nav_band?.bar_centre_hit,
            finish_hit: a.C3_nav_band?.finish_centre_hit,
          },
          C4: a.C4_machine_tokens,
        },
        null,
        1,
      ),
    );
  }
})();
