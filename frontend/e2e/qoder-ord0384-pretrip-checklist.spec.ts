/**
 * ORD-0384 -- the pre-trip checklist may only say what the server's fields say.
 *
 * The expectation table below is written from the payload fields **inside this file**, on purpose: the
 * panel and the derivation module already agree by construction, so comparing the screen to the module
 * would be self-proof and would stay green through any mutation of the rules. Judging the screen
 * against an independent reading of the same response is what makes mutation M1 (a rule inverted) and
 * M2 (an empty state that drops its action) go red.
 *
 * Cells:
 *   X1  every item on the screen is true in the response, and every response condition that is true has
 *       an item -- co-presence, both directions, on the live sealed-demo journey;
 *   X2  clear a field in the response and its item disappears; put it back and the item returns -- the
 *       "completion is not a checkbox" claim, measured;
 *   X3  a fully clean response yields no items, one honest empty line, and a strikable action;
 *   X4  every item names its endpoint and field on screen, and no raw network reading or smuggled
 *       sentence reaches the DOM or an attribute (Q64=① / Q70 / Q71);
 *   X5  the band that can read "一切正常" never sits underneath a list of open items -- in the clear
 *       state it drops its own kicker, so an unqualified all-clear below "还差这些" is a denial of the
 *       list above it, which is the same one-screen-one-rule defect `today-attention-does-not-
 *       contradict-the-map` already pins for the map.
 */
import { expect, test, type Page, type Route } from "@playwright/test";
import { writeFileSync } from "node:fs";
import { evidencePath } from "./_qoderEvidence";
import { strikeableOnly, surveyName } from "./_qoderNamedHits";

const FILE = "e2e/qoder-ord0384-pretrip-checklist.spec.ts";
const node = (id: string, detail: string) => `${FILE} :: ${id} — ${detail}`;
const RUN = process.env.CITYNEXUS_E2E_RUN_ID ?? "local";

type Bag = Record<string, any>;

/**
 * The independent truth table: for each item the panel can render, the condition on the response that
 * makes it true. Written against the fields, not against `derivePretripChecklist`.
 */
const TRUTH: Record<string, (exp: Bag, wal: Bag | null) => boolean> = {
  stay_budget_undeclared: (e) => e.trip?.stay_budget?.declared === null,
  plan_feasibility_open: (e) => Array.isArray(e.experience_flags?.feasibility_failures) && e.experience_flags.feasibility_failures.length > 0,
  stay_chosen_but_unconfirmed: (e, w) => !!e.selected_option_id && (w?.reservations?.length ?? -1) === 0 && (w?.commitments?.length ?? -1) === 0,
  stay_not_chosen: (e) => e.selected_option_id === null || e.selected_option_id === undefined || e.selected_option_id === "",
  no_active_plan: (e) => e.active_plan === null || e.active_plan === undefined,
  recovery_needs_decision: (e) => e.recovery?.requires_user_decision === true,
  arrival_anchor_missing: (e) => !e.trip?.arrival_anchor?.at,
  departure_anchor_missing: (e) => !e.trip?.departure_anchor?.at,
  offline_pack_not_ready: (_e, w) => w?.offline_ready === false,
};

const readings: Record<string, unknown> = {};

function armOf(title: string): string {
  return /^([X]\d)/.exec(title)?.[1] ?? title.slice(0, 2);
}

test.afterEach(({}, info) => {
  const arm = armOf(info.title);
  const prior = (readings[arm] ?? {}) as Record<string, unknown>;
  const body: Record<string, unknown> = { ...prior };
  body.nodeid = `${info.file}:${info.line} > ${info.title}`;
  body.test_status = info.status;
  if (info.status !== "passed") {
    body.error_head = String(info.error?.message ?? "").replace(/\s+/g, " ").slice(0, 700);
  }
  writeFileSync(
    evidencePath(`ord0384/${RUN}__${arm}.json`),
    JSON.stringify({ run_id: RUN, arm, spec: FILE, ...body }, null, 1),
    "utf-8",
  );
});

