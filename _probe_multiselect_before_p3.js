/* ORD-0435 BEFORE-fix probe, r3 (lane be19052c) - my instrument, not the commander's r3.
 * (Name collision noted on purpose: the commander's gauge is `claim_coordinate_check_r7.py`; the
 * "r1/r2/r3" here are revisions of THIS probe and are referred to as probe-r1/probe-r2 in the record.)
 *
 * WHY probe-r1 IS WITHDRAWN
 * probe-r1 reported cards: 0 and a row of zeros in both arms. Those zeros are VACUOUS: its own
 * text_sample shows the screen it sat on was the onboarding wizard ("新建行程 三步完成…下一步"), not the
 * discovery console. The shell needs a journey before it renders any route panel
 * (V8Experience.tsx:775 reads `citynexus.v8.journey_id`); probe-r1 set only the locale.
 *
 * WHY probe-r2 IS WITHDRAWN
 * probe-r2 set the journey and reached /v8/discover, but counted immediately after `load`. Both arms
 * stayed on the shell's own loading screen - "正在准备城市周末行程…" / "Preparing a captured city
 * weekend…" - and the Chinese arm recorded 0 calls to /api/, because under `npm run dev` vite compiles
 * each module on first request. A screenshot of a spinner is not a screen read.
 *
 * WHAT THIS ONE DOES
 *   1. ask this backend which journey the demo stage holds (GET /api/v1/demo/scene) rather than
 *      hardcoding a uuid, so the reading names a journey the server actually has;
 *   2. warm the bundle on a throwaway hub visit, then navigate to /v8/discover by deep link and WAIT
 *      for the console (ORD-0404 keeps the asked-for screen across the demo gate);
 *   3. prove arrival before counting: data-testid="v13-discovery" plus the goal textarea. No console
 *      => the arm reports ARRIVED_NO_CONSOLE and contributes no zeros;
 *   4. record the HTTP receipt of the discovery call itself (status + byte count), so a card count of
 *      0 names the request that refused instead of pointing at an empty list.
 */
const { chromium } = require("D:/moodle/CityNexus/frontend/node_modules/playwright");
const fs = require("fs");

const BASE = process.argv[2] || "http://127.0.0.1:4817";
const OUT = process.argv[3] || "D:/moodle/_qoder_b_ord0435_20260929/_probe_before_r3";
fs.mkdirSync(OUT, { recursive: true });

const SELECTORS = {
  aria_pressed: "[aria-pressed]",
  aria_checked: "[aria-checked]",
  data_selected: "[data-selected]",
  checkbox: "input[type=checkbox]",
  role_checkbox: "[role=checkbox]",
  selected_class: ".selected",
  result_cards: "article.v8-stay-card",
  submit: '[data-testid="v13-discover-submit"]',
  goal: '[data-testid="v13-discovery-goal"]',
  results: '[data-testid="v13-discovery-result"]',
  console: '[data-testid="v13-discovery"]',
  error: '[data-testid="v13-discovery-error"]',
  mode: 'select[aria-label]',
};

function trackHttp(page, http) {
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
}

