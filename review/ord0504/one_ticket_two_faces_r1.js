/*
 * ORD-0504 self-check, one ticket read twice.
 *
 * The 预订 face prints money with `formatMinorMoney`, which asks `frontend/src/lib/money.ts:1` how many
 * minor units a currency has. The 花费 face prints money with `moneyText` in
 * `frontend/src/features/trip/spendFacts.ts:312`, which divides by 100 and never asks -- and that second
 * helper is the one I shipped in the r5 hand. One JPY row in one store settles it: 4800 minor is 4,800 yen.
 *
 * Two arms, both from the doors, both reading rendered text:
 *   spend/a_zero_decimal_amount_keeps_its_own_exponent_on_the_face
 *   spend/the_two_faces_of_one_journey_agree_on_one_ticket
 *
 * The earlier version of this file graded the 花费 tab too early: with the shell's doors still landing it
 * drew 0 lines, which read as "nothing to compare" rather than as a measurement. Everything below now waits
 * for the line list to appear and prints what it counted, so a short wait shows up as a named failure
 * instead of a silent empty denominator.
 */
const fs = require("fs");
const path = require("path");
const http = require("http");
const LANE = "D:/moodle/_qoder_r_ord0465_20260929";
const REPO = LANE + "/wt";
const { chromium } = require(path.join(REPO, "frontend/node_modules/playwright"));

const FRONT = "http://127.0.0.1:4931";
const API_PORT = 8731;
const OUT = path.resolve(REPO, process.env.SPEND_OUT || "review/ord0504/one_ticket_two_faces_r1.json");
const DESKTOP = { width: 1280, height: 900 };

const ZERO_DECIMAL = new Set(["JPY", "KRW", "VND", "IDR"]);
const exponent = (code) => (ZERO_DECIMAL.has(String(code ?? "CNY").toUpperCase()) ? 0 : 2);
const digits = (minor, code) => {
  const e = exponent(code);
  return (minor / 10 ** e).toLocaleString("en-US", { minimumFractionDigits: e, maximumFractionDigits: e });
};

function fetchWallet(journey) {
  return new Promise((resolve, reject) => {
    http.get({ host: "127.0.0.1", port: API_PORT, path: `/api/v1/journeys/${journey}/wallet` }, (answer) => {
      const chunks = [];
      answer.on("data", (chunk) => chunks.push(chunk));
      answer.on("end", () => {
        try { resolve(JSON.parse(Buffer.concat(chunks).toString("utf-8"))); }
        catch (error) { reject(error); }
      });
    }).on("error", reject);
  });
}

const cells = (page, selector) => page.$$eval(selector,
  (els) => els.map((e) => e.innerText.replace(/\s+/g, " ").trim()));

async function openShell(browser, tab) {
  const context = await browser.newContext({ viewport: DESKTOP, locale: "zh-CN" });
  await context.addInitScript(([id]) => window.localStorage.setItem("citynexus.v8.journey_id", id), [JOURNEY]);
  const page = await context.newPage();
  if (tab === "route-bookings") {
    // the same page the traveller reaches by typing the ticket screen's own address; the tab click inside
    // the trips shell left this section unmounted in an earlier run of this file, so both ways are kept
    await page.goto(FRONT + "/v8/bookings", { waitUntil: "domcontentloaded" });
  } else {
    await page.goto(FRONT + "/v8/trips", { waitUntil: "domcontentloaded" });
    await page.waitForSelector('[data-testid="trips-tabs"]', { timeout: 30000 });
    await page.click(`[data-testid="trips-tab-${tab}"]`);
  }
  return { context, page };
}

let JOURNEY;
const results = [];