async function stageJourneyId(page: Page): Promise<string> {
  const scene = (await (await page.request.get("/api/v1/demo/scene")).json()) as { journey_id?: string };
  const id = String(scene.journey_id ?? "");
  expect(id.length > 0, node("boot", "the stage named no journey, so there is nothing to check against"));
  return id;
}

async function boot(page: Page, id: string, w = 390, h = 844) {
  await page.addInitScript((jid) => {
    localStorage.clear();
    localStorage.setItem("citynexus.v8.journey_id", jid);
    localStorage.setItem("citynexus.locale", "zh-CN");
  }, id);
  page.setDefaultTimeout(30_000);
  await page.setViewportSize({ width: w, height: h });
}

/** Read what the screen rendered, as keys. */
async function renderedKeys(page: Page): Promise<string[]> {
  return page.$$eval('[data-testid="pretrip-item"]', (els) =>
    els.map((el) => el.getAttribute("data-cnx-key") ?? "?"),
  );
}

/** Read the same two responses the app read, from the test's own connection. */
async function truthPair(page: Page, id: string): Promise<{ exp: Bag; wal: Bag }> {
  const exp = (await (await page.request.get(`/api/v1/journeys/${id}/experience`)).json()) as Bag;
  const wal = (await (await page.request.get(`/api/v1/journeys/${id}/wallet`)).json()) as Bag;
  return { exp, wal };
}

/**
 * Patch each leg of the pair on its own way back. The first version patched a local `wal` object and
 * then fulfilled the **unpatched** wallet body, so every "clean response" cell was silently judging a
 * dirty one -- which is why X3 reported no empty line while X1 was green.
 */
function patchLegs(id: string, patchExp: (exp: Bag) => void, patchWal: (wal: Bag) => void) {
  return async (route: Route) => {
    const url = route.request().url();
    const which = url.includes(`/journeys/${id}/experience`) ? "exp" : url.includes(`/journeys/${id}/wallet`) ? "wal" : null;
    if (!which) return route.fallback();
    const res = await route.fetch();
    const body = await res.json().catch(() => null);
    if (!body || typeof body !== "object") return route.fallback();
    (which === "exp" ? patchExp : patchWal)(body);
    return route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(body) });
  };
}

/** The patch that makes every rule false, field by field. */
const CLEAN_EXP = (exp: Bag) => {
  exp.trip.stay_budget.declared = true;
  exp.experience_flags.feasibility_failures = [];
  exp.recovery = null;
  if (!exp.selected_option_id) exp.selected_option_id = "ORD0384-STAY";
  if (!exp.trip.arrival_anchor) exp.trip.arrival_anchor = { at: "2026-09-21T02:00:00Z" };
  if (!exp.trip.departure_anchor) exp.trip.departure_anchor = { at: "2026-09-22T10:00:00Z" };
  exp.trip.arrival_anchor.at = exp.trip.arrival_anchor.at ?? "2026-09-21T02:00:00Z";
  exp.trip.departure_anchor.at = exp.trip.departure_anchor.at ?? "2026-09-22T10:00:00Z";
};
const CLEAN_WAL = (wal: Bag) => {
  wal.offline_ready = true;
  wal.reservations = [{ id: "ORD0384-R1", type: "HOTEL", confirmation_ref: "X", scheduled_departure_at: null, scheduled_arrival_at: null, realtime_status: "CONFIRMED", price: { amount_minor: 1, currency: "CNY", status: "KNOWN" } }];
  wal.commitments = [{ id: "ORD0384-C1", level: "SOFT", kind: "STAY", external_ref: null, status: "CONFIRMED", monetary_value_status: "KNOWN" }];
};
const NO_CLEAN_EXP = (exp: Bag) => {
  exp.trip.stay_budget.declared = null;
  exp.experience_flags.feasibility_failures = ["ORD0384_SYNTHETIC_FAILURE"];
};
const NO_CLEAN_WAL = (wal: Bag) => {
  wal.reservations = [];
  wal.commitments = [];
};

/**
 * Both legs have to have answered before the screen is judged: the wallet arrives after the experience,
 * so reading the list in between would compare a half-built panel against a full response and call the
 * difference a product defect. The waits are registered before the navigation that triggers them.
 */
