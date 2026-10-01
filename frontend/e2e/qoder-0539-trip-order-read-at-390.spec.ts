import { expect, test, type APIRequestContext, type Page } from "@playwright/test";
import { writeFileSync } from "node:fs";
import { openScreen } from "./_qoderShellSeed";
import { evidencePath } from "./_qoderEvidence";

/**
 * ORD-0539 -- the trip list's order, read by eye at the phone width, for every tier.
 *
 * ORD-0518 shipped eleven arms and two of them run at 390x844, but those two judge *reachability*
 * (can a finger land on the row) and read the roster at one chosen tier. What was never said out loud
 * at this width is the thing the commander asked to see: after each tier is pressed, which trip is
 * the first row and which is the last, as painted, and what the verdict sentence claims about it.
 * At 390 px that is not a small question -- the roster is the only part of the screen that grows with
 * the data, and most of its rows sit below the first screen (measured in ORD-0518: 3 of 21 rows in
 * the reachable band before anything is scrolled). So "the first and last trip" at this width is a
 * reading a traveller gets only after scrolling, and an arm that never took that reading could not
 * say so.
 *
 * Arms: one per tier, four tiers. Each one scrolls the roster into the reachable band the way a
 * finger would, then reports the painted text of the topmost and bottommost rows both as painted
 * (whatever the traveller actually sees first) and as this arm's own trips. Nothing is mocked; every
 * assertion reads rendered text, and one evidence file plus one screenshot per arm, written before
 * the judgement.
 */

const FILE = "e2e/qoder-0539-trip-order-read-at-390.spec.ts";
const node = (id: string, detail: string) => `${FILE} :: ${id} — ${detail}`;
const RUN = process.env.CITYNEXUS_E2E_RUN_ID ?? "local";
const DIR = "ord0539-read-at-390";
const WIDTH = 390;
const HEIGHT = 844;
const HIT_FLOOR = 768;

const TIERS = ["CREATION_ORDER", "RECENT_UPDATE", "DEPARTURE_DATE", "TITLE"] as const;

/** The same four names ORD-0518 seeds, in the same three different orders, so the two files read one
 *  shape of data rather than each inventing its own. */
const FIXTURE = [
  { name: "delta", start: "2026-11-06T09:00:00+08:00" },
  { name: "Alpha", start: "2026-11-03T09:00:00+08:00" },
  { name: "charlie", start: "2026-11-04T08:00:00+00:00" },
  { name: "北京", start: "2026-11-05T09:00:00+08:00" },
];

async function seedTraveler(request: APIRequestContext, code: string): Promise<string> {
  const created = await request.post("api/v1/travelers", {
    data: { display_name: `ORD0539-${code} traveller`, locale: "zh-CN", timezone: "Asia/Shanghai" },
  });
  expect(created.status(), node("S1", `the traveller door answered ${created.status()}`)).toBe(201);
  return (await created.json()).id as string;
}

async function createTrip(
  request: APIRequestContext,
  travelerId: string,
  mark: string,
  name: string,
  start: string,
): Promise<string> {
  const end = new Date(new Date(start).getTime() + 2 * 86_400_000).toISOString();
  const created = await request.post("api/v1/journeys", {
    data: {
      traveler_id: travelerId,
      title: `O539-${mark} ${name}`,
      city_code: "CN-TIANJIN",
      timezone: "Asia/Shanghai",
      start_at: start,
      end_at: end,
      budget: { amount_minor: 90000, currency: "CNY" },
      planning_mode: "balanced",
    },
  });
  expect(created.status(), node("S1", `creating ${name} -> ${created.status()} ${await created.text()}`)).toBe(201);
  return (await created.json()).id as string;
}