(async () => {
  const seed = JSON.parse(fs.readFileSync(path.join(LANE, "run/book_seed_report.json"), "utf-8"));
  JOURNEY = seed.journey_id;
  const wallet = await fetchWallet(JOURNEY);
  const reservations = wallet.reservations || [];
  const zeroRows = reservations.filter(
    (r) => typeof r.price.amount_minor === "number" && exponent(r.price.currency) === 0);

  const browser = await chromium.launch({ channel: "chrome", headless: true });
  const record = (arm, pass, detail) => {
    results.push({ arm, pass, detail });
    console.log(`${pass ? "PASS" : "FAIL"}  ${arm}${pass ? "" : "  " + JSON.stringify(detail).slice(0, 900)}`);
  };

  /* the 花费 face: wait until the line list exists, then read the money column verbatim */
  const spend = await openShell(browser, "spend");
  await spend.page.waitForSelector('[data-testid="trips-spend"]', { timeout: 20000 });
  let lines = [];
  try {
    await spend.page.waitForFunction(
      () => document.querySelectorAll('[data-testid="spend-line"]').length > 0, { timeout: 25000 });
  } catch {
    lines = [];
  }
  lines = await cells(spend.page, '[data-testid="spend-line"]');
  const amounts = await cells(spend.page, '[data-testid="spend-line-amount"]');
  const totals = await cells(spend.page, '[data-testid="spend-group-total"]');
  const lede = (await spend.page.innerText('[data-testid="spend-lede"]').catch(() => "")).replace(/\s+/g, " ");
  await spend.context.close();

  /* the 预订 face, same store, same ticket: the ticket cards are drawn in the door's own order */
  const book = await openShell(browser, "route-bookings");
  await book.page.waitForSelector('[data-testid="v8-bookings"]:visible', { timeout: 30000 });
  // same lesson as the 花费 side: the ticket cards only exist once /wallet has landed, and reading the
  // section before that returns an empty list that looks like "the screen draws nothing"
  await book.page.waitForSelector('[data-testid="wallet-reservation"]', { timeout: 25000 });
  const scope = book.page.locator('[data-testid="v8-bookings"]:visible').first();
  const cards = await scope.locator('[data-testid="wallet-reservation"]').allInnerTexts();
  await book.context.close();

  const which = (text, right, wrong) => (text.includes(right) ? right
    : text.includes(wrong) ? wrong : "@@unread@@");
  const readings = zeroRows.map((row) => {
    const index = reservations.indexOf(row);
    const card = cards[index] || "";
    const right = digits(row.price.amount_minor, row.price.currency);
    const wrong = digits(row.price.amount_minor, "CNY");
    const spendLine = lines.find((t) => t.includes(String(row.price.currency) + " " + wrong))
      || lines.find((t) => t.includes(String(row.price.currency))) || "";
    const spendTotal = totals.find((t) => t.includes(String(row.price.currency))) || "";
    return {
      reservation_id: row.id, server_currency: row.price.currency, minor: row.price.amount_minor,
      correct_digits: right, digits_if_always_dividing_by_100: wrong,
      bookings_face_card: card.replace(/\s+/g, " ").slice(0, 200),
      spend_face_line: spendLine.slice(0, 200), spend_face_group_total: spendTotal.slice(0, 200),
      bookings_shown: which(card, right, wrong),
      spend_line_shown: which(spendLine, right, wrong),
      spend_group_shown: which(spendTotal, right, wrong),
    };
  });

  record("spend/a_zero_decimal_amount_keeps_its_own_exponent_on_the_face",
    readings.length > 0 && readings.every((r) => r.spend_line_shown === r.correct_digits
      && r.spend_group_shown === r.correct_digits),
    { zero_decimal_rows: readings.length, spend_line_count: lines.length, readings,
      note: "moneyText divides every currency by 100; lib/money.ts says JPY has no minor fraction" });

  record("spend/the_two_faces_of_one_journey_agree_on_one_ticket",
    readings.length > 0 && readings.every((r) => r.bookings_shown === r.spend_line_shown
      && r.bookings_shown !== "@@unread@@" && r.spend_line_shown !== "@@unread@@"),
    { readings: readings.map((r) => ({ currency: r.server_currency, minor: r.minor,
        digits_on_bookings_face: r.bookings_shown, digits_on_spend_face: r.spend_line_shown,
        bookings_face: r.bookings_face_card, spend_face: r.spend_face_line,
        spend_group_total: r.spend_face_group_total })),
      spend_lede: lede, spend_amount_column: amounts });

  /* the third thing this screen does with a number the server never learned: the 花费 face's own honest
   * label for "no price" is 还没有价 (it is drawn on two lines above), so a `CNY 0.00` in the same column
   * is a zero the traveller did not spend. */
  const unknownCommitments = (wallet.commitments || [])
    .filter((c) => String(c.monetary_value_status ?? "") !== "KNOWN");
  const zeroAmounts = amounts.filter((a) => /(?:¥|￥|US\$|\$|CNY|JPY|USD)\s*0(?:\.00)?(?![\d])/.test(a));
  record("spend/an_unlearned_commitment_price_is_not_a_zero_on_the_face",
    zeroAmounts.length === 0,
    { unknown_commitment_rows: unknownCommitments.map((c) => ({ id: c.id,
        status: c.monetary_value_status, minor: (c.monetary_value || {}).amount_minor,
        currency: (c.monetary_value || {}).currency })),
      amounts_drawn: amounts, amounts_that_are_a_zero: zeroAmounts,
      honest_word_used_on_this_face: "还没有价" });

  fs.writeFileSync(OUT, JSON.stringify({
    generated_at: new Date().toISOString(), journey: JOURNEY, store: seed.lane_db,
    helpers: {
      bookings_face: "frontend/src/lib/money.ts formatMinorMoney (exponent aware)",
      spend_face: "frontend/src/features/trip/spendFacts.ts:312 moneyText (always /100)",
    },
    spend_line_count: lines.length, spend_lines: lines, spend_group_totals: totals,
    bookings_card_count: cards.length, results,
  }, null, 2), { encoding: "utf-8" });

  const failed = results.filter((r) => !r.pass);
  console.log(`\nARMS=${results.length} PASSED=${results.length - failed.length} FAILED=${failed.length}`);
  await browser.close();
  process.exit(failed.length ? 1 : 0);
})().catch(async (error) => {
  console.error("DRIVER_ERROR", error && error.message);
  fs.writeFileSync(OUT, JSON.stringify({ driver_error: String(error && error.message), results }, null, 2),
    { encoding: "utf-8" });
  process.exit(2);
});