function awaitSources(page: Page, id: string) {
  return Promise.all([
    page.waitForResponse((r) => r.url().includes(`/journeys/${id}/experience`) && r.status() === 200),
    page.waitForResponse((r) => r.url().includes(`/journeys/${id}/wallet`) && r.status() === 200),
  ]);
}

async function settleJourney(page: Page, id: string, route = "/v8/hub") {
  const settled = awaitSources(page, id);
  await page.goto(route, { waitUntil: "load" });
  await settled;
  await expect(page.getByTestId("pretrip-checklist"), node("boot", `the checklist band is missing on ${route}`)).toBeVisible({ timeout: 30_000 });
}

/** Wait for the panel to settle on a set of keys, in whichever direction is being asserted. */
async function expectKeysInclude(page: Page, keys: string[], where: string) {
  await expect
    .poll(() => renderedKeys(page), { message: node(where, `the panel never showed ${JSON.stringify(keys)}`), timeout: 20_000 })
    .toEqual(expect.arrayContaining(keys));
}

async function expectKeysExclude(page: Page, keys: string[], where: string) {
  await expect
    .poll(async () => (await renderedKeys(page)).filter((k) => keys.includes(k)), {
      message: node(where, `the panel never dropped ${JSON.stringify(keys)}`),
      timeout: 20_000,
    })
    .toEqual([]);
}

/* ------------------------------------------------------------------ X1: co-presence, both directions */

test("X1_every_item_is_true_in_the_response_and_every_true_condition_has_an_item — 屏上每条都对得上响应字段，字段成立的每条都在屏上", async ({ page }) => {
  test.setTimeout(300_000);
  const arm = "X1";
  const id = await stageJourneyId(page);
  await boot(page, id);
  await settleJourney(page, id);
  await expect(page.getByTestId("today-hero"), node(arm, "Today never rendered")).toBeVisible({ timeout: 30_000 });
  /* once both legs have answered, the "a source is still missing" line must be gone -- otherwise the
     panel is permanently hedging and the co-presence comparison below means nothing. Polled, because
     the line is legitimately there until React has applied the wallet response. */
  await expect(
    page.getByTestId("pretrip-source-pending"),
    node(arm, "the panel still says a source has not been read, after both responses answered"),
  ).toHaveCount(0, { timeout: 15_000 });
  const keys = await renderedKeys(page);
  const { exp, wal } = await truthPair(page, id);
  const expected = Object.entries(TRUTH).filter(([, holds]) => holds(exp, wal)).map(([k]) => k);
  /* settle both ways: the panel may still be rendering the second source's effect */
  await expect
    .poll(() => renderedKeys(page), { message: node(arm, `the panel never settled on ${JSON.stringify(expected)}`), timeout: 20_000 })
    .toEqual(expect.arrayContaining(expected));
  const settledKeys = await renderedKeys(page);
  const missing = expected.filter((k) => !settledKeys.includes(k));
  const invented = settledKeys.filter((k) => !(TRUTH[k]?.(exp, wal) ?? false));
  readings[arm] = {
    journey_id: id,
    rendered_keys: settledKeys,
    truth_table_keys: expected,
    rendered_but_false: invented,
    true_but_absent: missing,
    declared_value: exp.trip?.stay_budget?.declared,
    feasibility_failures: exp.experience_flags?.feasibility_failures,
    selected_option_id: exp.selected_option_id,
    reservations_n: wal.reservations?.length,
    commitments_n: wal.commitments?.length,
    offline_ready: wal.offline_ready,
  };
  /* the frame has to contain the thing under test; at scroll 0 the band sits below the fold */
  await page.getByTestId("pretrip-checklist").scrollIntoViewIfNeeded();
  await page.waitForTimeout(300);
  await page.screenshot({ path: evidencePath(`ord0384/${RUN}__X1_today.png`) });
  expect(missing, node(arm, `the response states conditions with no item on screen: ${JSON.stringify(missing)} (rendered ${JSON.stringify(keys)})`)).toEqual([]);
  expect(invented, node(arm, `the screen lists items the response does not support: ${JSON.stringify(invented)} (truth table ${JSON.stringify(expected)})`)).toEqual([]);
  expect(settledKeys.length, node(arm, "the checklist rendered nothing at all, which makes both comparisons above vacuous")).toBeGreaterThan(0);
});

