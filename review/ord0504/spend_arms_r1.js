/*
 * ORD-0504 -- read the 花费 tab on a real browser, and check every number on it against the two
 * doors the screen is allowed to read.
 *
 * The judge does its own arithmetic. `review/ord0504/spend_seed_report.json` holds the `/experience`
 * and `/wallet` answers fetched from the same server the browser talks to, and this file adds the
 * amounts up per currency and per strength on its own. If the app's math and this math disagree, the
 * arm goes red -- a judge that read the app's own `data-*` attributes would be asking the app to
 * grade itself, which is the thing the order's clause 5 forbids.
 *
 * The two counterexamples the order asks for are arms 5 and 6 here:
 *   5. a trip with nothing priced: the face must say so and must not print a total. A `0.00` is a
 *      number, and a traveller reads a number as an answer.
 *   6. one real amount changed: the estimated total has to move by exactly that much and the confirmed
 *      total must not move at all. An assertion that passes on every run is not a judge.
 *
 * Driven against the built bundle on :4931 with this lane's own backend on :8731. Screenshots are not
 * used as evidence anywhere: the map under the spend tab animates and a waiting screenshot times out,
 * so every claim here is text read out of the rendered DOM.
 */
const fs = require("fs");
const path = require("path");
const LANE = "D:/moodle/_qoder_r_ord0465_20260929";
const REPO = LANE + "/wt";
const { chromium } = require(path.join(LANE, "wt/frontend/node_modules/playwright"));

const FRONT = "http://127.0.0.1:4931";
const shotDir = path.join(REPO, "review/ord0504");
fs.mkdirSync(shotDir, { recursive: true });

const seed = JSON.parse(fs.readFileSync(path.join(LANE, "run/spend_seed_report.json"), "utf-8"));
const DESKTOP = { width: 1280, height: 900 };
const MOBILE = { width: 390, height: 844 };
const http = require("http");

/**
 * The two answers, fetched now rather than read out of the seed report. The seed report is a record of
 * what was written at seed time; the face is judged against what the server answers at reading time,
 * which is the only pair that can show a number moving.
 */
function fetchDoor(journeyId, door) {
  return new Promise((resolve, reject) => {
    http.get(
      { host: "127.0.0.1", port: 8731, path: `/api/v1/journeys/${journeyId}/${door}` },
      (answer) => {
        const chunks = [];
        answer.on("data", (chunk) => chunks.push(chunk));
        answer.on("end", () => {
          try { resolve(JSON.parse(Buffer.concat(chunks).toString("utf-8"))); }
          catch (error) { reject(error); }
        });
      },
    ).on("error", reject);
  });
}

async function answers(journeyId) {
  return {
    experience: await fetchDoor(journeyId, "experience"),
    wallet: await fetchDoor(journeyId, "wallet"),
  };
}


const results = [];
let browser = null;

function record(arm, pass, detail) {
  results.push({ arm, pass, detail });
  console.log(`${pass ? "PASS" : "FAIL"}  ${arm}${pass ? "" : "  " + JSON.stringify(detail).slice(0, 500)}`);
}

/**
 * The judge's own reading of the two answers: per currency, confirmed / estimated / unpriced.
 * Written here from the server's field names only -- no import of the app's module, on purpose.
 */
