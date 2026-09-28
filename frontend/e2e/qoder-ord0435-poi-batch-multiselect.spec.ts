/**
 * ORD-0435 -- a POI batch has to be selectable, countable, and written somewhere real.
 *
 * The order borrowed four checkpoints from the reference app's map findings
 * (`_apk_analysis_pi_travel/MAP/map_findings.md:150`) and one pairing rule: a selection set must
 * carry a count, it must name a target container, an empty set must land on an empty state rather
 * than a dead end, 完成 must sit beside 新建 so finishing one batch always opens the next, and every
 * selected state needs its unselected twin.
 *
 * The red line is the order's own: no client state may pretend a place was added. So Q4 does not
 * stop at the screen -- it takes the plan identity the screen printed and asks the route for that
 * plan again, and Q5 proves the refusal path cannot be mistaken for success by anyone reading the
 * screen.
 *
 * Every arm first proves the result cards are actually on screen. That is not ceremony: this lane's
 * first before-read counted zeros on the onboarding wizard, its second counted them on a loading
 * spinner, and in both cases the zeros looked exactly like the finding.
 */
import { expect, test } from "@playwright/test";
import { writeFileSync } from "node:fs";
import { evidencePath } from "./_qoderEvidence";

const FILE = "e2e/qoder-ord0435-poi-batch-multiselect.spec.ts";
const node = (id: string, detail: string) => `${FILE} :: ${id} — ${detail}`;
const RUN = process.env.CITYNEXUS_E2E_RUN_ID ?? "local";

const TICK = '[data-testid="v13-pick-candidate"]';
const CARDS = "article.v8-stay-card";
const COUNT = '[data-testid="v13-discovery-picked-count"]';
const TARGET = '[data-testid="v13-discovery-batch-target"]';
const EMPTY = '[data-testid="v13-discovery-batch-empty"]';
const NOTE = '[data-testid="v13-discovery-batch-note"]';
const FINISH = '[data-testid="v13-discovery-finish-batch"]';
const FRESH = '[data-testid="v13-discovery-new-batch"]';
const RECEIPT = '[data-testid="v13-discovery-batch-receipt"]';
const ROW = '[data-testid="v13-discovery-batch-row"]';
const PLAN_LINE = ".v8-batch-receipt-plan";
const BATCH_ERROR = '[data-testid="v13-discovery-batch-error"]';
const TECHNICAL = '[data-testid="v13-discovery-batch-technical"]';

const readings: Record<string, unknown> = {};
test.afterEach(({}, info) => {
  const arm = /^([QR]\d)/.exec(info.title)?.[1] ?? info.title.slice(0, 2);
  const prior = (readings[arm] ?? {}) as Record<string, unknown>;
  const body: Record<string, unknown> = { ...prior };
  body.nodeid = `${info.file}:${info.line} > ${info.title}`;
  body.test_status = info.status;
  if (info.status !== "passed") {
    body.error_head = String(info.error?.message ?? "").replace(/\s+/g, " ").slice(0, 700);
  }
  writeFileSync(
    evidencePath(`ord0435/${RUN}__${arm}.json`),
    JSON.stringify({ run_id: RUN, arm, spec: FILE, ...body }, null, 1),
    "utf-8",
  );
});

/**
 * Drive the console to a real result set in the language of this arm.
 *
 * The journey is asked for from the stage first (`GET /api/v1/demo/scene`, read-only), and only if
 * the stage holds none does this fall back to seeding one through `POST /api/v1/demo/reset`. That
 * order is not politeness: since ORD-0389 the reset door requires `X-Demo-Reset-Token` to match
 * `CITYNEXUS_DEMO_RESET_TOKEN`, and nothing in this suite supplies it — so a spec that reaches for
 * reset first dies on a 403 before it has measured anything (measured here: `http 403` on the very
 * first attempt at this boot). The fallback is kept because a run that *did* configure the token
 * should still be able to seed, and `seed_route` in the reading says which one happened.
 *
 * Two further things are load-bearing. The journey id is read from the stage rather than hardcoded,
 * because a stored id that no longer exists renders an error screen and the arm would then be
 * measuring nothing. And the mode is switched to the synthetic-demo leg on purpose: the console's
 * own default asks for a fully-grounded evidence pair and answers `
 * V13_FULL_GROUNDING_MISSING_MOBILITY_PAIR` without one -- a real refusal, but one that leaves no
 * cards to tick.
 */