/* ------------------------------------------------------------------ X2: fields change, items follow */

test("X2_a_field_appears_its_item_appears_the_field_clears_its_item_goes — 字段造出来条目就出现，字段清掉条目就消失（不靠勾选）", async ({ page }) => {
  test.setTimeout(300_000);
  const arm = "X2";
  const id = await stageJourneyId(page);

  /* Phase 1 -- make the server say three things are outstanding. The fixture's own state is not
     assumed: the first version of this cell required the demo journey to arrive with an undeclared
     budget, and on this stack it does not (X1 proved the panel agrees with it either way). */
  await page.route("**/api/v1/journeys/**", patchLegs(id, NO_CLEAN_EXP, NO_CLEAN_WAL));
  await boot(page, id);
  await settleJourney(page, id);
  await expectKeysInclude(
    page,
    ["stay_budget_undeclared", "plan_feasibility_open", "stay_chosen_but_unconfirmed"],
    arm,
  );
  const raised = await renderedKeys(page);
  const raisedTruth = await truthPair(page, id);
  readings[arm] = {
    journey_id: id,
    keys_raised: raised,
    patched_declared: raisedTruth.exp.trip?.stay_budget?.declared,
    patched_failures: raisedTruth.exp.experience_flags?.feasibility_failures,
    patched_reservations: raisedTruth.wal.reservations?.length,
    patched_commitments: raisedTruth.wal.commitments?.length,
  };
  expect(raised.includes("stay_budget_undeclared"), node(arm, `the response says the budget is undeclared and the list does not show it (${JSON.stringify(raised)})`)).toBe(true);
  expect(raised.includes("plan_feasibility_open"), node(arm, `the response lists a feasibility failure and the list does not show it (${JSON.stringify(raised)})`)).toBe(true);
  expect(raised.includes("stay_chosen_but_unconfirmed"), node(arm, `both wallet lists are empty with a stay selected and the list does not show it (${JSON.stringify(raised)})`)).toBe(true);
  await page.screenshot({ path: evidencePath(`ord0384/${RUN}__X2_raised.png`) });

  /* Phase 2 -- clear those same fields. Nothing was clicked on the panel: there is no control to click.
     If the items survive, "done" is being carried somewhere other than the truth. */
  await page.unroute("**/api/v1/journeys/**");
  await page.route("**/api/v1/journeys/**", patchLegs(id, CLEAN_EXP, CLEAN_WAL));
  await settleJourney(page, id);
  const three = ["stay_budget_undeclared", "plan_feasibility_open", "stay_chosen_but_unconfirmed"];
  await expectKeysExclude(page, three, arm);
  const cleared = await renderedKeys(page);
  const clearedTruth = await truthPair(page, id);
  (readings[arm] as Record<string, unknown>).keys_cleared = cleared;
  (readings[arm] as Record<string, unknown>).cleared_declared = clearedTruth.exp.trip?.stay_budget?.declared;
  (readings[arm] as Record<string, unknown>).cleared_failures = clearedTruth.exp.experience_flags?.feasibility_failures;
  (readings[arm] as Record<string, unknown>).cleared_commitments = clearedTruth.wal.commitments?.length;
  await page.screenshot({ path: evidencePath(`ord0384/${RUN}__X2_cleared.png`) });
  /* and back once more, so the direction is shown to be the field and not the reload */
  await page.unroute("**/api/v1/journeys/**");
  await page.route("**/api/v1/journeys/**", patchLegs(id, NO_CLEAN_EXP, NO_CLEAN_WAL));
  await settleJourney(page, id);
  await expectKeysInclude(page, ["stay_budget_undeclared"], arm);
  const again = await renderedKeys(page);
  (readings[arm] as Record<string, unknown>).keys_again = again;
  expect(again.includes("stay_budget_undeclared"), node(arm, `the item did not return when the field went back (${JSON.stringify(again)})`)).toBe(true);
});

/* ------------------------------------------------------------------ X3: the clean case stays honest */

