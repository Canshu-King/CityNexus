/* ORD-0553 · lane short-tiler (duanwagong) -- second leg: the receipt row, painted, with the
 * instant held at the API boundary.
 *
 * Why this leg exists: the write leg (qoder-duanwagong-0553-batch-row-instant-r1.spec.ts) asks the
 * planner for a real candidate plan, and on this generation the stage journey gets a domain refusal
 * back (HTTP 422 from `authoritative_compose_journey`, which re-raises the planner's ValueError).
 * That refusal is a property of the seeded stage, not of this order -- see the reading in
 * review/duanwagong/readouts. So this leg keeps everything the traveller touches real (the console
 * still asks the live server for grounded candidates, the cards, the tick, the button) and holds
 * only the two compose hops at the route boundary, so the row's instant is a known quantity.
 *
 * Two instants are put in the same batch on purpose:
 *   `+08:00` -- the offset the store actually uses for Tianjin rows (measured in seed_main.db).
 *   `+00:00` -- the shape V8Experience.tsx documents as the defect: slicing the ISO string prints
 *              the UTC wall clock and calls it local.
 * The old line printed both as `2026-10-10 15:30` / `2026-10-10 02:00`. The row now prints the
 * device-zone reading in the language the screen opened in, so the two rows differ by six hours on
 * screen exactly as they differ by six hours in the store.
 *
 * Nothing here writes to a database: the compose POST is answered from the route handler and never
 * reaches the backend, and the plan GET is answered the same way.
 */
import { expect, test, type Page, type Route } from "@playwright/test";
import fs from "node:fs";
import path from "node:path";

const FILE = "frontend/e2e/qoder-duanwagong-0553-batch-row-stub-r1.spec.ts";
const RUN = process.env.CITYNEXUS_E2E_RUN_ID ?? "dev";
const EVIDENCE_DIR = path.join(process.cwd(), "..", "review", "duanwagong", "readouts");
const PLAN_ID = "00000000-0000-4000-8000-000000d05530";
const EAST = "2026-10-10T15:30:00+08:00";
const UTC = "2026-10-10T02:00:00+00:00";

const TICK = '[data-testid="v13-pick-candidate"]';
const CARDS = "article.v8-stay-card";
const FINISH = '[data-testid="v13-discovery-finish-batch"]';
const RECEIPT = '[data-testid="v13-discovery-batch-receipt"]';
const ROW = '[data-testid="v13-discovery-batch-row"]';

const LOCALES: Array<["zh-CN" | "en", string]> = [
  ["zh-CN", "zh"],
  ["en", "en"],
];

const readings: Record<string, unknown> = {};

test.afterEach(({}, info) => {
  const arm = /^S(\w+)/.exec(info.title)?.[0] ?? info.title.slice(0, 6);
  fs.mkdirSync(EVIDENCE_DIR, { recursive: true });
  fs.writeFileSync(
    path.join(EVIDENCE_DIR, `dwg0553stub__${arm}.json`),
    JSON.stringify({ run_id: RUN, spec: FILE, arm, ...((readings[arm] ?? {}) as object) }, null, 1),
    "utf-8",
  );
});

const node = (arm: string, text: string) => `[dwg-0553-stub ${arm}] ${text}`;

function activitiesFor(placeIds: string[]) {
  return placeIds.map((placeId, index) => ({
    id: `11111111-1111-4111-8111-${String(index).padStart(12, "0")}`,
    sequence_no: index + 1,
    title: `stub row ${index}`,
    place_id: placeId,
    start_at: index === 0 ? EAST : UTC,
    end_at: index === 0 ? EAST : UTC,
  }));
}

async function holdCompose(route: Route) {
  let placeIds: string[] = [];
  try {
    const body = JSON.parse(route.request().postData() ?? "{}") as { place_ids?: string[] };
    placeIds = body.place_ids ?? [];
  } catch {
    placeIds = [];
  }
  await route.fulfill({
    status: 201,
    contentType: "application/json",
    body: JSON.stringify({
      optimizer: "held_at_route",
      complete_plan_count: 1,
      frozen_evidence_ids: [],
      stay_offer_id: null,
      top_k: [{ id: PLAN_ID, version_no: 7, status: "CANDIDATE", activities: activitiesFor(placeIds) }],
    }),
  });
}

async function holdPlanReadback(route: Route, placeIds: string[]) {
  await route.fulfill({
    status: 200,
    contentType: "application/json",
    body: JSON.stringify({
      id: PLAN_ID,
      version_no: 7,
      status: "CANDIDATE",
      activities: activitiesFor(placeIds),
    }),
  });
}