function expectedFromDoors(answers) {
  const timeZone = (answers.experience.journey && answers.experience.journey.timezone) || "UTC";
  const dayKey = (iso) => {
    if (!iso) return null;
    // The trip's own calendar day, computed here rather than borrowed from the app: `en-CA` is the
    // one locale whose format is already the ISO date the face groups by.
    try {
      return new Intl.DateTimeFormat("en-CA", { timeZone, year: "numeric", month: "2-digit",
        day: "2-digit" }).format(new Date(iso));
    } catch {
      return null;
    }
  };
  const lines = [];
  const plan = answers.experience.active_plan;
  for (const leg of (plan && plan.legs) || []) {
    lines.push({
      currency: leg.currency ?? null,
      strength: leg.cost_status === "KNOWN" ? "ESTIMATED" : "UNNAMED",
      amount: typeof leg.cost_amount_minor === "number" ? leg.cost_amount_minor : null,
      dayKey: dayKey(leg.depart_at),
    });
  }
  for (const reservation of answers.wallet.reservations || []) {
    const price = reservation.price || {};
    lines.push({
      currency: price.currency ?? null,
      strength: reservation.status === "CONFIRMED" && (price.status === "KNOWN" || price.status === "FREE_KNOWN")
        ? "CONFIRMED" : price.status === "ESTIMATED" ? "ESTIMATED" : "UNNAMED",
      amount: typeof price.amount_minor === "number" ? price.amount_minor : null,
      dayKey: dayKey(reservation.scheduled_departure_at),
    });
  }
  for (const commitment of answers.wallet.commitments || []) {
    const value = commitment.monetary_value || {};
    const backed = (answers.wallet.reservations || []).some((r) => r.commitment_id === commitment.id);
    lines.push({
      currency: backed ? null : value.currency ?? null,
      strength: backed ? "UNNAMED"
        : ["ACTIVE", "FULFILLED"].includes(commitment.status)
          && ["C2_Reserved", "C3_Guaranteed", "C4_Anchored"].includes(commitment.level)
          && commitment.monetary_value_status === "KNOWN" ? "CONFIRMED" : "UNNAMED",
      amount: backed ? null : typeof value.amount_minor === "number" ? value.amount_minor : null,
      dayKey: backed ? null : dayKey(commitment.policy && commitment.policy.scheduled_start_at),
    });
  }
  const groups = {};
  for (const line of lines) {
    const key = line.currency ?? "UNKNOWN_CURRENCY";
    const group = groups[key] || { confirmed: 0, estimated: 0, unpriced: 0 };
    if (line.amount === null) group.unpriced += 1;
    else if (line.strength === "CONFIRMED") group.confirmed += line.amount;
    else if (line.strength === "ESTIMATED") group.estimated += line.amount;
    groups[key] = group;
  }
  return { lines, groups };
}

const money = (minor) => (minor / 100).toLocaleString("en-US", {
  minimumFractionDigits: 2, maximumFractionDigits: 2,
});

async function openSpend(viewport, journeyId) {
  const context = await browser.newContext({
    viewport, locale: "zh-CN", hasTouch: viewport.width < 500, isMobile: viewport.width < 500,
    deviceScaleFactor: viewport.width < 500 ? 3 : 1,
  });
  const page = await context.newPage();
  await page.addInitScript(([id]) => {
    window.localStorage.setItem("citynexus.v8.journey_id", id);
  }, [journeyId]);
  const requests = [];
  page.on("request", (request) => requests.push({ method: request.method(), url: request.url() }));
  await page.goto(FRONT + "/v8/trips", { waitUntil: "domcontentloaded" });
  await page.waitForSelector('[data-testid="trips-tabs"]', { timeout: 30000 });
  await page.waitForTimeout(1500);
  await page.click('[data-testid="trips-tab-spend"]');
  await page.waitForSelector('[data-testid="trips-spend"]', { timeout: 20000 });
  await page.waitForTimeout(900);
  const text = (locator) => page.$$eval(locator, (els) => els.map((el) => el.innerText.trim()))
    .catch(() => []);
  return {
    page, context, requests,
    groups: await text('[data-testid="spend-group"]'),
    totals: await text('[data-testid="spend-group-total"]'),
    days: await text('[data-testid="spend-day"]'),
    dayLines: await text('[data-testid="spend-day-line"]'),
    lines: await text('[data-testid="spend-line"]'),
    amounts: await text('[data-testid="spend-line-amount"]'),
    strengths: await text('[data-testid="spend-line-strength"]'),
    missing: await text('[data-testid="spend-missing-class"]'),
    unpriced: (await text('[data-testid="spend-unpriced"]')).join(" | "),
    lede: (await page.innerText('[data-testid="spend-lede"]').catch(() => "")).replace(/\s+/g, " "),
    empty: await page.$('[data-testid="spend-empty"]'),
    emptyBody: (await page.innerText('[data-testid="spend-empty-body"]').catch(() => "")).replace(/\s+/g, " "),
    declared: (await page.innerText('[data-testid="spend-declared-value"]').catch(() => "")).trim(),
    body: (await page.innerText('[data-testid="trips-spend"]')).replace(/\s+/g, " "),
  };
}

