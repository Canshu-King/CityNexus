/*
 * ORD-0504 book-screen hand -- the same 回答事实 ruler the 花费 tab already answers to, pointed at
 * the 预订 tab (the ledger and the tickets).
 *
 * One rule, unchanged from `spend_arms_r1.js`: a card may only show what the two doors the screen is
 * allowed to read actually answered. Every expectation here is summed by this file from freshly
 * fetched `GET /journeys/{id}/experience` and `GET /journeys/{id}/wallet` answers, and every
 * assertion reads rendered text a traveller can see -- no `data-*` value is evidence, because an
 * attribute can carry a fact the screen never showed anybody.
 *
 * The store is this lane's own (`run/ord0465_lane.db`), seeded by `book_seed_r1.py`, which deliberately
 * writes one reservation the server calls PENDING, one with no price, and one commitment whose price
 * the server never learned. Those three shapes are what the 已确认 word and the 价格未知 word are for.
 */
const fs = require("fs");
const path = require("path");
const http = require("http");
const LANE = "D:/moodle/_qoder_r_ord0465_20260929";
const REPO = LANE + "/wt";
const { chromium } = require(path.join(REPO, "frontend/node_modules/playwright"));

const FRONT = "http://127.0.0.1:4931";
const API_PORT = 8731;
// one file per pass: two runs must not overwrite each other's evidence
const OUT = path.resolve(REPO, process.env.BOOK_OUT || "review/ord0504/book_screen_facts_r1.json");
const DESKTOP = { width: 1280, height: 900 };
const MOBILE = { width: 390, height: 844 };
const seed = JSON.parse(fs.readFileSync(path.join(LANE, "run/book_seed_report.json"), "utf-8"));
const JOURNEY = seed.journey_id;

function fetchDoor(door) {
  return new Promise((resolve, reject) => {
    http.get({ host: "127.0.0.1", port: API_PORT, path: `/api/v1/journeys/${JOURNEY}/${door}` },
      (answer) => {
        const chunks = [];
        answer.on("data", (chunk) => chunks.push(chunk));
        answer.on("end", () => {
          try { resolve(JSON.parse(Buffer.concat(chunks).toString("utf-8"))); }
          catch (error) { reject(error); }
        });
      }).on("error", reject);
  });
}

async function answers() {
  return { experience: await fetchDoor("experience"), wallet: await fetchDoor("wallet") };
}

const money = (minor) => (minor / 100).toLocaleString("en-US", {
  minimumFractionDigits: 2, maximumFractionDigits: 2,
});

const CONFIRMED_STATES = new Set(["CONFIRMED", "FULFILLED", "COMPLETED"]);

/*
 * Two ways onto the same face, because both are real: the shell route `/v8/bookings` is what a
 * desktop traveller types or lands on, and Trips -> 预订 is what the phone draws. The panel is
 * mounted for both, so every locator here is pinned to the visible instance -- a hidden duplicate
 * would otherwise answer for a card nobody can see.
 */
async function openBookings(viewport, via) {
  const context = await browser.newContext({
    viewport, locale: "zh-CN", hasTouch: viewport.width < 500, isMobile: viewport.width < 500,
    deviceScaleFactor: viewport.width < 500 ? 3 : 1,
  });
  const page = await context.newPage();
  await page.addInitScript(([id]) => window.localStorage.setItem("citynexus.v8.journey_id", id), [JOURNEY]);
  const requests = [];
  page.on("request", (request) => requests.push({ method: request.method(), url: request.url() }));
  if (via === "route") {
    await page.goto(FRONT + "/v8/bookings", { waitUntil: "domcontentloaded" });
  } else {
    await page.goto(FRONT + "/v8/trips", { waitUntil: "domcontentloaded" });
    await page.waitForSelector('[data-testid="trips-tabs"]', { timeout: 30000 });
    await page.waitForTimeout(1500);
    await page.click('[data-testid="trips-tab-bookings"]');
  }
  await page.waitForSelector('[data-testid="v8-bookings"]:visible', { timeout: 25000 });
  await page.waitForTimeout(900);
  const scope = page.locator('[data-testid="v8-bookings"]:visible').first();
  const text = async (locator) => {
    const count = await scope.locator(locator).count();
    const out = [];
    for (let i = 0; i < count; i += 1) out.push((await scope.locator(locator).nth(i).innerText()).replace(/\s+/g, " ").trim());
    return out;
  };
  const card = (locator) => text(locator);
  return {
    context, page, requests,
    reservations: await card('[data-testid="wallet-reservation"]'),
    commitments: await card('[data-testid="wallet-commitment"]'),
    stayTotal: await text('[data-testid="bookings-stay-total"]'),
    noStay: await text('[data-testid="bookings-no-stay"]'),
    simulated: await text('[data-testid="wallet-commitment-simulated"]'),
    refs: await text('[data-testid="wallet-reservation-ref"]'),
    face: (await scope.innerText().catch(() => "")).replace(/\s+/g, " "),
  };
}