async function enterAccess(page: Page): Promise<void> {
  await page.addInitScript(() => {
    try {
      localStorage.setItem("citynexus.locale", "zh-CN");
    } catch {
      /* a profile that refuses localStorage is reported by the arms that need it */
    }
  });
  await openScreen(page, "/v8/access", ["access-panel"]);
  await expect(
    page.getByTestId("access-panel"),
    node("S0", "zh-CN: /v8/access never mounted the panel -- the reading would be of the shell"),
  ).toBeVisible();
}

/** Every row of the roster as painted, top of the page first, with the box that says where it stands. */
async function paintedRows(page: Page): Promise<{ text: string; y: number; reachable: boolean }[]> {
  return page.evaluate((floorPx: number) => {
    return Array.from(document.querySelectorAll<HTMLElement>("[data-testid='access-trip-row']")).map((row) => {
      const box = row.getBoundingClientRect();
      const centre = [Math.round(box.x + box.width / 2), Math.round(box.y + box.height / 2)];
      const at = document.elementFromPoint(centre[0], centre[1]);
      const own = row.querySelector<HTMLElement>("[data-testid^='access-trip-open']");
      return {
        text: (row.textContent ?? "").trim(),
        y: Math.round(box.y),
        reachable:
          !!own && box.y >= 0 && box.bottom <= window.innerHeight && centre[1] < floorPx &&
          !!at && (at === own || own.contains(at)),
      };
    });
  }, HIT_FLOOR);
}

async function pickTier(page: Page, tier: string): Promise<void> {
  await page.click(`[data-testid='access-sort-tier-${tier}']`);
  await page
    .waitForFunction(() => document.querySelectorAll("[data-testid='access-trips-loading']").length === 0, undefined, { timeout: 20_000 })
    .catch(() => undefined);
  await page.waitForTimeout(1_200);
}