test("X3_a_clean_response_gives_no_items_one_honest_line_and_a_strikable_action — 全干净时：0 条目、一句实话、一个打得开的动作", async ({ page }) => {
  test.setTimeout(300_000);
  const arm = "X3";
  const id = await stageJourneyId(page);
  await page.route("**/api/v1/journeys/**", patchLegs(id, CLEAN_EXP, CLEAN_WAL));
  await boot(page, id);
  await settleJourney(page, id);
  const keys = await renderedKeys(page);
  const empty = page.getByTestId("pretrip-empty");
  await expect(empty, node(arm, "a clean response produced no empty-state line, so the band would be a silent hole")).toBeVisible();
  const action = page.getByTestId("pretrip-empty-action");
  await expect(action, node(arm, "the empty state carries no action -- 「暂无数据」 with nowhere to go is the shape this order forbids")).toBeVisible();
  const emptyText = (await empty.textContent() ?? "").trim();
  /* Bring it into view BEFORE the strike test: an action below the fold answers no `elementFromPoint`,
     and that is a fact about the viewport, not about whether a traveller can reach it. */
  await action.scrollIntoViewIfNeeded();
  await page.waitForTimeout(300);
  const hits = await surveyName(page, "去看方案");
  const kept = strikeableOnly(hits);
  const box = await action.boundingBox();
  readings[arm] = {
    journey_id: id,
    rendered_keys: keys,
    item_count: keys.length,
    empty_text: emptyText,
    action_box: box,
    action_strikeable_buttons: kept.length,
    claims_all_checked: /全部通过|一切正常|已确认无误|all checked/.test(emptyText),
  };
  await page.screenshot({ path: evidencePath(`ord0384/${RUN}__X3_empty.png`) });
  expect(keys.length, node(arm, `a clean response still listed items: ${JSON.stringify(keys)} -- at least one rule is not reading its field`)).toBe(0);
  expect(box && box.width > 0 && box.height > 0, node(arm, `the empty-state action has no box (${JSON.stringify(box)})`)).toBe(true);
  expect(kept.length, node(arm, "the empty-state action is in the DOM but nothing can strike it")).toBeGreaterThan(0);
  expect(emptyText.length > 0, node(arm, "the empty line says nothing at all")).toBe(true);
  expect((readings[arm] as Record<string, unknown>).claims_all_checked, node(arm, `the empty line claims a verdict it did not earn (${emptyText}) -- an empty list is not "all clear"`)).toBe(false);
});

/* ------------------------------------------------------------------ X4: basis on screen, nothing raw */