async function openConsole(page: import("@playwright/test").Page, locale: "zh-CN" | "en") {
  let journeyId = "";
  let seedRoute = "GET /api/v1/demo/scene";
  const scene = await page.request.get("/api/v1/demo/scene");
  const sceneStatus = scene.status();
  if (sceneStatus === 200) journeyId = String(((await scene.json()) as { journey_id?: string }).journey_id ?? "");
  if (journeyId.length < 8) {
    seedRoute = "POST /api/v1/demo/reset";
    const token = process.env.CITYNEXUS_DEMO_RESET_TOKEN;
    const seeded = await page.request.post("/api/v1/demo/reset", {
      headers: token ? { "X-Demo-Reset-Token": token } : {},
    });
    expect(
      seeded.status(),
      node(
        "boot",
        `the stage held no journey (scene http ${sceneStatus}) and seeding one answered ${seeded.status()} -- ` +
          "reset is gated behind CITYNEXUS_DEMO_RESET_TOKEN since ORD-0389",
      ),
    ).toBe(200);
    journeyId = String(((await seeded.json()) as { journey_id?: string }).journey_id ?? "");
  }
  expect(journeyId.length > 8, node("boot", "the stage named no journey, so there is no console to open")).toBe(true);

  await page.addInitScript((seed) => {
    localStorage.clear();
    localStorage.setItem("citynexus.locale", seed.locale);
    localStorage.setItem("citynexus.v8.journey_id", seed.journey);
  }, { locale, journey: journeyId });

  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/v8/hub", { waitUntil: "load" });
  await expect(page.getByTestId("today-hero"), node("boot", `Today never rendered in ${locale}`)).toBeVisible({
    timeout: 30_000,
  });
  await page.goto("/v8/discover", { waitUntil: "load" });
  await expect(page.getByTestId("v13-discovery-goal"), node("boot", "the discovery console never mounted")).toBeVisible({
    timeout: 30_000,
  });

  const statuses: number[] = [];
  page.on("response", (res) => {
    if (res.url().includes("authoritative-compose")) statuses.push(res.status());
  });

  await page.locator('select[aria-label]').first().selectOption("replay");
  await page.getByTestId("v13-discover-submit").click();
  await expect(page.getByTestId("v13-discovery-result"), node("boot", "the console answered with no result block")).toBeVisible({
    timeout: 60_000,
  });
  await expect
    .poll(async () => await page.locator(CARDS).count(), {
      message: node("boot", "no result card rendered, so every count below would be a count of nothing"),
      timeout: 30_000,
    })
    .toBeGreaterThan(0);

  const cards = await page.locator(CARDS).count();
  return { journeyId, cards, composeStatuses: statuses, seed_route: seedRoute, scene_status: sceneStatus };
}

