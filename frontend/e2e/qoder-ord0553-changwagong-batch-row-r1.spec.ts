/**
 * ORD-0553 (lane 长瓦工) -- the discovery batch read-back row, read on screen in both locales.
 *
 * What is under test is one render: the `<span>` inside `[data-testid="v13-discovery-batch-row"]`.
 * Before this cut it printed `row.start_at.slice(0, 16).replace("T", " ")`, so the traveller read an
 * ISO-8601 fragment (`2026-10-10 09:00`) with no statement of whose clock that was; the stored value
 * carries an offset (read from the tree's own store: every one of the sampled `activities.start_at`
 * rows ends `+08:00`), so the cut silently presented the itinerary city's wall clock as if it were
 * un-zoned.  This arm asks for the same instant through `formatWhen` and asserts three things that a
 * green-by-default test would not: no ISO date pattern on the screen, the painted text equals the
 * device-zone rendering of that instant computed in this very page, and the English arm paints no
 * Chinese.
 *
 * Why the compose is served from a fixture instead of being written for real: this screen's own
 * comment records that a compose on this store refuses with
 * `V13_FULL_GROUNDING_MISSING_MOBILITY_PAIR` (RealCityDiscoveryPanel.tsx, the ORD-0435 block above
 * `request`).  The existing ORD-0435 Q4 arms, which do take the write route, are red on the
 * unmodified authoritative tip in this lane's stack for exactly that reason -- measured in
 * `review/changwagong/`, and reported rather than hidden.  So the network leg here is a stub, while
 * the boot (stage journey, replay discovery, result cards, the tick, the 完成 click) is the real
 * console.  That buys a screen reading of this row's render path and buys no claim about the write
 * route.
 */
import { expect, test, type Page } from "@playwright/test";
import { writeFileSync } from "node:fs";
import { randomUUID } from "node:crypto";
import { evidencePath } from "./_qoderEvidence";

const FILE = "e2e/qoder-ord0553-changwagong-batch-row-r1.spec.ts";
const node = (id: string, detail: string) => `${FILE} :: ${id} — ${detail}`;
const RUN = process.env.CITYNEXUS_E2E_RUN_ID ?? "local";
const BASE_TIP = process.env.CITYNEXUS_E2E_GIT_HEAD ?? "unknown";

const CARDS = "article.v8-stay-card";
const TICK = '[data-testid="v13-pick-candidate"]';
const FINISH = '[data-testid="v13-discovery-finish-batch"]';
const ROW = '[data-testid="v13-discovery-batch-row"]';
const ROW_TIME = `${ROW} span`;

/** One real stored shape, read verbatim out of the tree's own SQLite `activities.start_at`. */
const START_AT = "2026-10-10T09:00:00+08:00";
const OLD_PAINTING = START_AT.slice(0, 16).replace("T", " ");

type Locale = "zh-CN" | "en";
const LOCALES: ReadonlyArray<readonly [Locale, string]> = [
  ["zh-CN", "zh"],
  ["en", "en"],
];

/**
 * Serve the compose and the plan read-back so the receipt block renders.
 *
 * The activity's `place_id` is taken from the POST body the console itself sent, because the panel
 * only counts a row as landed when its `place_id` is in its own picked set -- a fixture written with
 * invented ids would render an empty list and the arm would be measuring nothing.
 */
async function stubCompose(page: Page, planId: string) {
  const plan = (placeIds: string[]) => ({
    id: planId,
    version_no: 4,
    status: "CANDIDATE",
    activities: placeIds.map((placeId, i) => ({
      id: randomUUID(),
      sequence_no: i + 1,
      title: "Nexus River Cruise Pier",
      activity_type: "visit",
      place_id: placeId,
      start_at: START_AT,
      end_at: "2026-10-10T10:15:00+08:00",
      status: "PLANNED",
      locked: 0,
    })),
  });
  let sentPlaceIds: string[] = [];
  await page.route("**/api/v1/journeys/*/plans/authoritative-compose", async (route) => {
    const body = JSON.parse(String(route.request().postData() ?? "{}"));
    sentPlaceIds = Array.isArray(body.place_ids) ? body.place_ids.map(String) : [];
    await route.fulfill({
      status: 201,
      contentType: "application/json",
      body: JSON.stringify({
        optimizer: "V13_MULTIDAY",
        complete_plan_count: 1,
        frozen_evidence_ids: [],
        stay_offer_id: null,
        top_k: [plan(sentPlaceIds)],
      }),
    });
  });
  await page.route("**/api/v1/plans/*", (route) =>
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(plan(sentPlaceIds)),
    }),
  );
}