async function arm(browser, locale, journeyId) {
  const ctx = await browser.newContext({ locale, viewport: { width: 390, height: 844 } });
  const seed = { locale, journey: journeyId };
  await ctx.addInitScript((s) => {
    localStorage.clear();
    localStorage.setItem("citynexus.locale", s.locale);
    localStorage.setItem("citynexus.v8.journey_id", s.journey);
  }, seed);

  /* Warm pass: get vite to compile the shell and the discovery feature once, outside the measurement. */
  const warm = await ctx.newPage();
  await warm.goto(BASE + "/v8/hub", { waitUntil: "load" });
  await warm.waitForSelector('[data-testid="today-hero"]', { timeout: 180_000 }).catch(() => {});
  await warm.waitForSelector(SELECTORS.goal, { timeout: 60_000 }).catch(() => {});
  await warm.close();

  const http = [];
  const page = await ctx.newPage();
  trackHttp(page, http);
  await page.goto(BASE + "/v8/discover", { waitUntil: "load" });

  const out = {
    locale,
    journey_id_used: journeyId,
    path_after_load: new URL(page.url()).pathname,
    console_present: 0,
    goal_present: 0,
  };
  await page.waitForSelector(SELECTORS.console, { timeout: 150_000 }).catch(() => {});
  await page.waitForSelector(SELECTORS.goal, { timeout: 150_000 }).catch(() => {});
  await page.waitForTimeout(1000);
  out.console_present = await page.locator(SELECTORS.console).count();
  out.goal_present = await page.locator(SELECTORS.goal).count();
  out.arrived = out.console_present === 1 && out.goal_present === 1;
  out.body_if_not_arrived = out.arrived
    ? null
    : (await page.evaluate(() => document.body.innerText)).replace(/\s+/g, " ").slice(0, 200);
  if (!out.arrived) {
    await page.screenshot({ path: `${OUT}/${locale}_not_arrived.png` });
    await ctx.close();
    return { ...out, http, status: "ARRIVED_NO_CONSOLE" };
  }

  out.default_goal_text = await page.locator(SELECTORS.goal).inputValue();
  out.mode_options = await page.locator(SELECTORS.mode).first().locator("option").allInnerTexts();
  out.submit_before_fill = await page.locator(SELECTORS.submit).isDisabled().catch(() => null);
  await page.locator(SELECTORS.goal).fill(
    locale.startsWith("zh") ? "河边适合散步咖啡" : "riverside walk and coffee",
  );
  const submit = page.locator(SELECTORS.submit);
  out.submit_after_fill = await submit.isDisabled().catch(() => null);

  /* Leg 1 -- the console's own default (captured_replay) is recorded first, honestly, including the
     refusal it produces on this copy of the store: the fully-grounded door answers 422 with
     V13_FULL_GROUNDING_MISSING_MOBILITY_PAIR. Keeping that reading here is what stops leg 2 from
     looking like it was cherry-picked to make the cards appear. */
  await page.locator(SELECTORS.mode).first().selectOption("captured_replay").catch(() => {});
  await submit.click();
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
  out.leg1_error_present = await page.locator(SELECTORS.error).count();
  out.leg1_error_text = out.leg1_error_present
    ? (await page.locator(SELECTORS.error).innerText()).replace(/\s+/g, " ").slice(0, 240)
    : null;
  out.leg1_cards = await page.locator(SELECTORS.result_cards).count();
  out.leg1_http = http.filter((h) => h.url.includes("intelligence"));

  /* Leg 2 -- the same screen, synthetic-demo mode, which this backend answers 201 with a real
     candidate set (measured outside the browser first: `replay` -> 201, 129,440 B, 3 candidates,
     provider SEALED_REPLAY_SEMANTIC_FALLBACK). Only here do the multiselect zeros mean anything,
     because only here are there cards on screen to lack a checkbox. */
  await page.locator(SELECTORS.mode).first().selectOption("replay").catch(() => {});
  await submit.click();
  /* Wait for the call to answer rather than nap: the sealed-replay leg is fast, a live provider leg
     is not, and a screenshot taken mid-request looks exactly like an empty result set. */
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
  await page.waitForTimeout(1500);
  /* Wait for the call to answer rather than nap: the sealed-replay leg is fast, a live provider leg
     is not, and a screenshot taken mid-request looks exactly like an empty result set. */
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
  await page.waitForTimeout(1500);

  out.results_present = await page.locator(SELECTORS.results).count();
  out.result_cards = await page.locator(SELECTORS.result_cards).count();
  out.error_present = await page.locator(SELECTORS.error).count();
  out.error_text = out.error_present
    ? (await page.locator(SELECTORS.error).innerText()).replace(/\s+/g, " ").slice(0, 240)
    : null;
  for (const key of ["aria_pressed", "aria_checked", "data_selected", "checkbox", "role_checkbox", "selected_class"]) {
    out[key] = await page.locator(SELECTORS[key]).count();
  }
  /* A card is only a card if it says something: read the rendered names so the record carries proof
     the console is full, not only the number I asked for. */
  out.card_names = await page.locator("article.v8-stay-card h3").allInnerTexts().then((v) => v.slice(0, 6));
  const body = await page.evaluate(() => document.body.innerText);
  out.count_pattern_hits = (
    body.match(/(已选择|选中\s*\d|选择\s*\d|\b\d+\s*(items?|selected)\b)/gi) || []
  ).slice(0, 5);
  out.done_button = (body.match(/(完成|\bDone\b)/g) || []).length;
  out.create_button = (body.match(/(新建|创建|\bNew\b|\bCreate\b)/g) || []).length;
  out.add_button = (body.match(/(加入|添加|\bAdd\b)/g) || []).length;
  out.text_sample = body.replace(/\s+/g, " ").slice(0, 600);
  await page.screenshot({ path: `${OUT}/${locale}_cards_${out.result_cards}.png`, fullPage: true });
  await ctx.close();
  return { ...out, http, status: out.result_cards > 0 ? "CARDS_ON_SCREEN" : "CONSOLE_WITHOUT_CARDS" };
}

(async () => {
  const sceneRes = await fetch(BASE + "/api/v1/demo/scene");
  const scene = await sceneRes.json();
  const journeyId = String(scene.journey_id ?? "");
  if (journeyId.length < 8) throw new Error("stage named no journey: " + JSON.stringify(scene).slice(0, 200));

  const browser = await chromium.launch();
  const zh = await arm(browser, "zh-CN", journeyId);
  const en = await arm(browser, "en", journeyId);
  await browser.close();

  const rep = {
    base: BASE,
    journey_id: journeyId,
    note: "BEFORE fix probe-r3: arrival proven before counting; multiselect and selection-count must be absent",
    probe_r1_withdrawn: "counted on the onboarding wizard (no journey in localStorage) - every zero vacuous",
    probe_r2_withdrawn: "counted on the shell's loading screen; zh arm made 0 calls to /api/ (vite compiles on first request)",
    zh,
    en,
  };
  fs.writeFileSync(`${OUT}/probe_before_r3.json`, JSON.stringify(rep, null, 1), "utf-8");
  for (const a of [zh, en]) {
    console.log(
      JSON.stringify(
        {
          locale: a.locale,
          status: a.status,
          path: a.path_after_load,
          cards: a.result_cards,
          card_names: a.card_names,
          aria_pressed: a.aria_pressed,
          aria_checked: a.aria_checked,
          data_selected: a.data_selected,
          checkbox: a.checkbox,
          selected_class: a.selected_class,
          count_hits: a.count_pattern_hits,
          done: a.done_button,
          create: a.create_button,
          add: a.add_button,
          goal_default: a.default_goal_text,
          mode_options: a.mode_options,
          leg1_cards: a.leg1_cards,
          leg1_error: a.leg1_error_text,
          leg1_http: a.leg1_http,
          submit_before: a.submit_before_fill,
          submit_after: a.submit_after_fill,
          error: a.error_text,
          api_calls: a.http.filter((h) => h.url.startsWith("/api")).length,
          discovery_http: a.http.filter((h) => h.url.includes("intelligence")),
        },
        null,
        1,
      ),
    );
  }
})();