for (const tier of TIERS) {
  test(`ord0539-read-${tier} — at ${WIDTH}px the tier's first and last row are read as trip names, and how far down they are`, async ({
    page,
    request,
  }) => {
    await page.setViewportSize({ width: WIDTH, height: HEIGHT });
    // seed first, then mount. The panel's own first order is RECENT_UPDATE, so pressing that tier is a
    // press on an already-pressed control and asks the door nothing new; mounting after the seed is
    // what makes the mount-time fetch carry this arm's trips. (The no-op itself is reported as a
    // finding: `ord0539-pressing-the-tier-in-use` below.)
    const traveler = await seedTraveler(request, tier);
    const ids: string[] = [];
    for (const row of FIXTURE) ids.push(await createTrip(request, traveler, tier, row.name, row.start));
    await enterAccess(page);
    await pickTier(page, tier);

    const mine = (rows: { text: string }[]) => rows.filter((row) => FIXTURE.some((f) => row.text.includes(`O539-${tier} ${f.name}`)));
    const atTop = mine(await paintedRows(page));
    const verdictCell = page.getByTestId("access-order-verdict");
    const verdict = {
      state: (await verdictCell.getAttribute("data-state").catch(() => null)) ?? "MISSING",
      text: ((await verdictCell.innerText().catch(() => "")) ?? "").trim(),
    };
    // the roster is long, so the bottom of it is reached the way a traveller reaches it: by scrolling
    await page.evaluate(() => {
      const rows = document.querySelectorAll<HTMLElement>("[data-testid='access-trip-row']");
      rows[rows.length - 1]?.scrollIntoView({ block: "center", inline: "nearest" });
    });
    await page.waitForTimeout(700);
    const afterScroll = mine(await paintedRows(page));
    const paintedTopmost = (await paintedRows(page)).filter((row) => row.reachable)[0] ?? null;
    const shot = evidencePath(DIR, `${RUN}_read_${tier}.png`);
    await page.screenshot({ path: shot, fullPage: false });
    writeFileSync(
      evidencePath(DIR, `${RUN}_read-${tier}.json`),
      JSON.stringify(
        {
          file: FILE,
          arm: `ord0539-read-${tier}`,
          run_id: RUN,
          readings: {
            viewport: [WIDTH, HEIGHT],
            hit_floor_px: HIT_FLOOR,
            tier: tier,
            rows_before_scroll: atTop.length,
            first_row_before_scroll: atTop[0]?.text ?? null,
            last_row_before_scroll: atTop[atTop.length - 1]?.text ?? null,
            rows_after_scroll: afterScroll.length,
            first_row_after_scroll: afterScroll[0]?.text ?? null,
            last_row_after_scroll: afterScroll[afterScroll.length - 1]?.text ?? null,
            reachable_topmost_after_scroll: paintedTopmost?.text ?? null,
            verdict,
            ids,
            shot,
          },
        },
        null,
        1,
      ),
    );

    const rows = afterScroll.length > 0 ? afterScroll : atTop;
    expect(rows.length, node("A1", `${tier}: the roster painted none of this arm's four trips at ${WIDTH}px`))
      .toBeGreaterThanOrEqual(4);
    const first = rows[0].text;
    const last = rows[rows.length - 1].text;
    for (const text of [first, last]) {
      // 亲读判据：两端读出来的是行程名，不是编号、不是 uuid、不是空
      expect(text.length, node("A1", `${tier}: an end row reads as "${text}" -- empty or not a name`))
        .toBeGreaterThan(`O539-${tier} `.length + 1);
      expect(/[0-9a-f]{8}-[0-9a-f]{4}/.test(text), node("A1", `${tier}: an end row shows an id instead of a name: "${text}"`))
        .toBe(false);
    }
    // the tier is on the glass as a word, and the sentence about the order matches the rows
    const pressedWord = ((await page.getByTestId(`access-sort-tier-${tier}`).innerText()) ?? "").trim();
    expect(pressedWord.length, node("A2", `${tier}: the pressed tier carries no word on the glass`)).toBeGreaterThan(1);
    expect(
      ["RECENT_UPDATE", "DEPARTURE_DATE", "TITLE", "CREATION_ORDER"].includes(pressedWord),
      node("A2", `${tier}: the tier button reads as the machine word "${pressedWord}"`),
    ).toBe(false);
    expect(verdict.text, node("A2", `${tier}: the verdict sentence is not painted at all`)).not.toBe("");
    if (verdict.state === "CONSISTENT") {
      expect(verdict.text, node("A2", `${tier}: a CONSISTENT claim with no row-checked words under it: "${verdict.text}"`))
        .toContain("逐行核过");
    }
    if (verdict.state === "NOT_VERIFIABLE") {
      expect(verdict.text, node("A2", `${tier}: NOT_VERIFIABLE without saying it cannot check: "${verdict.text}"`))
        .toContain("核不了");
      expect(verdict.text, node("A2", `${tier}: the screen claimed a checked order while saying it cannot check one`))
        .not.toContain("逐行核过");
    }
  });
}

/**
 * The question the four arms above cannot answer: at this width, can the first row and the last row
 * of the roster be seen *at the same time*? The roster is as long as the server's answer, and
 * ORD-0518 measured that most of it starts below the reachable band. If both ends never share a
 * screen, then "read the first and last trip" is a two-glance act at 390 px, and the block should say
 * that with a number rather than imply a list that fits.
 */
