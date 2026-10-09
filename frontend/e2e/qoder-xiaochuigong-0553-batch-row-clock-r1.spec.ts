/* ORD-0553 (lane xiaochuigong) -- what the traveller reads for an instant in the discovery
 * batch-receipt row (`frontend/src/features/discovery/RealCityDiscoveryPanel.tsx`).
 *
 * Why this file exists.  That row only renders after `finishBatch`, which needs
 * `POST /api/v1/journeys/{id}/plans/authoritative-compose` (backend/app/main.py:7738) and then
 * `GET /api/v1/plans/{id}` (backend/app/main.py:7795) to answer.  ORD-0435's own gate drives exactly
 * that route and is red on this tip with pristine bytes: this lane ran `e2e/qoder-ord0435-poi-batch-
 * multiselect.spec.ts -g Q4` against the authoritative generation it branched from, and both Q4zh and
 * Q4en failed on "produced no read-back block" while the screen's own alert read 没能组合探索结果.
 * So no one can reach that row through the live write route at this sha, and a lane that owes a screen
 * reading for it has to get the reading without inventing the instant.
 *
 * What this file does, in order, all against the stack this run starts:
 *   1. boot the console, run discovery for real, and capture the discovery answer the browser got;
 *   2. read a real stored instant off a real door (journey -> active plan -> first activity row);
 *   3. PROBE the compose door with the picked candidate's own `place_id`, recording status and body --
 *      the pre-existing red goes on the record instead of being routed around silently;
 *   4. if that probe answers, replay its own bytes; otherwise re-send the plan door's own row with the
 *      `place_id` re-pointed at the traveller's pick (every other value, the instant included, is the
 *      door's) and record which of the two happened in `replay_origin`;
 *   5. tick the matching card, let the panel ask its two doors, and read the row in both locales.
 *
 * The shape judgement -- ISO fragment before, locale rendering after -- lives in
 * `review/xiaochuigong/ord0553_discovery_batch_row_arm_r1.py`, run once against this generation's
 * bytes and once against this lane's, so before/after is measured rather than promised.  What is
 * asserted here is only what must hold in BOTH: a receipt renders, it carries a row, and the row
 * states the same hour:minute the server holds.  A fix that quietly moved the clock fails here.
 */

import { expect, test, type Page } from "@playwright/test";
import { mkdirSync, readFileSync, writeFileSync } from "node:fs";
import path from "node:path";

const CARDS = "article.v8-stay-card";
const TICK = '[data-testid="v13-pick-candidate"]';
const FINISH = '[data-testid="v13-discovery-finish-batch"]';
const RECEIPT = '[data-testid="v13-discovery-batch-receipt"]';
const ROW = '[data-testid="v13-discovery-batch-row"]';
const GOAL = '[data-testid="v13-discovery-goal"]';
const SUBMIT = '[data-testid="v13-discover-submit"]';
const RESULT = '[data-testid="v13-discovery-result"]';
const BATCH_ERROR = '[data-testid="v13-discovery-batch-error"]';

const PANEL = path.join("src", "features", "discovery", "RealCityDiscoveryPanel.tsx");
const EVIDENCE = path.join(process.cwd(), "..", "review", "xiaochuigong", "readouts", "ord0553");
const RUN = process.env.CITYNEXUS_E2E_RUN_ID ?? "manual";
/* Required, not defaulted: a reading that cannot name the bytes it rendered behind is worthless. */
const HEAD = process.env.CITYNEXUS_E2E_GIT_HEAD ?? "";
if (HEAD.length < 7) {
  throw new Error("CITYNEXUS_E2E_GIT_HEAD must name the generation this run rendered (review/run_spec.py sets it)");
}
const node = (arm: string, what: string) =>
  `e2e/qoder-xiaochuigong-0553-batch-row-clock-r1.spec.ts :: ${arm} — ${what}`;

const hhmm = (iso: string) => `${iso.slice(11, 13)}:${iso.slice(14, 16)}`;

type PlanRow = { id: string; place_id?: string | null; title: string; start_at: string; end_at: string };
type PlanBody = { id: string; version_no?: number; status?: string; activities?: PlanRow[] };