/** The same instant rendered by the device, computed the way the helper does it. */
async function deviceReading(page: Page, locale: Locale) {
  return page.evaluate(
    ([raw, loc]) =>
      new Intl.DateTimeFormat(loc === "zh-CN" ? "zh-CN" : "en-GB", {
        month: "short",
        day: "numeric",
        hour: "2-digit",
        minute: "2-digit",
      }).format(new Date(raw)),
    [START_AT, locale] as [string, Locale],
  );
}

async function arm(page: Page, locale: Locale, tag: string) {
  test.setTimeout(180_000);
  const scene = await page.request.get("/api/v1/demo/scene");
  const journeyId = String(((await scene.json()) as { journey_id?: string }).journey_id ?? "");
  expect(journeyId.length > 8, node(`R1${tag}`, `the stage named no journey (scene http ${scene.status()})`)).toBe(true);

  await page.addInitScript((seed) => {
    localStorage.clear();
    localStorage.setItem("citynexus.locale", seed.locale);
    localStorage.setItem("citynexus.v8.journey_id", seed.journey);
  }, { locale, journey: journeyId });

  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/v8/hub", { waitUntil: "load" });
  await expect(page.getByTestId("today-hero"), node(`R1${tag}`, `Today never rendered in ${locale}`)).toBeVisible({
    timeout: 30_000,
  });
  await page.goto("/v8/discover", { waitUntil: "load" });
  await expect(page.getByTestId("v13-discovery-goal"), node(`R1${tag}`, "the discovery console never mounted")).toBeVisible({
    timeout: 30_000,
  });

  const planId = randomUUID();
  await stubCompose(page, planId);

  await page.locator('select[aria-label]').first().selectOption("replay");
  await page.getByTestId("v13-discover-submit").click();
  await expect(page.getByTestId("v13-discovery-result"), node(`R1${tag}`, "no result block")).toBeVisible({
    timeout: 60_000,
  });
  await expect
    .poll(async () => page.locator(CARDS).count(), {
      message: node(`R1${tag}`, "no result card, so the tick below would tick nothing"),
      timeout: 30_000,
    })
    .toBeGreaterThan(0);

  await page.locator(TICK).first().click();
  await page.locator(FINISH).click();
  const row = page.locator(ROW_TIME).first();
  await expect(row, node(`R1${tag}`, "the read-back row never rendered")).toBeVisible({ timeout: 30_000 });

  const shown = (await row.innerText()).replace(/\s+/g, " ").trim();
  const expected = await deviceReading(page, locale);
  await page.screenshot({ path: evidencePath(`ord0553/${RUN}__row_${tag}.png`), fullPage: false });

  const readings = {
    run_id: RUN,
    arm: `R1${tag}`,
    spec: FILE,
    base_tip: BASE_TIP,
    locale,
    served_start_at: START_AT,
    painted: shown,
    device_reading: expected,
    old_painting_would_have_been: OLD_PAINTING,
    device_zone: await page.evaluate(() => Intl.DateTimeFormat().resolvedOptions().timeZone),
  };
  writeFileSync(evidencePath(`ord0553/${RUN}__R1${tag}.json`), JSON.stringify(readings, null, 1), "utf-8");

  /* 1. Nothing that looks like an ISO date reaches the traveller. */
  expect(shown, node(`R1${tag}`, `the row still paints an ISO fragment: "${shown}"`)).not.toMatch(/\d{4}-\d{2}-\d{2}/);
  /* 2. The text is exactly this device's rendering of that instant, not a hand-written string. */
  expect(shown, node(`R1${tag}`, `"${shown}" is not the device reading "${expected}"`)).toBe(expected);
  /* 3. The reading this row used to produce is gone. */
  expect(shown, node(`R1${tag}`, `the row still paints the pre-fix reading`)).not.toBe(OLD_PAINTING);
  /* 4. Locale discipline: the English arm paints no Chinese, the Chinese arm paints some. */
  if (locale === "en") {
    expect(shown, node(`R1${tag}`, `the English arm painted Chinese: "${shown}"`)).not.toMatch(/[\u4e00-\u9fff]/);
  } else {
    expect(shown, node(`R1${tag}`, `the Chinese arm painted no Chinese: "${shown}"`)).toMatch(/[\u4e00-\u9fff]/);
  }
}

for (const [locale, tag] of LOCALES) {
  test(`R1${tag}_${locale} — 批次回读行不再把 ISO 片段上屏`, async ({ page }) => {
    await arm(page, locale, tag);
  });
}