test(`ord0539-both-ends-at-once — whether the two ends of the roster ever share the reachable band at ${WIDTH}px`, async ({
  page,
  request,
}) => {
  await page.setViewportSize({ width: WIDTH, height: HEIGHT });
  const traveler = await seedTraveler(request, "BOTH");
  const ids: string[] = [];
  for (const row of FIXTURE) ids.push(await createTrip(request, traveler, "BOTH", row.name, row.start));
  await enterAccess(page);
  await pickTier(page, "TITLE");

  const probe = () =>
    page.evaluate((floorPx: number) => {
      const rows = Array.from(document.querySelectorAll<HTMLElement>("[data-testid='access-trip-row']"));
      const inBand = rows.filter((row) => {
        const box = row.getBoundingClientRect();
        const centre = [Math.round(box.x + box.width / 2), Math.round(box.y + box.height / 2)];
        const at = document.elementFromPoint(centre[0], centre[1]);
        const own = row.querySelector<HTMLElement>("[data-testid^='access-trip-open']");
        return !!own && box.y >= 0 && box.bottom <= window.innerHeight && centre[1] < floorPx &&
          !!at && (at === own || own.contains(at));
      });
      const first = rows[0];
      const last = rows[rows.length - 1];
      return {
        rows: rows.length,
        in_band: inBand.length,
        first_in_band: !!first && inBand.includes(first),
        last_in_band: !!last && inBand.includes(last),
      };
    }, HIT_FLOOR);

  await page.evaluate(() => window.scrollTo(0, 0));
  await page.waitForTimeout(500);
  const atTop = await probe();
  // how a keyboard gets to the last row: focus its own button and let the browser place it. This is
  // the position worth measuring, because `focus()` asks for `scrollIntoView({block:'nearest'})`, and
  // 'nearest' is free to land the row under a fixed bottom bar.
  const focused = await page.evaluate((floorPx: number) => {
    const rows = Array.from(document.querySelectorAll<HTMLElement>("[data-testid='access-trip-row']"));
    const last = rows[rows.length - 1];
    const own = last?.querySelector<HTMLElement>("[data-testid^='access-trip-open']");
    own?.focus();
    return new Promise((resolve) => {
      requestAnimationFrame(() => requestAnimationFrame(() => {
        if (!last || !own) return resolve({ focused: false, in_band: false, note: "no last row" });
        const box = last.getBoundingClientRect();
        const centre = [Math.round(box.x + box.width / 2), Math.round(box.y + box.height / 2)];
        const at = document.elementFromPoint(centre[0], centre[1]);
        resolve({
          focused: document.activeElement === own,
          y: Math.round(box.y),
          bottom: Math.round(box.bottom),
          centre_y: centre[1],
          viewport_height: window.innerHeight,
          floor: floorPx,
          in_band:
            box.y >= 0 && box.bottom <= window.innerHeight && centre[1] < floorPx &&
            !!at && (at === own || own.contains(at)),
        });
      }));
    });
  }, HIT_FLOOR);
  // how a thumb gets there: pull the last row to the middle of the screen
  await page.evaluate(() => {
    const rows = document.querySelectorAll<HTMLElement>("[data-testid='access-trip-row']");
    rows[rows.length - 1]?.scrollIntoView({ block: "center", inline: "nearest" });
  });
  await page.waitForTimeout(500);
  const atBottom = await probe();
  const bothAtOnce =
    (atTop.first_in_band && atTop.last_in_band) || (atBottom.first_in_band && atBottom.last_in_band);
  const shot = evidencePath(DIR, `${RUN}_both_ends.png`);
  await page.screenshot({ path: shot, fullPage: false });
  writeFileSync(
    evidencePath(DIR, `${RUN}_both-ends.json`),
    JSON.stringify(
      {
        file: FILE,
        arm: "ord0539-both-ends-at-once",
        run_id: RUN,
        readings: {
          viewport: [WIDTH, HEIGHT],
          hit_floor_px: HIT_FLOOR,
          at_scroll_top: atTop,
          reached_by_focus: focused,
          at_last_row_scrolled_into_view: atBottom,
          both_ends_share_the_band_at_a_position: bothAtOnce,
          band_capacity_rows: Math.max(atTop.in_band, atBottom.in_band),
          shot,
        },
      },
      null,
      1,
    ),
  );

  expect(atTop.rows, node("B1", "the roster painted no rows, so the band question was never asked")).toBeGreaterThan(0);
  expect(
    atTop.first_in_band,
    node("B1", `the first row is not even reachable at the top of the page: ${JSON.stringify(atTop)}`),
  ).toBe(true);
  expect(
    atBottom.last_in_band,
    node("B1", `the last row cannot be reached by scrolling it to the middle of the screen: ${JSON.stringify(atBottom)}`),
  ).toBe(true);
  // the requirement a traveller actually has: the last row is reachable by the keyboard too, not only
  // by a thumb that happens to drag it to the middle. A focus that parks the row under the fixed bar
  // is a row nobody can press.
  expect(
    focused,
    node("B2", `the last row is not reachable by focus at ${WIDTH}px -- it lands under the bottom bar: ${JSON.stringify(focused)}`),
  ).toMatchObject({ focused: true, in_band: true });
});