async function realStoredPlan(request: Page["request"], journeyId: string, arm: string) {
  const door = await request.get(`/api/v1/journeys/${journeyId}`);
  expect(door.status(), node(arm, `GET /api/v1/journeys/{id} answered ${door.status()}`)).toBe(200);
  const planId = String(((await door.json()) as { active_plan_version_id?: string | null }).active_plan_version_id ?? "");
  expect(planId.length > 8, node(arm, "the seeded journey holds no active plan to read an instant from")).toBe(true);
  const read = await request.get(`/api/v1/plans/${planId}`);
  expect(read.status(), node(arm, `GET /api/v1/plans/{id} answered ${read.status()}`)).toBe(200);
  const body = read ? await read.text() : "";
  const parsed = JSON.parse(body) as PlanBody;
  const rows = parsed.activities ?? [];
  expect(rows.length, node(arm, "the active plan answers with no activity rows")).toBeGreaterThan(0);
  return { planId, body, parsed, row: rows[0] };
}

async function arm(page: Page, locale: "zh-CN" | "en", tag: string) {
  test.setTimeout(300_000);
  const armName = `R0553${tag}`;
  mkdirSync(EVIDENCE, { recursive: true });

  const scene = await page.request.get("/api/v1/demo/scene");
  const journeyId = String(((await scene.json()) as { journey_id?: string }).journey_id ?? "");
  expect(journeyId.length > 8, node("boot", `the stage named no journey (scene http ${scene.status()})`)).toBe(true);

  const stored = await realStoredPlan(page.request, journeyId, "boot");

  await page.addInitScript((seed) => {
    localStorage.clear();
    localStorage.setItem("citynexus.locale", seed.locale);
    localStorage.setItem("citynexus.v8.journey_id", seed.journey);
  }, { locale, journey: journeyId });

  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/v8/hub", { waitUntil: "load" });
  await expect(page.getByTestId("today-hero"), node("boot", `Today never rendered in ${locale}`)).toBeVisible({ timeout: 30_000 });
  await page.goto("/v8/discover", { waitUntil: "load" });
  await expect(page.locator(GOAL), node("boot", "the discovery console never mounted")).toBeVisible({ timeout: 30_000 });

  /* The discovery answer the browser itself receives: its candidate rows carry the
     `materialized_place_id` the panel later sends to the compose door, so the pick below is the
     traveller's own pick and not a place id this test chose for them. */
  let discoveryBody: { discovery?: { candidates?: Array<{ id: string; name: string; materialized_place_id?: string }> } } | null = null;
  page.on("response", async (res) => {
    if (res.url().includes("/real-city/intelligence")) {
      try { discoveryBody = await res.json(); } catch { /* a non-JSON answer leaves the capture empty */ }
    }
  });

  await page.locator('select[aria-label]').first().selectOption("replay");
  await page.locator(SUBMIT).click();
  await expect(page.locator(RESULT), node("boot", "the console answered with no result block")).toBeVisible({ timeout: 60_000 });
  await expect.poll(async () => await page.locator(CARDS).count(),
    { message: node("boot", "no card rendered, so every reading below would be a reading of nothing"), timeout: 30_000 })
    .toBeGreaterThan(0);

  const cardTitles = (await page.locator(`${CARDS} h3`).allInnerTexts()).map((v) => v.replace(/\s+/g, " ").trim());
  const candidates = discoveryBody?.discovery?.candidates ?? [];
  expect(candidates.length, node(armName, "the discovery door's own answer was never captured")).toBeGreaterThan(0);
  const wanted = candidates.findIndex((c) => cardTitles.includes(String(c.name).replace(/\s+/g, " ").trim()));
  expect(wanted >= 0, node(armName, `no card ("${cardTitles.join(" | ")}") matches a candidate the door returned`)).toBe(true);
  const picked = candidates[wanted];
  const pickedPlace = String(picked.materialized_place_id ?? picked.id);

  /* Step 3: the real door, unstubbed.  Whatever it answers is recorded either way. */
  const probe = await page.request.post(`/api/v1/journeys/${journeyId}/plans/authoritative-compose`, {
    data: { place_ids: [pickedPlace], candidate_count: 1 },
  });
  const probeBody = (await probe.text()).replace(/\s+/g, " ").slice(0, 500);
  const composedId = String((((JSON.parse(probeBody || "{}") as { top_k?: Array<{ id?: string }> }).top_k ?? [{}])[0]).id ?? "");
  const readback = composedId.length > 8 ? await page.request.get(`/api/v1/plans/${composedId}`) : null;
  const readbackText = readback ? await readback.text() : "";
  const readbackRows = readback ? ((JSON.parse(readbackText || "{}") as PlanBody).activities ?? []) : [];
  const holdsPicked = readbackRows.some((r) => String(r.place_id ?? "") === pickedPlace);

  let replayPlanId = composedId;
  let replayBody = readbackText;
  let replayOrigin = "server";
  if (!(readback && readback.status() === 200 && holdsPicked)) {
    /* The compose door does not answer, so the read-back is the plan door's own first row with only
       its `place_id` re-pointed at the traveller's pick.  The instant, the row id, the version and the
       status are all bytes that door answered with; only the pairing is this test's. */
    replayPlanId = stored.planId;
    replayBody = JSON.stringify({
      ...stored.parsed,
      activities: [{ ...stored.row, place_id: pickedPlace, title: String(picked.name) }],
    });
    replayOrigin = "plan_door_row_repointed_at_the_pick";
  }

  await page.route(`**/api/v1/plans/${replayPlanId}`, (route) =>
    route.fulfill({ status: 200, contentType: "application/json", body: replayBody }));
  await page.route("**/plans/authoritative-compose", (route) =>
    route.fulfill({ status: 201, contentType: "application/json", body: JSON.stringify({ top_k: [{ id: replayPlanId }] }) }));

  await page.locator(TICK).nth(wanted).click();
  await expect(page.locator(FINISH), node(armName, "完成 was never pressable for the ticked card")).toBeEnabled({ timeout: 20_000 });
  await page.locator(FINISH).click();

  const errors = await page.locator(BATCH_ERROR).count();
  expect(errors, node(armName, "the read-back never reached the screen")).toBe(0);
  await expect(page.locator(RECEIPT), node(armName, "no read-back block appeared")).toBeVisible({ timeout: 60_000 });

  const rows = (await page.locator(ROW).allInnerTexts()).map((v) => v.replace(/\s+/g, " ").trim());
  expect(rows.length, node(armName, "the receipt rendered with no row in it")).toBeGreaterThan(0);
  await page.locator(ROW).first().scrollIntoViewIfNeeded();
  const shot = path.join(EVIDENCE, `${RUN}__${armName}_row.png`);
  await page.locator(RECEIPT).screenshot({ path: shot });

  const instantUsed = replayOrigin === "server" ? String(readbackRows[0]?.start_at) : String(stored.row.start_at);
  const need = hhmm(instantUsed);
  expect(rows[0], node(armName, `the row reads "${rows[0]}" and does not state ${need} from ${instantUsed}`)).toContain(need);

  const renderLine = (readFileSync(path.join(process.cwd(), PANEL), "utf-8").split("\n")
    .find((l) => /<span>\{(?:formatWhen\()?row\.start_at/.test(l)) ?? "").trim();

  writeFileSync(path.join(EVIDENCE, `${RUN}__${armName}.json`), JSON.stringify({
    run_id: RUN,
    git_head: HEAD,
    arm: armName,
    nodeid: `e2e/qoder-xiaochuigong-0553-batch-row-clock-r1.spec.ts > ${armName}_${locale}`,
    locale,
    viewport: "390x844",
    device_zone: Intl.DateTimeFormat().resolvedOptions().timeZone,
    product_render_line: renderLine,
    product_uses_formatter: renderLine.includes("formatWhen(row.start_at"),
    journey_id: journeyId,
    plan_door_read_of_record: { plan_id: stored.planId, activity_id: stored.row.id,
                                 start_at: stored.row.start_at, end_at: stored.row.end_at },
    discovery_candidate: { name: picked.name, materialized_place_id: pickedPlace },
    real_compose_probe: {
      status: probe.status(),
      body_head: probeBody,
      composed_id: composedId || null,
      readback_status: readback?.status() ?? null,
      readback_holds_picked: holdsPicked,
    },
    replay_origin: replayOrigin,
    instant_used: instantUsed,
    receipt_rows: rows,
    row_head: rows[0],
    hour_minute_required: need,
    screenshot: shot.replace(/\\/g, "/"),
    test_status: "reached_end_of_arm",
  }, null, 1), "utf-8");
}

for (const [locale, tag] of [["zh-CN", "zh"], ["en", "en"]] as const) {
  test(`R0553${tag}_${locale} — 批次回读那一行的时刻值`, async ({ page }) => {
    await arm(page, locale, tag);
  });
}