test("Q1_the_tick_is_its_own_state_and_not_the_feasibility_class — 勾选态与「合格」是两回事，不许共用同一个类", async ({ page }) => {
  test.setTimeout(240_000);
  const arm = "Q1";
  const boot = await openConsole(page, "zh-CN");
  const feasibilityBefore = await page.locator(`${CARDS}.selected`).count();
  const ticks = await page.locator(TICK).count();
  const unchecked = await page.locator(`${TICK}[aria-checked="false"]`).count();
  const checked = await page.locator(`${TICK}[aria-checked="true"]`).count();
  const unpickedCards = await page.locator(`${CARDS}[data-picked="false"]`).count();

  await page.locator(TICK).first().click();
  await page.waitForTimeout(300);
  const after = {
    checked: await page.locator(`${TICK}[aria-checked="true"]`).count(),
    feasibility: await page.locator(`${CARDS}.selected`).count(),
    pickedCards: await page.locator(`${CARDS}[data-picked="true"]`).count(),
  };
  await page.locator(TICK).first().click();
  await page.waitForTimeout(300);
  const backAgain = await page.locator(`${TICK}[aria-checked="false"]`).count();

  /* The tick has to fit beside the name it belongs to. `src/styles.css:47` is a bare
     `button { display: block; width: 100%; margin-top: 12px }`, and a class that overrides only
     `display` inherits that width: measured at 272 px inside a 358 px card, the control took 76 % of
     the card and pushed the place name into a column next to the eligibility badge. These two
     numbers are the regression guard for that, and they are read from the same layout the traveller
     sees -- not from the stylesheet. */
  const squeeze = await page.locator(CARDS).first().evaluate((card) => {
    const h3 = card.querySelector("h3");
    const badge = card.querySelector(".v8-selected-label");
    const tick = card.querySelector('[data-testid="v13-pick-candidate"]');
    if (!h3 || !badge || !tick) return { error: "MISSING_PARTS" };
    const a = h3.getBoundingClientRect();
    const b = badge.getBoundingClientRect();
    const t = tick.getBoundingClientRect();
    const c = card.getBoundingClientRect();
    const wide = Math.min(a.right, b.right) - Math.max(a.left, b.left);
    const tall = Math.min(a.bottom, b.bottom) - Math.max(a.top, b.top);
    return {
      card_width: Math.round(c.width),
      tick_width: Math.round(t.width),
      tick_share_pct: Math.round((t.width / c.width) * 100),
      name_badge_overlap_area: wide > 0 && tall > 0 ? Math.round(wide * tall) : 0,
      name_line_boxes: h3.getClientRects().length,
    };
  });
  await page.screenshot({ path: evidencePath(`ord0435/${RUN}__Q1.png`), fullPage: true });

  readings[arm] = {
    cards: boot.cards,
    seed_route: boot.seed_route,
    scene_status: boot.scene_status,
    feasibility_before: feasibilityBefore,
    ticks,
    unchecked,
    checked_at_start: checked,
    cards_unpicked_at_start: unpickedCards,
    after_one_tick: after,
    unchecked_after_untick: backAgain,
    squeeze,
  };

  expect(boot.cards, node(arm, "no result card reached the screen")).toBeGreaterThan(0);
  /* One control per card, and both twins present from the first paint: a state that only ever exists
     in one direction is the defect this order names, not a style choice. */
  expect(ticks, node(arm, `${ticks} tick controls for ${boot.cards} cards -- a card without a tick cannot join a batch`)).toBe(boot.cards);
  expect(unchecked, node(arm, `${unchecked} of ${boot.cards} ticks did not answer in the unselected twin`)).toBe(boot.cards);
  expect(checked, node(arm, `${checked} cards arrived already ticked; the batch must start empty`)).toBe(0);
  expect(unpickedCards, node(arm, `only ${unpickedCards} of ${boot.cards} cards carried data-picked="false" -- the unselected twin is missing on the card itself`)).toBe(boot.cards);
  expect(after.checked, node(arm, "the tick did not move to its selected twin")).toBe(1);
  expect(after.pickedCards, node(arm, "the card's own data-picked did not follow its tick")).toBe(1);
  /* `.selected` is the server's verdict on the place. If a tick could change it, no instrument could
     tell "the traveller chose this" from "this place passed the gate" again. */
  expect(after.feasibility, node(arm, `the feasibility class moved from ${feasibilityBefore} to ${after.feasibility} on a tick -- the two states are not independent`)).toBe(feasibilityBefore);
  expect(backAgain, node(arm, "unticking did not return the control to its unselected twin")).toBe(boot.cards);
  /* The layout guard for the `styles.css:47` inheritance trap described above: a tick that eats the
     card is as unusable as a tick that is missing, and only the second one shows up in a count. */
  const sq = squeeze as { card_width?: number; tick_share_pct?: number; name_badge_overlap_area?: number };
  expect(sq.card_width, node(arm, `the card could not be measured (${JSON.stringify(squeeze)})`)).toBeGreaterThan(0);
  expect(sq.name_badge_overlap_area, node(arm, `the place name and the eligibility badge overlap by ${sq.name_badge_overlap_area} px2 -- the tick has taken their row`)).toBe(0);
  expect(sq.tick_share_pct, node(arm, `the tick takes ${sq.tick_share_pct}% of the card width; the bare \`button { width: 100% }\` at src/styles.css:47 is winning again`)).toBeLessThan(40);
});