test("X4_every_item_names_its_endpoint_and_field_on_screen_and_no_raw_reading_reaches_the_dom — 每条都在屏上写出端点与字段，且没有网络原文或夹带文案", async ({ page }) => {
  test.setTimeout(300_000);
  const arm = "X4";
  const id = await stageJourneyId(page);
  await boot(page, id);
  await settleJourney(page, id);
  const truth = await truthPair(page, id);
  const expected = Object.entries(TRUTH).filter(([, holds]) => holds(truth.exp, truth.wal)).map(([k]) => k);
  /* A response arriving is not a screen re-rendering. Poll until the panel shows what the response
     supports, then judge what is on screen -- the first version read once and called the gap
     "no items rendered", which was my race, not the product's. */
  await expect
    .poll(() => renderedKeys(page), { message: node(arm, `the panel never settled on ${JSON.stringify(expected)}`), timeout: 20_000 })
    .toEqual(expect.arrayContaining(expected));
  const items = page.locator('[data-testid="pretrip-item"]');
  const count = await items.count();
  expect(count, node(arm, `no items rendered although the response supports ${JSON.stringify(expected)}`)).toBe(expected.length);
  const perItem: Array<Record<string, unknown>> = [];
  for (let i = 0; i < count; i += 1) {
    const el = items.nth(i);
    const text = (await el.textContent() ?? "").replace(/\s+/g, " ").trim();
    /* "The text is in the DOM" is not "the traveller can read it" -- that is the ORD-0373 lesson, and
       the 依据 line is the one place this order promises an endpoint name. So judge it where a reader
       would put it: centred in the viewport, sampled across the line, and whatever is on top there
       must be this panel. The global Copilot dock floats over the lower right of Today, so a basis
       line that only clears at one scroll offset is not enough. */
    const occ = await page.evaluate((idx) => {
      const it = (document.querySelectorAll('[data-testid="pretrip-item"]') as NodeListOf<HTMLElement>)[idx];
      if (!it) return { error: "item vanished" };
      const code = it.querySelector('[data-cnx-field="basis_endpoint"]') as HTMLElement | null;
      if (!code) return { error: "no basis element" };
      code.scrollIntoView({ block: "center" });
      const r = code.getBoundingClientRect();
      const panel = document.querySelector(".cn-pretrip");
      const covered: string[] = [];
      for (const f of [0.08, 0.3, 0.5, 0.7, 0.92]) {
        const x = r.left + r.width * f;
        const y = r.top + r.height / 2;
        const top = (document.elementsFromPoint(x, y) as HTMLElement[])[0];
        const mine = !!top && (top === panel || (!!panel && panel.contains(top)));
        if (!mine) covered.push(`${x.toFixed(0)},${y.toFixed(0)}:${top ? top.tagName.toLowerCase() + "." + String(top.className).slice(0, 40) : "none"}`);
      }
      return {
        rect: { x: Math.round(r.x), y: Math.round(r.y), w: Math.round(r.width), h: Math.round(r.height) },
        viewport: { w: window.innerWidth, h: window.innerHeight },
        covered_points: covered,
      };
    }, i);
    perItem.push({
      key: (await el.getAttribute("data-cnx-key")) ?? "?",
      names_endpoint: text.includes("/api/v1/journeys/"),
      text_length: text.length,
      goto_strikable: (await el.locator('[data-testid^="pretrip-goto-"]').count()) > 0,
      basis_occlusion: occ,
    });
    expect(occ.covered_points ?? ["unmeasured"], node(arm, `the endpoint name of item ${JSON.stringify((await el.getAttribute("data-cnx-key")) ?? "?")} is covered at the reading position by ${JSON.stringify(occ.covered_points)}`)).toEqual([]);
  }
  const dom = await page.evaluate(() => {
    /* Scoped to this panel: a whole-page sweep would let another lane's text decide whether ORD-0384
       passes, and would fail for reasons this order neither owns nor can fix. The page-wide counts are
       still recorded, just not asserted. */
    const panel = document.querySelector(".cn-pretrip") ?? document.body;
    /* the element itself carries a hook too, and querySelectorAll does not return the root */
    const inPanel = (root: Element) => [root, ...Array.from(root.querySelectorAll("*"))];
    const pairs = inPanel(panel).flatMap((el) =>
      Array.from(el.attributes).filter((a) => a.name.startsWith("data-") || a.name.startsWith("aria-")).map((a) => `${el.tagName.toLowerCase()}|${a.name}|${a.value}`),
    );
    const body = document.body.textContent ?? "";
    const panelText = panel.textContent ?? "";
    const allPairs = Array.from(document.querySelectorAll("*")).flatMap((el) =>
      Array.from(el.attributes).filter((a) => a.name.startsWith("data-") || a.name.startsWith("aria-")).map((a) => `${el.tagName.toLowerCase()}|${a.name}|${a.value}`),
    );
    const q64 = ["http_status", "content_type", "body_bytes", "response_received", "elapsed_ms", "request_id"];
    return {
      pairs: pairs.length,
      page_pairs: allPairs.length,
      q64_in_panel: q64.filter((f) => panelText.includes(f)),
      q64_on_whole_page: q64.filter((f) => body.includes(f)),
      cnx_field_values: pairs.filter((p) => p.includes("|data-cnx-field|")).map((p) => p.split("|")[2]),
    };
  });
  readings[arm] = { journey_id: id, items: perItem, ...dom };
  for (const it of perItem) {
    expect(it.names_endpoint, node(arm, `item ${JSON.stringify(it.key)} does not state which endpoint its field came from (${JSON.stringify(it)})`)).toBe(true);
    expect(it.goto_strikable, node(arm, `item ${JSON.stringify(it.key)} has no way to go and handle it`)).toBe(true);
  }
  expect(dom.q64_in_panel, node(arm, `raw network readings inside the panel: ${JSON.stringify(dom.q64_in_panel)}`)).toEqual([]);
  /* Q70: a data-cnx-field hook names a contract field and nothing else -- no sentence, no value. */
  const sentences = dom.cnx_field_values.filter((v) => v.includes("：") || v.includes(" ") || /[，。]/.test(v));
  expect(sentences, node(arm, `data-cnx-field holds more than a field name: ${JSON.stringify(sentences)}`)).toEqual([]);
  expect(dom.cnx_field_values.length, node(arm, `the panel exposes ${String(dom.cnx_field_values.length)} contract hooks, expected at least the three this order names`)).toBeGreaterThanOrEqual(3);
});