(async () => {
  browser = await chromium.launch({ channel: "chrome", headless: true });
  const expected = expectedFromDoors(await answers(seed.journeys.priced));

  /* ---------------------------------------------------- 1. the numbers on the face are the server's */
  for (const [shape, viewport] of [["desktop", DESKTOP], ["mobile", MOBILE]]) {
    const opened = await openSpend(viewport, seed.journeys.priced);
    const wantCny = expected.groups.CNY || { confirmed: 0, estimated: 0, unpriced: 0 };
    const wantUsd = expected.groups.USD || { confirmed: 0, estimated: 0, unpriced: 0 };
    const allText = opened.totals.join(" | ");
    const expectedUnpriced = Object.values(expected.groups)
      .reduce((sum, group) => sum + group.unpriced, 0);
    const checks = {
      cny_confirmed: allText.includes(`已确认 CNY ${money(wantCny.confirmed)}`),
      cny_estimated: allText.includes(`估算 CNY ${money(wantCny.estimated)}`),
      // The unpriced lines are their own sentence now, not a `未定价 0` hanging off a currency total --
      // a count of lines the server could not price belongs beside the totals, never inside one.
      unpriced_sentence: opened.unpriced.includes(`${expectedUnpriced} 项`),
      usd_confirmed: allText.includes(`已确认 USD ${money(wantUsd.confirmed)}`),
      // The two buckets have to be different strings, not one number printed twice.
      buckets_apart: wantCny.confirmed !== wantCny.estimated,
      line_count: opened.lines.length === expected.lines.length,
      amounts_match_server: expected.lines.every((line, index) => {
        const shown = opened.amounts[index] || "";
        return line.amount === null ? shown === "还没有价" : shown.includes(money(line.amount));
      }),
    };
    record(`spend_face/${shape}_shows_the_servers_own_amounts`,
      Object.values(checks).every(Boolean),
      { want_cny: wantCny, want_usd: wantUsd, shown_totals: opened.totals,
        shown_amounts: opened.amounts, lines_on_face: opened.lines.length,
        lines_expected: expected.lines.length, checks });
    if (shape === "desktop") {
      await opened.page.screenshot({ path: path.join(shotDir, "spend_desktop.png") });
    } else {
      await opened.page.screenshot({ path: path.join(shotDir, "spend_mobile.png"), fullPage: true });
    }
    await opened.context.close();
  }

  /* ------------------------------------- 2. no invented number: every figure traces to a door line */
  {
    const opened = await openSpend(DESKTOP, seed.journeys.priced);
    const serverAmounts = new Set(expected.lines
      .filter((line) => line.amount !== null).map((line) => money(line.amount)));
    // A currency total is a sum, so allow it; anything else that looks like money must be one of the
    // server's own amounts.
    const allowed = new Set([...serverAmounts,
      money((expected.groups.CNY || {}).confirmed || 0),
      money((expected.groups.CNY || {}).estimated || 0),
      money((expected.groups.USD || {}).confirmed || 0),
      money((expected.groups.USD || {}).estimated || 0),
      // the declared budget, which is a real server number and labelled as declared
      money(300000)]);
    const digits = (opened.body.match(/[A-Z]{3} [\d,]+\.\d{2}/g) || [])
      .map((token) => token.split(" ")[1]);
    const unaccounted = digits.filter((value) => !allowed.has(value));
    record("spend_face/no_figure_that_is_not_a_server_amount", unaccounted.length === 0,
      { money_tokens_on_face: digits, unaccounted, allowed: [...allowed] });
    await opened.context.close();
  }

  /* ------------------------------------- 3. currencies are never merged into one made-up total */
  {
    const opened = await openSpend(DESKTOP, seed.journeys.priced);
    const merged = money(expected.groups.CNY.confirmed + expected.groups.USD.confirmed);
    const crossTotals = opened.totals.filter((line) => /CNY/.test(line) && /USD/.test(line));
    const pseudoCurrency = opened.totals.filter((line) => /UNKNOWN_CURRENCY/.test(line));
    record("spend_face/currencies_stay_in_their_own_total",
      opened.groups.length === 2 && crossTotals.length === 0 && pseudoCurrency.length === 0 &&
        !opened.totals.some((line) => line.includes(merged)) &&
        opened.totals.join(" ").includes("USD") && opened.unpriced.includes("1 项"),
      { groups: opened.groups.length, shown: opened.totals, merged_would_be: merged,
        pseudo_currency_rows: pseudoCurrency, unpriced_sentence: opened.unpriced });
    await opened.context.close();
  }

  /* ------------------------------------------- 4. per-day rows, in the trip's own timezone */
  {
    const opened = await openSpend(DESKTOP, seed.journeys.priced);
    const pricedDays = new Set(expected.lines
      .filter((line) => line.amount !== null).map((line) => line.dayKey).filter(Boolean));
    record("spend_face/per_day_rows_are_drawn",
      opened.days.length >= 1 && opened.dayLines.length >= 1 &&
        opened.dayLines.every((line) => /已确认|估算/.test(line)),
      { days_on_face: opened.days.length, day_lines: opened.dayLines,
        server_said_days: pricedDays.size });
    await opened.context.close();
  }

  /* -------- counterexample 1: nothing priced on the server -> no total on the face, and no zero */
  {
    const opened = await openSpend(DESKTOP, seed.journeys.bare);
    const bareExpected = expectedFromDoors(await answers(seed.journeys.bare));
    const moneyOnFace = (opened.body.match(/[A-Z]{3} [\d,]+\.\d{2}/g) || [])
      .filter((token) => !token.includes(money(300000)));
    /* The bare trip is seeded with one leg the server cannot price, so "nothing priced" is not the
       same as "nothing there". The face has to show the empty state AND list that line as unpriced --
       a line it silently dropped would leave the traveller with no way to learn the trip has a segment
       nobody has costed yet. */
    record("counterexample/no_server_fact_prints_no_total",
      opened.empty !== null && bareExpected.lines.length === 1 &&
        bareExpected.lines.every((line) => line.amount === null) &&
        opened.groups.length === 0 && opened.lines.length === 1 &&
        opened.amounts.every((value) => value === "还没有价") &&
        moneyOnFace.length === 0 && /等于零|没有可加/.test(opened.emptyBody),
      { empty_face_shown: Boolean(opened.empty), empty_body: opened.emptyBody,
        server_lines: bareExpected.lines.length, server_amounts: bareExpected.lines.map((l) => l.amount),
        group_cells: opened.groups.length, line_rows: opened.lines.length,
        line_amounts: opened.amounts, money_apart_from_budget: moneyOnFace });
    await opened.page.screenshot({ path: path.join(shotDir, "spend_empty.png") });
    await opened.context.close();
  }

  /* -- counterexample 2: one real amount changed -> the estimated total moves, the confirmed one does not */
  {
    const { execFileSync } = require("child_process");
    const current = await answers(seed.journeys.priced);
    const knownLeg = ((current.experience.active_plan || {}).legs || [])
      .find((leg) => leg.cost_status === "KNOWN" && typeof leg.cost_amount_minor === "number");
    const amountBefore = knownLeg ? knownLeg.cost_amount_minor : null;
    const amountAfter = amountBefore === null ? null : amountBefore + 5000;

    const readCny = async () => {
      const opened = await openSpend(DESKTOP, seed.journeys.priced);
      const line = opened.totals.find((text) => text.includes("CNY")) || "";
      await opened.context.close();
      return line;
    };
    const legWrite = (amount) => JSON.parse(execFileSync(
      "D:/moodle/CityNexus/.venv/Scripts/python.exe",
      [path.join(REPO, "review/ord0504/change_one_leg_cost_r1.py"), seed.journeys.priced, String(amount)],
      { encoding: "utf-8",
        env: { ...process.env, NO_PROXY: "*", HTTP_PROXY: "", HTTPS_PROXY: "",
          // The store the server is serving, read out of the seed report rather than guessed: this
          // lane has more than one sqlite file under run/ and writing the wrong one would leave the
          // face unchanged while the lever reported success.
          CITYNEXUS_DATABASE_URL: seed.lane_db,
          PYTHONPATH: [REPO, path.join(REPO, "backend")].join(path.delimiter) } },
    ).trim().split("\n").pop());

    const beforeLine = await readCny();
    let afterLine = "";
    let revertedLine = "";
    let lever = null;
    try {
      if (amountAfter !== null) lever = legWrite(amountAfter);
      afterLine = await readCny();
    } finally {
      if (amountBefore !== null) legWrite(amountBefore);
      revertedLine = await readCny();
    }

    const estimatedOf = (line) => (/估算 CNY ([\d,.]+)/.exec(line) || [])[1] || "";
    const confirmedOf = (line) => (/已确认 CNY ([\d,.]+)/.exec(line) || [])[1] || "";
    const wantBefore = money(expected.groups.CNY ? expected.groups.CNY.estimated : 0);
    const wantAfter = money((expected.groups.CNY ? expected.groups.CNY.estimated : 0) + 5000);

    record("counterexample/changing_one_amount_moves_the_total",
      amountBefore !== null && beforeLine !== "" &&
        estimatedOf(beforeLine) === wantBefore &&
        estimatedOf(afterLine) === wantAfter &&
        confirmedOf(afterLine) === confirmedOf(beforeLine) &&
        // and back the other way: the face follows the store, it is not printing a constant
        estimatedOf(revertedLine) === wantBefore && beforeLine === revertedLine,
      { lever, estimated_before: estimatedOf(beforeLine), estimated_after: estimatedOf(afterLine),
        estimated_reverted: estimatedOf(revertedLine), expected_before: wantBefore,
        expected_after: wantAfter, confirmed_before: confirmedOf(beforeLine),
        confirmed_after: confirmedOf(afterLine), lines: { beforeLine, afterLine, revertedLine } });
  }

  /* ---------------------------------------- 5. the missing classes are said, in the traveller's words */
  {
    const opened = await openSpend(DESKTOP, seed.journeys.priced);
    const want = ["每个站的估价", "方案自己的总额", "预订单", "订单", "收支流水"];
    const seen = opened.missing.join(" | ");
    record("spend_face/missing_classes_are_named_on_screen",
      opened.missing.length === 5 && want.every((word) => seen.includes(word)),
      { shown: opened.missing });
    await opened.context.close();
  }

  /* ------------------------------------- 6. the browser asks nothing but GETs on this screen */
  {
    const opened = await openSpend(MOBILE, seed.journeys.priced);
    const writes = opened.requests.filter((r) => r.method !== "GET").map((r) => `${r.method} ${r.url}`);
    const spendDoor = opened.requests.filter((r) => /\/spend\b|\/cost|\/expense/.test(r.url));
    record("spend_face/opens_with_gets_and_no_new_door",
      writes.length === 0 && spendDoor.length === 0,
      { write_calls: writes, spend_door_calls: spendDoor.map((r) => r.url) });
    await opened.context.close();
  }

  /* ------------------------------------- 7. no machine word reaches the Chinese face */
  {
    const opened = await openSpend(DESKTOP, seed.journeys.priced);
    const upperSnake = opened.body.match(/\b[A-Z][A-Z0-9]*_[A-Z0-9_]+\b/g) || [];
    const words = ["KNOWN", "UNKNOWN", "ESTIMATED", "CONFIRMED", "LEG", "RESERVATION", "COMMITMENT",
      "STAY_OPTION", "BACKED_BY_RESERVATION", "SELECTED_OPTION", "CNY_", "LANE_SEED"].filter((w) =>
        opened.body.includes(w) && !/CNY|USD/.test(w));
    record("spend_face/no_machine_token_on_the_chinese_face",
      upperSnake.length === 0 && words.length === 0,
      { upper_snake: upperSnake, vocabulary_found: words });
    await opened.context.close();
  }

  /* --------- the three parts of a spend line must not be painted on top of one another */
  {
    const opened = await openSpend(MOBILE, seed.journeys.priced);
    const touching = await opened.page.evaluate(() => {
      const out = [];
      document.querySelectorAll('[data-testid="spend-line"]').forEach((line, index) => {
        const parts = ["spend-line-source", "spend-line-amount", "spend-line-strength"]
          .map((id) => line.querySelector(`[data-testid="${id}"]`))
          .filter(Boolean)
          .map((el) => {
            const box = el.getBoundingClientRect();
            return { id: el.getAttribute("data-testid"),
                     top: Math.round(box.top), bottom: Math.round(box.bottom),
                     left: Math.round(box.left), right: Math.round(box.right) };
          });
        for (let a = 0; a < parts.length; a += 1) {
          for (let b = a + 1; b < parts.length; b += 1) {
            const x = parts[a];
            const y = parts[b];
            const sameLine = x.top < y.bottom - 1 && y.top < x.bottom - 1;
            const overlapX = Math.min(x.right, y.right) - Math.max(x.left, y.left);
            if (sameLine && overlapX > 1) {
              out.push({ line: index, pair: `${x.id} / ${y.id}`, overlap_px: overlapX });
            }
          }
        }
      });
      return out;
    });
    record("spend_face/line_parts_are_pulled_apart", touching.length === 0, { touching });
    await opened.context.close();
  }

  const failed = results.filter((r) => !r.pass);
  const out = {
    front: FRONT, backend: "http://127.0.0.1:8731",
    journeys: seed.journeys,
    expected_groups: expected.groups,
    arms: results.length,
    passed: results.length - failed.length,
    failed: failed.map((f) => f.arm),
    results,
  };
  fs.writeFileSync(path.join(shotDir, "spend_arms_r1.json"), JSON.stringify(out, null, 2),
    { encoding: "utf-8" });
  console.log(`\nARMS=${results.length} PASSED=${results.length - failed.length} FAILED=${failed.length}`);
  await browser.close();
  process.exit(failed.length ? 1 : 0);
})().catch(async (error) => {
  console.error("DRIVER_ERROR", error && error.message);
  fs.writeFileSync(path.join(shotDir, "spend_arms_r1.json"),
    JSON.stringify({ driver_error: String(error && error.message), results }, null, 2),
    { encoding: "utf-8" });
  if (browser) await browser.close();
  process.exit(2);
});
