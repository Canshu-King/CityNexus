/* ORD-0435 AFTER-fix probe, p1 (lane be19052c).
 *
 * Drives the batch the order asked for and reads the screen back as rendered text, in both locales.
 * Arrival is the one the before-probe had to learn the hard way about (see
 * `_probe_multiselect_before_p3.js`: a count taken on the onboarding wizard or on the shell's
 * loading screen is a count of nothing).
 *
 * What each arm records, in this order:
 *   A0  the five checkpoints before anyone ticks anything: one tick control per card, every control
 *       in its unselected twin, the count reading zero, the empty state present, 完成 disabled,
 *       完成 and 新建 in the same horizontal band;
 *   A1  one tick: the count moves, the empty state goes, the control flips to its selected twin;
 *   A2  完成: the compose route writes, and the screen then shows what a *second* GET returned --
 *       the receipt rows carry activity ids this component never produced;
 *   A3  新建一批: the batch is empty again and the receipt is gone (a receipt that outlives its
 *       batch would be a stale claim on screen);
 *   A4  two ticks and 完成: the planner's own refusal (`V13_ACTIVITY_OUTSIDE_DEPARTURE_WINDOW`,
 *       measured against this store) has to reach the traveller as a named refusal, not as "added".
 *
 * The server-side reconciliation is a separate script (`_readback_after_p1.js`) that queries the
 * route with no browser in the loop, so the screen's claim and the store's answer are two readings.
 */
const { chromium } = require("D:/moodle/CityNexus/frontend/node_modules/playwright");
const fs = require("fs");

const BASE = process.argv[2] || "http://127.0.0.1:4817";
const OUT = process.argv[3] || "D:/moodle/_qoder_b_ord0435_20260929/_probe_after_p1";
fs.mkdirSync(OUT, { recursive: true });

const S = {
  console: '[data-testid="v13-discovery"]',
  goal: '[data-testid="v13-discovery-goal"]',
  submit: '[data-testid="v13-discover-submit"]',
  mode: 'select[aria-label]',
  cards: "article.v8-stay-card",
  ticks: '[data-testid="v13-pick-candidate"]',
  count: '[data-testid="v13-discovery-picked-count"]',
  target: '[data-testid="v13-discovery-batch-target"]',
  empty: '[data-testid="v13-discovery-batch-empty"]',
  note: '[data-testid="v13-discovery-batch-note"]',
  finish: '[data-testid="v13-discovery-finish-batch"]',
  fresh: '[data-testid="v13-discovery-new-batch"]',
  receipt: '[data-testid="v13-discovery-batch-receipt"]',
  rows: '[data-testid="v13-discovery-batch-row"]',
  refused: '[data-testid="v13-discovery-batch-refused"]',
  error: '[data-testid="v13-discovery-batch-error"]',
  technical: '[data-testid="v13-discovery-batch-technical"]',
};

/* Playwright's boundingBox() answers with {x, y, width, height}. Reading `.w`/`.h` off it yields
 * undefined, and `Math.abs(...) < Math.max(undefined, undefined)` is NaN, which is false -- so the
 * first run of this probe reported 完成 and 新建一批 as being in different bands when a direct DOM
 * measurement (`_measure_batch_bar.js`) had them at the same y, 44px tall, side by side at all four
 * widths. Normalise the field names here rather than let the instrument invent a defect. */
const sameBand = (a, b) =>
  Boolean(a && b && Math.abs(a.y + a.height / 2 - (b.y + b.height / 2)) < Math.max(a.height, b.height));