/* ------------------------------------------------- X5: the all-clear line must not deny the list */

test("X5_the_all_clear_line_never_sits_under_an_open_list — 「一切正常」不能印在还差这些的清单下面", async ({ page }) => {
  test.setTimeout(300_000);
  const arm = "X5";
  const id = await stageJourneyId(page);
  await boot(page, id);
  await settleJourney(page, id);
  /* The premise only exists when the panel actually has something open and the band is clear. Without
     items the ordering claim is vacuously true, so the cell would pass on an empty screen. */
  await expect
    .poll(() => renderedKeys(page), { message: node(arm, "the checklist never rendered an item"), timeout: 20_000 })
    .not.toHaveLength(0);
  const keys = await renderedKeys(page);
  const bandState = await page.evaluate(() => {
    const band = document.querySelector('[data-testid="today-attention-band"]');
    const strong = document.querySelector('[data-testid="today-attention"]');
    const kicker = document.querySelector('.cn-attention-band .cn-attention-head .v8-kicker');
    const panel = document.querySelector('[data-testid="pretrip-checklist"]');
    const rect = (el: Element | null) => {
      if (!el) return null;
      const r = (el as HTMLElement).getBoundingClientRect();
      return { top: Math.round(r.top + window.scrollY), bottom: Math.round(r.bottom + window.scrollY) };
    };
    return {
      band_attention: band?.getAttribute("data-attention") ?? null,
      band_text: strong ? (strong.textContent ?? "").trim() : null,
      band_kicker_visible: !!kicker && (kicker as HTMLElement).offsetParent !== null,
      band_rect: rect(band),
      panel_rect: rect(panel),
      panel_items: document.querySelectorAll('[data-testid="pretrip-checklist"] [data-cnx-key]').length,
    };
  });
  readings[arm] = { journey_id: id, rendered_keys: keys, ...bandState };
  await page.locator('[data-testid="today-attention-band"]').screenshot({ path: evidencePath(`ord0384/${RUN}__X5_band.png`) }).catch(() => undefined);
  await page.getByTestId("pretrip-checklist").scrollIntoViewIfNeeded();
  await page.waitForTimeout(250);
  await page.screenshot({ path: evidencePath(`ord0384/${RUN}__X5_pair.png`) });

  expect(bandState.band_rect, node(arm, "the attention band is not on the screen at all, so this cell proves nothing")).not.toBeNull();
  expect(bandState.panel_rect, node(arm, "the checklist panel is not on the screen at all, so this cell proves nothing")).not.toBeNull();
  expect(bandState.panel_items, node(arm, `the checklist rendered ${String(bandState.panel_items)} items -- an empty list cannot be contradicted, so order is untestable here`)).toBeGreaterThan(0);
  expect(bandState.band_attention, node(arm, `the band reads ${JSON.stringify(bandState.band_attention)}, not the clear state this cell is about`)).toBe("clear");
  /* The reason ordering is load-bearing: the clear state hides the band's own subject. */
  expect(bandState.band_kicker_visible, node(arm, "the clear band now shows its kicker, so the premise of this cell changed -- re-read it before trusting the verdict")).toBe(false);
  expect(
    bandState.band_rect!.bottom <= bandState.panel_rect!.top,
    node(arm, `the bare all-clear "${bandState.band_text}" renders at y=${String(bandState.band_rect!.top)}–${String(bandState.band_rect!.bottom)}, i.e. below the ${String(bandState.panel_items)} open items that end at y=${String(bandState.panel_rect!.bottom)} -- one screen, two answers`),
  ).toBe(true);
});