test("Q2_the_count_the_empty_state_and_the_twin_states_move_together — 计数、空态与成对态要一起动", async ({ page }) => {
  test.setTimeout(240_000);
  const arm = "Q2";
  const boot = await openConsole(page, "zh-CN");
  const start = {
    count: (await page.locator(COUNT).innerText()).replace(/\s+/g, " "),
    empty: await page.locator(EMPTY).count(),
    emptyText: (await page.locator(EMPTY).innerText()).replace(/\s+/g, " "),
    target: (await page.locator(TARGET).innerText()).replace(/\s+/g, " "),
    finishDisabled: await page.locator(FINISH).isDisabled(),
    note: await page.locator(NOTE).count(),
  };
  await page.locator(TICK).first().click();
  await page.waitForTimeout(300);
  const one = {
    count: (await page.locator(COUNT).innerText()).replace(/\s+/g, " "),
    empty: await page.locator(EMPTY).count(),
    note: (await page.locator(NOTE).innerText()).replace(/\s+/g, " "),
    finishDisabled: await page.locator(FINISH).isDisabled(),
  };
  await page.locator(TICK).nth(1).click();
  await page.waitForTimeout(300);
  const two = { count: (await page.locator(COUNT).innerText()).replace(/\s+/g, " ") };
  await page.locator(FRESH).click();
  await page.waitForTimeout(300);
  const cleared = {
    count: (await page.locator(COUNT).innerText()).replace(/\s+/g, " "),
    empty: await page.locator(EMPTY).count(),
    finishDisabled: await page.locator(FINISH).isDisabled(),
    checked: await page.locator(`${TICK}[aria-checked="true"]`).count(),
  };
  await page.screenshot({ path: evidencePath(`ord0435/${RUN}__Q2.png`), fullPage: true });

  readings[arm] = { cards: boot.cards, seed_route: boot.seed_route, scene_status: boot.scene_status, start, one, two, cleared };

  expect(start.count, node(arm, `an untouched batch read "${start.count}" -- the count must start at zero, not at absent`)).toContain("0");
  expect(start.empty, node(arm, "the empty batch had no empty state to land on")).toBe(1);
  expect(start.emptyText.length, node(arm, "the empty state renders no sentence, so it is not an empty state")).toBeGreaterThan(0);
  expect(start.finishDisabled, node(arm, "完成 was pressable on an empty batch -- that is the dead end the checkpoint names")).toBe(true);
  expect(start.note, node(arm, "a commitment note appeared before anything was picked")).toBe(0);
  expect(one.count, node(arm, `one tick read "${one.count}"`)).toContain("1");
  expect(one.empty, node(arm, "the empty state stayed on screen once the batch had a member")).toBe(0);
  expect(one.finishDisabled, node(arm, "完成 stayed disabled with one place picked")).toBe(false);
  /* The commitment travels with the batch because the planner refuses without it, and it is not one
     of the traveller's picks -- the count has to stay a count of ticks. */
  expect(one.note, node(arm, `the batch did not say what else travels with it (read "${one.note}")`)).toContain("承诺");
  expect(two.count, node(arm, `two ticks read "${two.count}"`)).toContain("2");
  expect(cleared.count, node(arm, `新建一批 left the batch at "${cleared.count}"`)).toContain("0");
  expect(cleared.checked, node(arm, "新建一批 left a card ticked")).toBe(0);
  expect(cleared.empty, node(arm, "新建一批 did not return the empty state")).toBe(1);
  expect(cleared.finishDisabled, node(arm, "after 新建一批, 完成 was still pressable on an empty batch")).toBe(true);
});