const results = [];
let browser = null;
function record(arm, pass, detail) {
  results.push({ arm, pass, detail });
  console.log(`${pass ? "PASS" : "FAIL"}  ${arm}${pass ? "" : "  " + JSON.stringify(detail).slice(0, 700)}`);
}

(async () => {
  browser = await chromium.launch({ channel: "chrome", headless: true });
  const a = await answers();
  const reservations = a.wallet.reservations || [];
  const commitments = a.wallet.commitments || [];
  const priced = reservations.filter((r) => typeof r.price.amount_minor === "number");
  const unpriced = reservations.filter((r) => r.price.amount_minor === null);

  /* 1. no option was answered, so the stay card must take the "no stay" branch and show no total */
  {
    const opened = await openBookings(DESKTOP, "route");
    record("book_screen/the_stay_card_answers_from_the_options_it_was_given",
      (a.experience.options || []).length === 0 && opened.noStay.length === 1 && opened.stayTotal.length === 0,
      { options_answered: (a.experience.options || []).length, no_stay_cards: opened.noStay.length,
        stay_totals: opened.stayTotal, active_plan: !!a.experience.active_plan });
    await opened.context.close();
  }

  /* 2a. the number on each priced ticket is the number the wallet answered for it */
  {
    const opened = await openBookings(DESKTOP, "route");
    const wantMinor = priced.map((r) => money(r.price.amount_minor));
    const cardsWithNumber = opened.reservations.filter((card) => wantMinor.some((w) => card.includes(w)));
    const cardsWithUnknown = opened.reservations.filter((card) => card.includes("价格未知"));
    record("book_screen/ticket_numbers_equal_the_wallets_own_amounts",
      opened.reservations.length === reservations.length
      && cardsWithNumber.length === wantMinor.length && cardsWithUnknown.length === unpriced.length,
      { want_minor_as_shown: wantMinor, want_unknown_count: unpriced.length,
        cards: opened.reservations.length, cards_with_number: cardsWithNumber.length,
        cards_with_unknown_word: cardsWithUnknown.length, cards: opened.reservations });
    await opened.context.close();
  }

  /* 2b. a number without an unambiguous currency is not an answer: `¥` stands for CNY and JPY both,
   *     so a traveller reading `¥99.00` on a USD ticket cannot tell which money it is. The doors carry
   *     an ISO code; this arm asks whether the face kept it. */
  {
    const opened = await openBookings(DESKTOP, "route");
    const rows = reservations.filter((r) => typeof r.price.amount_minor === "number");
    const perCard = opened.reservations.map((card, index) => {
      const row = reservations[index];
      if (!row || typeof row.price.amount_minor !== "number") return null;
      return { server_currency: row.price.currency,
               iso_on_card: card.includes(row.price.currency),
               symbol_on_card: /¥|US\$|￥|\$(?=\s?\d)/.test(card),
               card: card.slice(0, 150) };
    }).filter(Boolean);
    record("book_screen/a_ticket_price_names_its_currency_in_the_code_the_server_sent",
      perCard.every((entry) => entry.iso_on_card && !entry.symbol_on_card),
      { cards: perCard, note: "the wallet answers an ISO code; a symbol on the face loses which money" });
    await opened.context.close();
  }

  /* 3. the 已确认 word may only stand on a card the server itself calls confirmed */
  {
    const opened = await openBookings(DESKTOP, "route");
    const liarCards = opened.reservations
      .map((card, index) => ({ card, row: reservations[index] }))
      .filter(({ card, row }) => card.includes("已确认") && !CONFIRMED_STATES.has(row.status))
      .map(({ card, row }) => ({ server_status: row.status, shown: card.slice(0, 160) }));
    record("book_screen/confirmed_words_only_where_the_server_said_confirmed",
      liarCards.length === 0,
      { server_statuses: reservations.map((r) => r.status), cards_claiming_confirmed: liarCards });
    await opened.context.close();
  }

  /* 4. a commitment whose price the server never learned must not borrow the 0 the column defaults to.
   *     Measured shape: `commitments.monetary_value_minor` cannot be NULL, so an unlearned price is
   *     stored as 0 with `monetary_value_status = UNKNOWN` -- the face has to read the word, not the digit. */
  {
    const opened = await openBookings(DESKTOP, "route");
    const unknowns = commitments.filter((c) => c.monetary_value_status !== "KNOWN");
    const known = commitments.filter((c) => c.monetary_value_status === "KNOWN");
    const knownNumbers = known.map((c) => money(c.monetary_value.amount_minor));
    const cardsShowingZero = opened.commitments.filter((card) => /(?:¥|￥|US\$|\$|CNY|JPY|USD)\s*0\.00(?!\d)/.test(card));
    const cardsWithUnknownWord = opened.commitments.filter((card) => card.includes("价格未知"));
    const cardsWithKnownNumber = opened.commitments.filter((card) => knownNumbers.some((n) => card.includes(n)));
    record("book_screen/an_unlearned_price_stays_a_word_not_a_zero",
      opened.commitments.length === commitments.length
      && cardsWithUnknownWord.length === unknowns.length
      && cardsShowingZero.length === 0 && cardsWithKnownNumber.length === known.length,
      { commitment_rows: commitments.map((c) => ({ status: c.monetary_value_status,
          minor: c.monetary_value.amount_minor })),
        cards: opened.commitments.length, cards_with_unknown_word: cardsWithUnknownWord.length,
        cards_showing_a_zero_amount: cardsShowingZero.length, cards_with_known_number: cardsWithKnownNumber.length });
    await opened.context.close();
  }

  /* 5. 模拟承诺 follows the store's own external_ref, in both directions */
  {
    const opened = await openBookings(DESKTOP, "route");
    const mockRows = commitments.filter((c) => String(c.external_ref || "").startsWith("mock-"));
    const plainRows = commitments.filter((c) => !String(c.external_ref || "").startsWith("mock-"));
    record("book_screen/the_simulated_word_only_covers_a_mock_reference",
      opened.simulated.length === mockRows.length
      && opened.commitments.filter((card) => card.includes("模拟承诺")).length === mockRows.length
      && opened.commitments.filter((card) => card.includes("模拟承诺") && card.includes(plainRows
        .map((p) => p.external_ref)[0])).length === 0,
      { mock_refs: mockRows.map((c) => c.external_ref), plain_refs: plainRows.map((c) => c.external_ref),
        simulated_badges: opened.simulated.length });
    await opened.context.close();
  }

  /* 6. the Chinese face carries no machine word a traveller cannot read */
  {
    const opened = await openBookings(MOBILE, "route");
    const visible = opened.face;
    const tokens = ["CONFIRMED", "PENDING", "FULFILLED", "C3_Guaranteed", "C2_Reserved", "UNKNOWN",
      "KNOWN", "mock-booking", "SCHEDULED", "BOOKING", "train", "TRAIN", "flight", "FLIGHT",
      "ACTIVE", "visit"];
    const found = tokens.filter((token) => visible.includes(token));
    record("book_screen/no_machine_token_on_the_chinese_face", found.length === 0,
      { found, view: "mobile 390x844", sample: visible.slice(0, 240) });
    await opened.context.close();
  }

  /* 6b. the phone's own entry point exists and is labelled, even though the panel above is reached
   *     through the route in this run -- a missing tab would make the whole face unreachable by thumb. */
  {
    const context = await browser.newContext({ viewport: MOBILE, locale: "zh-CN", hasTouch: true,
      isMobile: true, deviceScaleFactor: 3 });
    const page = await context.newPage();
    await page.addInitScript(([id]) => window.localStorage.setItem("citynexus.v8.journey_id", id), [JOURNEY]);
    await page.goto(FRONT + "/v8/trips", { waitUntil: "domcontentloaded" });
    await page.waitForSelector('[data-testid="trips-tabs"]', { timeout: 30000 });
    const labels = await page.$$eval('[data-testid^="trips-tab-"]',
      (els) => els.map((el) => `${el.getAttribute("data-testid")}:${el.innerText.trim()}`));
    record("book_screen/the_phone_tab_strip_offers_the_bookings_face", labels.includes("trips-tab-bookings:预订"),
      { tabs: labels });
    await context.close();
  }

  /* 7. the face asks nothing new: only GETs, and the doors this screen already reads */
  {
    const opened = await openBookings(DESKTOP, "route");
    const prefix = `/api/v1/journeys/${JOURNEY}/`;
    const api = opened.requests.filter((r) => r.url.includes(prefix));
    const doors = [...new Set(api.map((r) => r.url.split(prefix)[1].split("?")[0]))].sort();
    const nonGet = opened.requests.filter((r) => r.method !== "GET").map((r) => `${r.method} ${r.url}`);
    record("book_screen/opens_with_gets_and_no_new_door",
      nonGet.length === 0 && doors.includes("wallet") && doors.includes("experience"),
      { non_get_requests: nonGet, journey_doors_read: doors, api_calls: api.length });
    await opened.context.close();
  }

  const failed = results.filter((r) => !r.pass);
  fs.writeFileSync(OUT, JSON.stringify({
    generated_at: new Date().toISOString(), journey: JOURNEY, store: seed.lane_db,
    server_rows: { reservations: reservations.map((r) => ({ id: r.id, status: r.status,
        price: r.price, commitment_id: r.commitment_id ?? null })),
      commitments: commitments.map((c) => ({ id: c.id, status: c.monetary_value_status,
        value: c.monetary_value, external_ref: c.external_ref })) },
    results,
  }, null, 2), { encoding: "utf-8" });
  console.log(`\nARMS=${results.length} PASSED=${results.length - failed.length} FAILED=${failed.length}`);
  await browser.close();
  process.exit(failed.length ? 1 : 0);
})().catch(async (error) => {
  console.error("DRIVER_ERROR", error && error.message);
  fs.writeFileSync(OUT, JSON.stringify({ driver_error: String(error && error.message), results }, null, 2),
    { encoding: "utf-8" });
  if (browser) await browser.close();
  process.exit(2);
});
