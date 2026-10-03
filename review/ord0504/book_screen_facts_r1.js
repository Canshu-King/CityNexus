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

/* The ruler keeps its OWN exponent table. `frontend/src/lib/money.ts:1` says JPY/KRW/VND/IDR carry no
 * minor fraction; if the face (or my own spend helper) divides by 100 anyway, the number on the screen is
 * 100x off, and this table is what notices. */
const ZERO_DECIMAL = new Set(["JPY", "KRW", "VND", "IDR"]);
const exponent = (code) => (ZERO_DECIMAL.has(String(code ?? "CNY").toUpperCase()) ? 0 : 2);
const money = (minor, code = "CNY") => {
  const digits = exponent(code);
  return (minor / 10 ** digits).toLocaleString("en-US", {
    minimumFractionDigits: digits, maximumFractionDigits: digits,
  });
};

/* What the locale's own currency formatter would print for that amount, computed here rather than read
 * from the product helper, so a mistake in the product's exponent handling shows up as a red arm. */
const markedMoney = (minor, code, locale = "zh-CN") => {
  const digits = exponent(code);
  return new Intl.NumberFormat(locale, {
    style: "currency", currency: String(code ?? "CNY"), maximumFractionDigits: digits,
  }).format(minor / 10 ** digits);
};

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
    const wantMinor = priced.map((r) => money(r.price.amount_minor, r.price.currency));
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

  /* 2b. the money on a ticket must be traceable to the currency the wallet answered.  Measured, not argued:
   *     for every priced row the card has to carry either the ISO code or the exact string this locale's own
   *     formatter produces for that amount -- and no two different ISO codes may collapse into one string.
   *     A first version of this arm demanded "code on the card, no symbol" and reported the USD ticket as
   *     `¥`; that reading was wrong and is retracted here: under zh-CN this Chrome answers CNY=`¥230.00`,
   *     JPY=`JP¥4,800`, USD=`US$99.00`, so the marks differ. What stays required is the traceability. */
  {
    const opened = await openBookings(DESKTOP, "route");
    const perCard = opened.reservations
      .map((card, index) => {
        const row = reservations[index];
        if (!row || typeof row.price.amount_minor !== "number") return null;
        const code = String(row.price.currency);
        const marked = markedMoney(row.price.amount_minor, code);
        return { server_currency: code, formatter_says: marked,
                 card_carries_the_code: card.includes(code),
                 card_carries_the_locale_mark: card.includes(marked),
                 card: card.slice(0, 150) };
      })
      .filter(Boolean);
    const byMark = {};
    for (const entry of perCard) {
      const key = entry.card_carries_the_code ? entry.server_currency : entry.formatter_says;
      (byMark[key] = byMark[key] || new Set()).add(entry.server_currency);
    }
    const collapsed = Object.keys(byMark)
      .filter((mark) => byMark[mark].size > 1)
      .map((mark) => ({ mark, server_currencies: Array.from(byMark[mark]).sort() }));
    record("book_screen/every_ticket_price_is_traceable_to_the_currency_answered",
      perCard.every((entry) => entry.card_carries_the_code || entry.card_carries_the_locale_mark)
      && collapsed.length === 0,
      { cards: perCard, collapsed_marks: collapsed,
        note: "a price the locale cannot trace back to one ISO code is not an answer" });
    await opened.context.close();
  }

  /* 2c. zero-decimal money measured on the face: the store holds 4800 minor JPY, which is 4,800 yen, not
   *     48.00.  A face that divides every currency by 100 (the way `frontend/src/features/trip/spendFacts.ts`
   *     does in `moneyText`) lands on the wrong number here, so this row exists to be caught. */
  {
    const opened = await openBookings(DESKTOP, "route");
    const zeroRows = reservations.filter(
      (r) => typeof r.price.amount_minor === "number" && exponent(r.price.currency) === 0);
    const readings = zeroRows.map((row) => {
      const card = opened.reservations[reservations.indexOf(row)] || "";
      const correct = money(row.price.amount_minor, row.price.currency);
      const hundredOff = money(row.price.amount_minor, "CNY");
      return { server_currency: row.price.currency, minor: row.price.amount_minor,
               wants_on_card: correct, wrong_if_always_dividing_by_100: hundredOff,
               card: card.slice(0, 150), shows_correct: card.includes(correct),
               shows_the_hundred_off_number: card.includes(hundredOff) };
    });
    record("book_screen/a_zero_decimal_currency_is_not_divided_by_100",
      zeroRows.length > 0
      && readings.every((entry) => entry.shows_correct && !entry.shows_the_hundred_off_number),
      { zero_decimal_rows: readings.length, readings,
        note: "empty readings would mean the store has no zero-decimal money, which is a seed failure" });
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
    const knownNumbers = known.map((c) => money(c.monetary_value.amount_minor, c.monetary_value.currency));
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

  /* 4b. the same rule on the ticket cards.  Control R1 of `book_screen_controls_r1.py` put a `¥0.00` on a
   *     ticket and this ruler stayed green, because arm 4 only reads the commitment cards -- the blind spot
   *     was mine, so the arm that closes it ships with the reading.  The word is the product's own:
   *     `bookings.priceUnknown` is 价格未知 at `frontend/src/i18n/LocaleContext.tsx:1431`. */
  {
    const opened = await openBookings(DESKTOP, "route");
    const unpriced = reservations.filter((r) => r.price.amount_minor == null);
    const priced = reservations.filter((r) => typeof r.price.amount_minor === "number");
    const zeroCards = opened.reservations
      .filter((card) => /(?:¥|￥|US\$|\$|CNY|JPY|USD)\s*0(?:\.00)?(?![\d])/.test(card));
    const wordCards = opened.reservations.filter((card) => card.includes("价格未知"));
    const numberCards = opened.reservations.filter((card) => /(?:¥|￥|US\$|\$|CNY|JPY|USD)\s*[1-9]/.test(card));
    record("book_screen/an_unlearned_ticket_price_stays_a_word_not_a_zero",
      opened.reservations.length === reservations.length
      && zeroCards.length === 0 && wordCards.length === unpriced.length
      && numberCards.length === priced.length,
      { ticket_rows: reservations.length, unpriced_rows: unpriced.length,
        priced_rows: priced.length, cards_showing_a_zero: zeroCards,
        cards_with_the_word: wordCards.length, cards_with_a_number: numberCards.length,
        expected_word: "价格未知" });
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

  /* 6a. the kind word on each ticket must come from the face's own vocabulary, recomputed here from the
   *     door's token.  A table-miss kind is answered with a word (`其他预订`), never with the door's own
   *     spelling: `CRUISE_SHIP`/`train` on a Chinese screen tells the traveller nothing. */
  {
    const opened = await openBookings(DESKTOP, "route");
    const TYPE_WORDS = { FLIGHT: "航班", RAIL: "火车", TRAIN: "火车", COACH: "大巴", FERRY: "轮渡",
      HOTEL: "住宿", TICKET: "门票", RESERVATION: "预订" };
    const UNKNOWN_WORD = "其他预订";
    const perCard = opened.reservations.map((card, index) => {
      const row = reservations[index];
      const drawn = card.split("·")[0].trim();
      const wants = TYPE_WORDS[String(row && row.reservation_type ? row.reservation_type : "").toUpperCase()]
        || UNKNOWN_WORD;
      return { door_token: row ? row.reservation_type : null, word_on_card: drawn, word_expected: wants,
               card: card.slice(0, 120) };
    });
    record("book_screen/the_ticket_kind_is_drawn_from_the_word_table",
      perCard.every((entry) => entry.word_on_card === entry.word_expected),
      { cards: perCard, vocabulary_source: "review/ord0504/book_screen_facts_r1.js:308" });
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