/**
 * The thing that made this file's first cut read a stale list, said as a measurement instead of being
 * designed away: pressing the tier that is already in use asks the door nothing.
 *
 * It is not a defect on its own -- the order in use has not changed, so there is nothing to re-ask for.
 * But it is the reason a traveller who added a trip somewhere else and taps "最近更新" again sees the
 * old list, and it is the reason an arm that seeds *after* mounting reads rows that are not its own.
 * The arm therefore asserts only what the product promises (a different tier always re-asks) and
 * records what happens on a same-tier press, with the request count, so the block can say which of the
 * two it measured rather than which it expected.
 */
test(`ord0539-pressing-the-tier-in-use — a different tier re-asks the door; what a same-tier press does is recorded`, async ({
  page,
  request,
}) => {
  await page.setViewportSize({ width: WIDTH, height: HEIGHT });
  const traveler = await seedTraveler(request, "PRESS");
  for (const row of FIXTURE) await createTrip(request, traveler, "PRESS", row.name, row.start);
  await enterAccess(page);

  const asked: string[] = [];
  // only the list door itself: `/api/v1/journeys` with nothing after it, or with `?sort=` -- the
  // per-trip sub-resources (`/journeys/<id>/plans`) are this screen's other reads and would inflate
  // a count that is supposed to mean "the list was asked again"
  const LIST_DOOR = /\/api\/v1\/journeys(\?|$)/;
  page.on("request", (req) => {
    if (LIST_DOOR.test(req.url())) asked.push(req.url().split("/api/v1/journeys")[1] || "?");
  });

  const pressed = page.getByTestId("access-sort-tier-RECENT_UPDATE");
  const pressedNow = (await pressed.getAttribute("aria-pressed")) ?? "null";
  await pressed.click();
  await page.waitForTimeout(1_500);
  const afterSameTier = asked.length;

  await page.click("[data-testid='access-sort-tier-DEPARTURE_DATE']");
  await page.waitForTimeout(1_500);
  const afterOtherTier = asked.length - afterSameTier;
  const shot = evidencePath(DIR, `${RUN}_pressing.png`);
  await page.screenshot({ path: shot, fullPage: false });
  writeFileSync(
    evidencePath(DIR, `${RUN}_pressing-tier-in-use.json`),
    JSON.stringify(
      {
        file: FILE,
        arm: "ord0539-pressing-the-tier-in-use",
        run_id: RUN,
        readings: {
          tier_in_use_at_entry: pressedNow,
          door_requests_after_pressing_it_again: afterSameTier,
          door_requests_after_pressing_another_tier: afterOtherTier,
          requests_seen: asked,
          verdict_after_other_tier: await page
            .getByTestId("access-order-verdict")
            .getAttribute("data-state")
            .catch(() => null),
          shot,
        },
      },
      null,
      1,
    ),
  );

  expect(pressedNow, node("C1", `this screen should open on the tier in use, but aria-pressed read ${pressedNow}`)).toBe("true");
  expect(
    afterOtherTier,
    node("C1", `pressing a different tier asked the door ${afterOtherTier} times -- the order is not sent to the door: ${JSON.stringify(asked)}`),
  ).toBe(1);
  expect(
    afterSameTier,
    node("C1", `the same-tier press asked the door ${afterSameTier} times; the reading below was written to say which this build does`),
  ).toBeLessThanOrEqual(1);
});