test("Q3_完成_and_新建_stay_in_one_band_at_every_narrow_width — 完成与新建在四个窄屏宽度同带且不重叠", async ({ page }) => {
  test.setTimeout(360_000);
  const arm = "Q3";
  const boot = await openConsole(page, "zh-CN");
  const widths: Array<readonly [number, number]> = [
    [320, 568],
    [360, 740],
    [390, 844],
    [430, 932],
  ];
  const per: Record<string, unknown> = {};
  for (const [w, h] of widths) {
    await page.setViewportSize({ width: w, height: h });
    await page.waitForTimeout(250);
    const box = async (selector: string) => {
      const found = await page.locator(selector).first().boundingBox();
      return found;
    };
    const finish = await box(FINISH);
    const fresh = await box(FRESH);
    const nav = await page.locator("nav.v8-mobile-nav").first().boundingBox();
    type Box = { x: number; y: number; width: number; height: number } | null;
    const overlap = (a: Box, b: Box) => {
      if (!a || !b) return 0;
      const wide = Math.min(a.x + a.width, b.x + b.width) - Math.max(a.x, b.x);
      const tall = Math.min(a.y + a.height, b.y + b.height) - Math.max(a.y, b.y);
      return wide > 0 && tall > 0 ? Math.round(wide * tall) : 0;
    };
    await page.locator(TICK).first().click();
    await page.waitForTimeout(200);
    const enabled = {
      finish: await page.locator(FINISH).boundingBox(),
      fresh: await page.locator(FRESH).boundingBox(),
    };
    await page.locator(TICK).first().click();
    per[`${w}x${h}`] = {
      finish,
      fresh,
      same_band:
        Boolean(finish && fresh) &&
        Math.abs(finish!.y + finish!.height / 2 - (fresh!.y + fresh!.height / 2)) <
          Math.max(finish!.height, fresh!.height),
      gap_px: finish && fresh ? Math.round(fresh!.x - (finish!.x + finish!.width)) : null,
      /* 44px is the mobile tap floor this codebase already gates on; a batch control under it is a
         control a thumb misses, which is the same failure as a missing button. */
      min_height: Math.round(Math.min(finish?.height ?? 0, fresh?.height ?? 0)),
      finish_escapes_viewport: Boolean(finish && (finish.x < 0 || finish.x + finish.width > w + 0.5)),
      covered_by_bottom_nav: overlap(finish, nav) + overlap(fresh, nav),
      pressable_finish_and_fresh_same_band:
        Boolean(enabled.finish && enabled.fresh) &&
        Math.abs(enabled.finish!.y - enabled.fresh!.y) < Math.max(enabled.finish!.height, enabled.fresh!.height),
    };
    await page.screenshot({ path: evidencePath(`ord0435/${RUN}__Q3_${w}x${h}.png`), fullPage: true });
  }
  readings[arm] = { cards: boot.cards, seed_route: boot.seed_route, scene_status: boot.scene_status, per_width: per };
  for (const [key, value] of Object.entries(per)) {
    const v = value as {
      same_band: boolean;
      pressable_finish_and_fresh_same_band: boolean;
      min_height: number;
      finish_escapes_viewport: boolean;
      covered_by_bottom_nav: number;
    };
    expect(v.same_band, node(arm, `${key}: 新建一批 is not beside 完成 -- the checkpoint exists so 完成 is never a dead end`)).toBe(true);
    expect(v.pressable_finish_and_fresh_same_band, node(arm, `${key}: the two moved apart once the batch became pressable`)).toBe(true);
    expect(v.min_height, node(arm, `${key}: a batch control is ${v.min_height}px tall, under the 44px mobile floor`)).toBeGreaterThanOrEqual(44);
    expect(v.finish_escapes_viewport, node(arm, `${key}: 完成 escapes the viewport sideways`)).toBe(false);
    expect(v.covered_by_bottom_nav, node(arm, `${key}: a batch control is covered by the fixed bottom nav`)).toBe(0);
  }
});

test("Q4_完成_writes_through_the_route_and_the_screen_shows_a_second_read — 完成走真实写路由，屏上显示的是第二次读", async ({ page, request }) => {
  test.setTimeout(360_000);
  const arm = "Q4";
  const boot = await openConsole(page, "zh-CN");
  await page.locator(TICK).first().click();
  await page.waitForTimeout(200);
  const cardName = (await page.locator(`${CARDS} h3`).first().innerText()).replace(/\s+/g, " ");
  await page.locator(FINISH).click();
  await expect(page.locator(RECEIPT), node(arm, "完成 produced no read-back block")).toBeVisible({ timeout: 60_000 });
  await page.waitForTimeout(800);

  const rows = await page.locator(ROW).allInnerTexts();
  const rowText = rows.map((v) => v.replace(/\s+/g, " "));
  const target = (await page.locator(TARGET).innerText()).replace(/\s+/g, " ");
  const planLine = (await page.locator(`${RECEIPT} ${PLAN_LINE}`).first().innerText()).replace(/\s+/g, " ");
  const planId = /([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})/.exec(planLine)?.[1] ?? null;
  const activityIds = rowText
    .map((v) => /([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})/.exec(v)?.[1] ?? null)
    .filter((v): v is string => Boolean(v));
  await page.screenshot({ path: evidencePath(`ord0435/${RUN}__Q4_written.png`), fullPage: true });

  /* The second read. Nothing below this line is the browser's memory of the POST. */
  const again = planId ? await request.get(`/api/v1/plans/${planId}`) : null;
  const payload = again ? ((await again.json()) as { status?: string; activities?: Array<{ id: string; place_id?: string | null; title: string; start_at: string }> }) : null;
  const serverRows = (payload?.activities ?? []).filter((a) => String(a.place_id ?? "").startsWith("real-place-"));
  const dayOnScreen = /(\d{4}-\d{2}-\d{2})/.exec(target)?.[1] ?? null;

  readings[arm] = {
    cards: boot.cards,
    seed_route: boot.seed_route,
    scene_status: boot.scene_status,
    card_name: cardName,
    compose_statuses: boot.composeStatuses,
    row_count: rowText.length,
    row_texts: rowText,
    target_text: target,
    plan_line: planLine,
    plan_id: planId,
    activity_ids_on_screen: activityIds,
    second_read: {
      status: again?.status() ?? null,
      plan_status: payload?.status ?? null,
      picked_rows: serverRows.map((a) => ({ id: a.id, title: a.title, start_at: a.start_at })),
    },
    day_on_screen: dayOnScreen,
  };

  expect(planId, node(arm, `the read-back block named no plan to ask for (line read "${planLine}")`)).not.toBeNull();
  expect(again?.status(), node(arm, `the second read of plan ${planId} answered ${again?.status()}`)).toBe(200);
  expect(rowText.length, node(arm, "the screen showed a receipt with no row in it")).toBeGreaterThan(0);
  /* The red line: the row the traveller can see is a row the server holds, under the same identity,
     on the same day. A client-side "已加入" would pass every assertion above and still be a lie. */
  expect(serverRows.length, node(arm, `the store holds ${serverRows.length} activity for the batch the screen showed as ${rowText.length}`)).toBe(rowText.length);
  for (const shown of activityIds) {
    expect(serverRows.some((a) => a.id === shown), node(arm, `activity ${shown} is on the screen but not in the plan the server returned`)).toBe(true);
  }
  expect(serverRows[0]?.title, node(arm, `the written row reads "${serverRows[0]?.title}", the card the traveller ticked reads "${cardName}"`)).toBe(cardName);
  expect(dayOnScreen, node(arm, `the screen did not name a day (target read "${target}")`)).not.toBeNull();
  expect(String(serverRows[0]?.start_at ?? "").startsWith(dayOnScreen ?? ""), node(arm, `the screen says ${dayOnScreen} but the row starts ${serverRows[0]?.start_at}`)).toBe(true);
  /* A batch that was written is a candidate plan, not yet the plan the journey runs. Saying
     "SELECTED" here would claim an action nobody took. */
  expect(payload?.status, node(arm, `the batch landed as ${payload?.status}; this screen's 完成 does not select a plan`)).toBe("CANDIDATE");
});

