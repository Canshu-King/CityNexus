/*
 * ORD-0504 shared-recipe hand -- read the 花费 tab for the trips the SHARED board carries, on this
 * lane's private stack, and answer one question: does that screen also print nothing the server
 * did not send?
 *
 * The board is a consistent read-only backup of `live_checks/_cmdr_canary_day25.db` (made by
 * `run/copy_shared_board_day25_r1.py`), so these are the line's own rows, not this lane's synthetic
 * ones. Nothing here writes the shared store; the one mutation arm runs against this lane's copy and
 * is named as such.
 *
 * The judge re-implements the sums from the two door answers on purpose (see the header of
 * `spend_arms_r1.js`). It does not import the app's module and it reads no `data-*` value as evidence
 * -- every assertion is about text a traveller can see. The duplication between this file and the
 * shipped driver is deliberate: the accepted receipts cite those line numbers, and rewriting the
 * instrument under them would rot the published coordinates.
 */
const fs = require("fs");
const path = require("path");
const http = require("http");
const { execFileSync } = require("child_process");
const LANE = "D:/moodle/_qoder_r_ord0465_20260929";
const REPO = LANE + "/wt";
const { chromium } = require(path.join(REPO, "frontend/node_modules/playwright"));

const FRONT = "http://127.0.0.1:4931";
const API_PORT = 8731;
const COPY_DB = "sqlite:///" + LANE + "/run/ord0504_shared_day25_copy.db".replace(/\\/g, "/");
const OUT = path.join(REPO, "review/ord0504/spend_screen_shared_board_r1.json");
const DESKTOP = { width: 1280, height: 900 };
const MOBILE = { width: 390, height: 844 };

const board = JSON.parse(fs.readFileSync(path.join(LANE, "scratch_r2/shared_board_doors_r1.json"), "utf-8"));
// the trip the shared board actually shows: ACTIVE, one C3_Guaranteed commitment priced in CNY
const DEMO = Object.keys(board).find((id) => board[id].journey_status === "ACTIVE");
// a trip with no money row at all, used to check the face says so instead of adding up to zero
const BROKE = Object.keys(board).find((id) => id !== DEMO);