async function box(page, selector) {
  return page.locator(selector).first().boundingBox().catch(() => null);
}

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

  const http = [];
  const page = await ctx.newPage();
  page.on("response", async (res) => {
    if (!res.url().includes("/api/")) return;
    let bytes = null;
    try {
      bytes = (await res.text()).length;
    } catch {
      bytes = null;
    }
    http.push({ url: res.url().replace(BASE, ""), status: res.status(), bytes });
  });
  await page.goto(BASE + "/v8/discover", { waitUntil: "load" });
  await page.waitForSelector(S.goal, { timeout: 150_000 }).catch(() => {});

  const out = { locale, arrived: false };
  if (!(await page.locator(S.console).count()) || !(await page.locator(S.goal).count())) {
    out.body = (await page.evaluate(() => document.body.innerText)).replace(/\s+/g, " ").slice(0, 200);
    await ctx.close();
    return out;
  }
  out.arrived = true;

  const waitSettled = async () => {
    await page
      .waitForFunction(
        () =>
          Boolean(
            document.querySelector('[data-testid="v13-discovery-result"]') ||
              document.querySelector('[data-testid="v13-discovery-error"]'),
          ),
        { timeout: 150_000 },
      )
      .catch(() => {});
    await page.waitForTimeout(1200);
  };

  /* Reach a real result set the same way the before-probe did: the console's default mode is refused
     by the fully-grounded door on this store, so the batch is exercised on the synthetic-demo leg. */
  await page.locator(S.goal).fill(locale.startsWith("zh") ? "河边适合散步咖啡" : "riverside walk and coffee");
  await page.locator(S.mode).first().selectOption("captured_replay").catch(() => {});
  await page.locator(S.submit).click();
  await waitSettled();
  await page.locator(S.mode).first().selectOption("replay").catch(() => {});
  await page.locator(S.submit).click();
  await waitSettled();

  out.cards = await page.locator(S.cards).count();
  if (out.cards === 0) {
    out.status = "NO_CARDS";
    out.error_text = (await page.locator(S.error).count())
      ? await page.locator(S.error).innerText()
      : null;
    await ctx.close();
    return out;
  }

  /* ---- A0: nothing ticked yet ---- */
  out.a0 = {
    ticks: await page.locator(S.ticks).count(),
    unchecked: await page.locator('[data-testid="v13-pick-candidate"][aria-checked="false"]').count(),
    checked: await page.locator('[data-testid="v13-pick-candidate"][aria-checked="true"]').count(),
    cards_unpicked: await page.locator('article.v8-stay-card[data-picked="false"]').count(),
    cards_picked: await page.locator('article.v8-stay-card[data-picked="true"]').count(),
    count_text: (await page.locator(S.count).innerText()).replace(/\s+/g, " "),
    empty_state: await page.locator(S.empty).count(),
    empty_text: (await page.locator(S.empty).innerText()).replace(/\s+/g, " "),
    target_text: (await page.locator(S.target).innerText()).replace(/\s+/g, " "),
    finish_disabled: await page.locator(S.finish).isDisabled(),
    finish_label: (await page.locator(S.finish).innerText()).replace(/\s+/g, " "),
    fresh_label: (await page.locator(S.fresh).innerText()).replace(/\s+/g, " "),
    finish_and_fresh_same_band: sameBand(await box(page, S.finish), await box(page, S.fresh)),
    receipt: await page.locator(S.receipt).count(),
  };
  await page.screenshot({ path: `${OUT}/${locale}_A0.png`, fullPage: true });

  /* ---- A1: one tick ---- */
  await page.locator(S.ticks).first().click();
  await page.waitForTimeout(400);
  out.a1 = {
    checked: await page.locator('[data-testid="v13-pick-candidate"][aria-checked="true"]').count(),
    unchecked: await page.locator('[data-testid="v13-pick-candidate"][aria-checked="false"]').count(),
    cards_picked: await page.locator('article.v8-stay-card[data-picked="true"]').count(),
    count_text: (await page.locator(S.count).innerText()).replace(/\s+/g, " "),
    empty_state: await page.locator(S.empty).count(),
    note_text: (await page.locator(S.note).innerText()).replace(/\s+/g, " "),
    finish_disabled: await page.locator(S.finish).isDisabled(),
  };
  await page.screenshot({ path: `${OUT}/${locale}_A1_one_tick.png`, fullPage: true });

  /* ---- A2: 完成 writes, and the screen shows the second read ---- */
  await page.locator(S.finish).click();
  await page
    .waitForSelector(S.receipt, { timeout: 150_000 })
    .catch(() => {});
  await page.waitForTimeout(1200);
  out.a2 = {
    receipt: await page.locator(S.receipt).count(),
    rows: await page.locator(S.rows).count(),
    row_texts: (await page.locator(S.rows).allInnerTexts()).map((v) => v.replace(/\s+/g, " ")),
    target_text: (await page.locator(S.target).innerText()).replace(/\s+/g, " "),
    plan_text: (await page.locator(S.receipt).count())
      ? (await page.locator(`${S.receipt} .v8-batch-receipt-plan`).innerText()).replace(/\s+/g, " ")
      : null,
    refused: await page.locator(S.refused).count(),
    error_text: (await page.locator(S.error).count())
      ? (await page.locator(S.error).innerText()).replace(/\s+/g, " ")
      : null,
    compose_http: http.filter((h) => h.url.includes("authoritative-compose")),
    readback_http: http.filter((h) => /\/api\/v1\/plans\//.test(h.url)),
  };
  await page.screenshot({ path: `${OUT}/${locale}_A2_written.png`, fullPage: true });

  /* ---- A3: 新建一批 clears the batch and the claim with it ---- */
  await page.locator(S.fresh).click();
  await page.waitForTimeout(500);
  out.a3 = {
    count_text: (await page.locator(S.count).innerText()).replace(/\s+/g, " "),
    empty_state: await page.locator(S.empty).count(),
    checked: await page.locator('[data-testid="v13-pick-candidate"][aria-checked="true"]').count(),
    receipt: await page.locator(S.receipt).count(),
    finish_disabled: await page.locator(S.finish).isDisabled(),
  };
  await page.screenshot({ path: `${OUT}/${locale}_A3_new_batch.png`, fullPage: true });

  /* ---- A4: a batch the planner refuses must arrive as a refusal ---- */
  await page.locator(S.ticks).nth(0).click();
  await page.locator(S.ticks).nth(1).click();
  await page.waitForTimeout(300);
  out.a4_count_before = (await page.locator(S.count).innerText()).replace(/\s+/g, " ");
  await page.locator(S.finish).click();
  await page
    .waitForFunction(
      () =>
        Boolean(
          document.querySelector('[data-testid="v13-discovery-batch-error"]') ||
            document.querySelector('[data-testid="v13-discovery-batch-receipt"]'),
        ),
      { timeout: 150_000 },
    )
    .catch(() => {});
  await page.waitForTimeout(1000);
  out.a4 = {
    error_text: (await page.locator(S.error).count())
      ? (await page.locator(S.error).innerText()).replace(/\s+/g, " ")
      : null,
    technical_fold: await page.locator(S.technical).count(),
    receipt: await page.locator(S.receipt).count(),
    target_text: (await page.locator(S.target).innerText()).replace(/\s+/g, " "),
    refused_http: http.filter((h) => h.url.includes("authoritative-compose")).slice(-1)[0] ?? null,
  };
  await page.screenshot({ path: `${OUT}/${locale}_A4_refused.png`, fullPage: true });
  out.status = "BATCH_EXERCISED";
  await ctx.close();
  return { ...out, http: http.filter((h) => h.url.startsWith("/api")) };
}

(async () => {
  const scene = await (await fetch(BASE + "/api/v1/demo/scene")).json();
  const journeyId = String(scene.journey_id ?? "");
  if (journeyId.length < 8) throw new Error("stage named no journey: " + JSON.stringify(scene).slice(0, 200));
  const browser = await chromium.launch();
  const zh = await arm(browser, "zh-CN", journeyId);
  const en = await arm(browser, "en", journeyId);
  await browser.close();
  fs.writeFileSync(
    `${OUT}/probe_after_p1.json`,
    JSON.stringify({ base: BASE, journey_id: journeyId, zh, en }, null, 1),
    "utf-8",
  );
  for (const a of [zh, en]) {
    console.log(JSON.stringify({ locale: a.locale, status: a.status, cards: a.cards, a0: a.a0, a1: a.a1, a2: a.a2, a3: a.a3, a4: a.a4 }, null, 1));
  }
})();