test("Q5_a_refused_batch_is_shown_as_a_refusal — 规划器拒掉的批次不许看起来像已加入", async ({ page }) => {
  test.setTimeout(360_000);
  const arm = "Q5";
  const boot = await openConsole(page, "zh-CN");
  await page.locator(TICK).nth(0).click();
  await page.locator(TICK).nth(1).click();
  await page.waitForTimeout(200);
  const countBefore = (await page.locator(COUNT).innerText()).replace(/\s+/g, " ");

  const responses: number[] = [];
  page.on("response", (res) => {
    if (res.url().includes("authoritative-compose")) responses.push(res.status());
  });
  await page.locator(FINISH).click();
  await expect(page.locator(BATCH_ERROR), node(arm, "a refused batch rendered no refusal")).toBeVisible({ timeout: 60_000 });
  await page.waitForTimeout(600);

  const errorText = (await page.locator(BATCH_ERROR).innerText()).replace(/\s+/g, " ");
  const receipt = await page.locator(RECEIPT).count();
  const technical = await page.locator(TECHNICAL).count();
  const target = (await page.locator(TARGET).innerText()).replace(/\s+/g, " ");
  await page.screenshot({ path: evidencePath(`ord0435/${RUN}__Q5_refused.png`), fullPage: true });

  readings[arm] = {
    cards: boot.cards,
    seed_route: boot.seed_route,
    scene_status: boot.scene_status,
    count_before: countBefore,
    compose_statuses: responses,
    error_text: errorText,
    receipt_blocks: receipt,
    technical_fold: technical,
    target_text: target,
  };

  expect(responses.includes(422), node(arm, `the order expected the planner's own 422 and saw ${JSON.stringify(responses)} -- the arm is not exercising the refusal it names`)).toBe(true);
  expect(errorText.length, node(arm, "the refusal rendered as an empty message")).toBeGreaterThan(0);
  expect(errorText, node(arm, `the refusal printed the answer's sentence ("${errorText}") instead of this screen's own words`)).not.toMatch(/V13_|HTTP \d{3}/);
  expect(receipt, node(arm, "a refused batch still showed a read-back receipt -- that is the fake 已加入 this order forbids")).toBe(0);
  expect(target, node(arm, `the target still claims a write after a refusal (read "${target}")`)).toContain("还没有");
  expect(technical, node(arm, "the named refusal left no measured facts behind, so nothing is diagnosable")).toBe(1);
});