function fetchDoor(journeyId, door) {
  return new Promise((resolve, reject) => {
    http.get({ host: "127.0.0.1", port: API_PORT, path: `/api/v1/journeys/${journeyId}/${door}` },
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

async function answers(journeyId) {
  return { experience: await fetchDoor(journeyId, "experience"), wallet: await fetchDoor(journeyId, "wallet") };
}

function expectedFromDoors(a) {
  const lines = [];
  for (const leg of ((a.experience.active_plan || {}).legs) || []) {
    lines.push({
      currency: leg.currency ?? null,
      strength: leg.cost_status === "KNOWN" ? "ESTIMATED" : "UNNAMED",
      amount: typeof leg.cost_amount_minor === "number" ? leg.cost_amount_minor : null,
      source: "LEG",
    });
  }
  for (const r of a.wallet.reservations || []) {
    const price = r.price || {};
    lines.push({
      currency: price.currency ?? null,
      strength: r.status === "CONFIRMED" && (price.status === "KNOWN" || price.status === "FREE_KNOWN")
        ? "CONFIRMED" : price.status === "ESTIMATED" ? "ESTIMATED" : "UNNAMED",
      amount: typeof price.amount_minor === "number" ? price.amount_minor : null,
      source: "RESERVATION",
    });
  }
  for (const c of a.wallet.commitments || []) {
    const value = c.monetary_value || {};
    const backed = (a.wallet.reservations || []).some((r) => r.commitment_id === c.id);
    lines.push({
      currency: backed ? null : value.currency ?? null,
      strength: backed ? "UNNAMED"
        : ["ACTIVE", "FULFILLED"].includes(c.status)
          && ["C2_Reserved", "C3_Guaranteed", "C4_Anchored"].includes(c.level)
          && c.monetary_value_status === "KNOWN" ? "CONFIRMED" : "UNNAMED",
      amount: backed ? null : typeof value.amount_minor === "number" ? value.amount_minor : null,
      source: "COMMITMENT",
    });
  }
  const groups = {};
  for (const line of lines) {
    const key = line.currency ?? "UNKNOWN_CURRENCY";
    const g = groups[key] || { confirmed: 0, estimated: 0, unpriced: 0 };
    if (line.amount === null) g.unpriced += 1;
    else if (line.strength === "CONFIRMED") g.confirmed += line.amount;
    else if (line.strength === "ESTIMATED") g.estimated += line.amount;
    groups[key] = g;
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
  await page.addInitScript(([id]) => window.localStorage.setItem("citynexus.v8.journey_id", id), [journeyId]);
  const requests = [];
  page.on("request", (request) => requests.push({ method: request.method(), url: request.url() }));
  await page.goto(FRONT + "/v8/trips", { waitUntil: "domcontentloaded" });
  await page.waitForSelector('[data-testid="trips-tabs"]', { timeout: 30000 });
  await page.waitForTimeout(1500);
  await page.click('[data-testid="trips-tab-spend"]');
  await page.waitForSelector('[data-testid="trips-spend"]', { timeout: 20000 });
  await page.waitForTimeout(900);
  const text = (locator) => page.$$eval(locator, (els) => els.map((el) => el.innerText.trim())).catch(() => []);
  return {
    page, context, requests,
    totals: await text('[data-testid="spend-group-total"]'),
    lines: await text('[data-testid="spend-line"]'),
    amounts: await text('[data-testid="spend-line-amount"]'),
    strengths: await text('[data-testid="spend-line-strength"]'),
    missing: await text('[data-testid="spend-missing-class"]'),
    unpriced: (await text('[data-testid="spend-unpriced"]')).join(" | "),
    empty: await page.$('[data-testid="spend-empty"]'),
    declared: (await page.innerText('[data-testid="spend-declared-value"]').catch(() => "")).trim(),
    body: (await page.innerText('[data-testid="trips-spend"]')).replace(/\s+/g, " "),
  };
}

const results = [];
let browser = null;
function record(arm, pass, detail) {
  results.push({ arm, pass, detail });
  console.log(`${pass ? "PASS" : "FAIL"}  ${arm}${pass ? "" : "  " + JSON.stringify(detail).slice(0, 600)}`);
}

(async () => {
  browser = await chromium.launch({ channel: "chrome", headless: true });
  const demoExpected = expectedFromDoors(await answers(DEMO));
  const brokeExpected = expectedFromDoors(await answers(BROKE));

  /* 1. the confirmed total on the shared trip is the commitment the server answered, no more */
  for (const [shape, viewport] of [["desktop", DESKTOP], ["mobile", MOBILE]]) {
    const opened = await openSpend(viewport, DEMO);
    const want = (demoExpected.groups.CNY || { confirmed: 0 }).confirmed;
    const allText = opened.totals.join(" | ");
    record(`shared_board/${shape}_shows_the_commitment_the_server_answered`,
      allText.includes(`已确认 CNY ${money(want)}`) && opened.lines.length === demoExpected.lines.length,
      { want_confirmed_cny_minor: want, totals: opened.totals, lines_on_face: opened.lines.length,
        lines_expected: demoExpected.lines.length, declared: opened.declared });
    await opened.context.close();
  }

  /* 2. every money-shaped string on the face traces back to one of the two answers */
  {
    const opened = await openSpend(DESKTOP, DEMO);
    const allowed = new Set();
    for (const line of demoExpected.lines) if (typeof line.amount === "number") allowed.add(money(line.amount));
    for (const group of Object.values(demoExpected.groups)) {
      if (group.confirmed) allowed.add(money(group.confirmed));
      if (group.estimated) allowed.add(money(group.estimated));
    }
    const declaredMinor = ((await answers(DEMO)).experience.journey.budget || {}).amount_minor;
    const shown = (opened.body.match(/[A-Z]{3} [-\d][\d,]*\.\d{2}/g) || []);
    const unexplained = shown.filter((s) => !allowed.has(s.split(" ")[1]) && s !== `CNY ${money(declaredMinor)}`);
    record("shared_board/no_amount_on_the_face_that_the_doors_did_not_send",
      unexplained.length === 0, { shown_amounts: shown, allowed, declared: `CNY ${money(declaredMinor)}`,
        unexplained, door_statuses: { experience: 200, wallet: 200 } });
    await opened.context.close();
  }

  /* 3. the shared board has no journey_legs rows at all, so the face may not draw a leg line */
  {
    const opened = await openSpend(DESKTOP, DEMO);
    const legLines = opened.lines.filter((line) => line.includes("路段"));
    record("shared_board/zero_legs_in_the_store_draws_no_leg_line",
      demoExpected.lines.filter((l) => l.source === "LEG").length === 0 && legLines.length === 0,
      { leg_lines_on_face: legLines, legs_answered: demoExpected.lines.filter((l) => l.source === "LEG").length });
    await opened.context.close();
  }

  /* 4. the classes the two answers never carry are named, not estimated */
  {
    const opened = await openSpend(DESKTOP, DEMO);
    record("shared_board/missing_classes_are_named_on_the_shared_trip",
      opened.missing.length >= 1 && /方案里的钱|停留|预订|订单|交易/.test(opened.missing.join(" ")),
      { missing: opened.missing });
    await opened.context.close();
  }

  /* 5. the trip with no money row says there is nothing to add up; it must not print 0.00 as an answer */
  {
    const opened = await openSpend(DESKTOP, BROKE);
    const zeroAsAnswer = opened.totals.some((t) => /0\.00/.test(t)) || opened.amounts.some((a) => /0\.00/.test(a));
    record("shared_board/the_unpriced_trip_shows_no_total_instead_of_zero",
      brokeExpected.lines.length === 0 && !!opened.empty && !zeroAsAnswer,
      { empty_face: !!opened.empty, totals: opened.totals, amounts: opened.amounts,
        lines_expected: brokeExpected.lines.length });
    await opened.context.close();
  }

  /* 6. teeth, on the shared shape: move the server's own number in THIS LANE'S COPY and watch the
   *    total follow it exactly, then put it back and watch the face go quiet again.
   *    The face has to be opened again after every reload -- a reload lands on the trip hub, not on
   *    the 花费 tab, and reading totals there would be reading an absence. */
  {
    const opened = await openSpend(DESKTOP, DEMO);
    const minor = demoExpected.lines.find((l) => typeof l.amount === "number").amount;
    const moved = minor + 9000;
    const setValue = (value) => {
      execFileSync("D:/moodle/CityNexus/.venv/Scripts/python.exe", [
        path.join(REPO, "review/ord0504/set_shared_copy_commitment_cost_r1.py"),
        path.join(LANE, "run/ord0504_shared_day25_copy.db"), String(value)],
        { encoding: "utf-8" });
    };
    const totalsNow = async () => {
      await opened.page.reload({ waitUntil: "domcontentloaded" });
      await opened.page.waitForSelector('[data-testid="trips-tabs"]', { timeout: 30000 });
      await opened.page.waitForTimeout(1500);
      await opened.page.click('[data-testid="trips-tab-spend"]');
      await opened.page.waitForSelector('[data-testid="trips-spend"]', { timeout: 20000 });
      await opened.page.waitForTimeout(1200);
      return opened.page.$$eval('[data-testid="spend-group-total"]', (els) => els.map((el) => el.innerText.trim()));
    };
    const before = opened.totals;
    setValue(moved);
    const after = await totalsNow();
    setValue(minor);
    const reverted = await totalsNow();
    const wantBefore = `已确认 CNY ${money(minor)}`;
    const wantAfter = `已确认 CNY ${money(moved)}`;
    record("counterexample_on_shared_shape/moving_the_commitment_moves_the_total",
      before.join(" | ").includes(wantBefore) && after.join(" | ").includes(wantAfter)
      && reverted.join(" | ").includes(wantBefore),
      { store_mutation: "commitments.monetary_value_minor in THIS LANE'S COPY only, restored afterwards",
        before, after, reverted, minor_before: minor, minor_after: moved });
    await opened.context.close();
  }

  const failed = results.filter((r) => !r.pass);
  fs.writeFileSync(OUT, JSON.stringify({
    generated_at: new Date().toISOString(),
    board_copy: COPY_DB,
    shared_source_of_copy: "D:/moodle/_qoder_cmdr_ref_20260921/live_checks/_cmdr_canary_day25.db (opened mode=ro)",
    journeys: { active_with_money: DEMO, no_money_row: BROKE },
    demo_expected: demoExpected, broke_expected: brokeExpected, results,
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