for (const [locale, tag] of LOCALES) {
  const arm = `S${tag}`;
  test(`S${tag} - the receipt row paints the instant, not the ISO string (${locale})`, async ({ page }) => {
    test.setTimeout(300_000);

    const scene = await page.request.get("/api/v1/demo/scene");
    expect(scene.status(), node(arm, "the stage answered no scene")).toBe(200);
    const journeyId = String(((await scene.json()) as { journey_id?: string }).journey_id ?? "");
    expect(journeyId.length > 8, node(arm, "the scene names no journey, so there is no console")).toBe(true);

    await page.addInitScript((seed) => {
      localStorage.clear();
      localStorage.setItem("citynexus.locale", seed.locale);
      localStorage.setItem("citynexus.v8.journey_id", seed.journey);
    }, { locale, journey: journeyId });

    await page.setViewportSize({ width: 390, height: 844 });
    await page.goto("/v8/hub", { waitUntil: "load" });
    await expect(page.getByTestId("today-hero"), node(arm, "Today never rendered")).toBeVisible({ timeout: 30_000 });
    await page.goto("/v8/discover", { waitUntil: "load" });
    await expect(page.getByTestId("v13-discovery-goal"), node(arm, "the discovery console never mounted")).toBeVisible({
      timeout: 30_000,
    });

    await page.locator('select[aria-label]').first().selectOption("replay");
    await page.getByTestId("v13-discover-submit").click();
    await expect(page.getByTestId("v13-discovery-result"), node(arm, "no result block")).toBeVisible({ timeout: 60_000 });
    await expect
      .poll(async () => await page.locator(CARDS).count(), { message: node(arm, "no card rendered"), timeout: 30_000 })
      .toBeGreaterThan(0);

    /* The tick has to land on two cards, so the batch carries both instants. */
    await page.locator(TICK).nth(0).click();
    await page.locator(TICK).nth(1).click();
    await page.waitForTimeout(200);

    const seenPlaceIds: string[] = [];
    await page.route("**/plans/authoritative-compose", async (route) => {
      try {
        const body = JSON.parse(route.request().postData() ?? "{}") as { place_ids?: string[] };
        seenPlaceIds.push(...(body.place_ids ?? []));
      } catch {
        /* the assertion below reports an empty batch */
      }
      await holdCompose(route);
    });
    await page.route(`**/api/v1/plans/${PLAN_ID}`, (route) => holdPlanReadback(route, seenPlaceIds));

    await page.locator(FINISH).click();
    await expect(page.locator(RECEIPT), node(arm, "the held compose produced no read-back block")).toBeVisible({
      timeout: 60_000,
    });
    await page.waitForTimeout(600);

    const cells = (await page.locator(`${ROW} span`).allInnerTexts()).map((v) => v.replace(/\s+/g, " ").trim());
    const rows = (await page.locator(ROW).allInnerTexts()).map((v) => v.replace(/\s+/g, " ").trim());
    const deviceZone = await page.evaluate(() => Intl.DateTimeFormat().resolvedOptions().timeZone);

    /* Recompute both readings in the page, from the two instants, with the browser's own Intl. */
    const expected = await page.evaluate(
      ([east, utc, loc]) =>
        [east, utc].map((raw) =>
          new Intl.DateTimeFormat(loc === "zh-CN" ? "zh-CN" : "en-GB", {
            month: "short",
            day: "numeric",
            hour: "2-digit",
            minute: "2-digit",
          }).format(new Date(raw))),
      [EAST, UTC, locale] as [string, string, "zh-CN" | "en"],
    );

    fs.mkdirSync(EVIDENCE_DIR, { recursive: true });
    await page.screenshot({ path: path.join(EVIDENCE_DIR, `dwg0553stub_${arm}_${RUN}.png`), fullPage: true });

    readings[arm] = {
      spec: FILE,
      run_id: RUN,
      locale,
      device_zone: deviceZone,
      instants_held: [EAST, UTC],
      cells_on_screen: cells,
      expected_from_instants: expected,
      row_texts: rows,
      old_slice_would_have_printed: [EAST.slice(0, 16).replace("T", " "), UTC.slice(0, 16).replace("T", " ")],
    };

    expect(cells.length, node(arm, `the receipt holds ${cells.length} rows, two instants were asked for`)).toBe(2);

    /* S1 -- no ISO date shape anywhere in the time cells. */
    for (const cell of cells) {
      expect(/\d{4}-\d{2}-\d{2}/.test(cell), node(arm, `a cell still prints an ISO date: "${cell}"`)).toBe(false);
      expect(/\d{2}:\d{2}:\d{2}/.test(cell), node(arm, `a cell still prints seconds: "${cell}"`)).toBe(false);
    }

    /* S2 -- each cell is the device-zone reading of the instant held for it. */
    expect(cells[0], node(arm, `east cell "${cells[0]}" is not the device reading "${expected[0]}" of ${EAST}`)).toBe(expected[0]);
    expect(cells[1], node(arm, `utc cell "${cells[1]}" is not the device reading "${expected[1]}" of ${UTC}`)).toBe(expected[1]);

    /* S3 -- the two instants that are six hours apart in the store are six hours apart on screen,
       which is the thing the sliced string could not say. */
    expect(cells[0] !== cells[1], node(arm, `both cells read the same: "${cells[0]}"`)).toBe(true);

    /* S4 -- the language the screen opened in is the language the date comes back in. */
    if (locale === "zh-CN") {
      expect(cells[0], node(arm, `zh cell is not Chinese-shaped: "${cells[0]}"`)).toContain("月");
    } else {
      expect(/^[A-Z][a-z]{2} \d/.test(cells[0]), node(arm, `en cell is not English-shaped: "${cells[0]}"`)).toBe(true);
    }
  });
}
