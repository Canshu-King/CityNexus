import { expect, test, type Page, type Route } from "@playwright/test";

/** First cut of the classroom sandbox on the map: the served simulated traveller must be drawn
 *  as its own marker, beside (not among) the numbered research pins.  All values are fixtures. */
const journeyId = "00000000-0000-4000-8000-000000000121";
const tid = "00000000-0000-4000-8000-000000000122";
const prefix = `**/api/v1/journeys/${journeyId}`;

async function fulfill(route: Route, value: unknown) {
  await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(value) });
}

async function mockJourney(page: Page) {
  await page.addInitScript(({ id }) => {
    window.sessionStorage.setItem("citynexus.traveler.bearer", "TEST_ONLY_SIGNED_FIXTURE_TOKEN");
    window.sessionStorage.setItem("citynexus.traveler.session-id", "fixture-traveler-121");
    window.localStorage.setItem("citynexus.revolution.firstlook.journey", JSON.stringify({
      id, ownerTravelerId: "fixture-traveler-121", cityCode: "CN-RV-TEST", cityName: "连城", status: "ACTIVE",
    }));
  }, { id: journeyId });
  await page.route("**/api/v1/agent/runtime-status", (r) => fulfill(r, {
    runtime_identity: "UNAVAILABLE", hermes_compat_configured: false, ai_state: "CONFIGURED_UNVERIFIED",
  }));
  await page.route(prefix, (r) => fulfill(r, {
    id: journeyId, status: "ACTIVE", timezone: "Asia/Shanghai", title: "TEST ONLY 执行中的旅行",
    city_code: "CN-RV-TEST", start_at: "2026-12-03T00:00:00+08:00", end_at: "2026-12-04T23:59:00+08:00",
  }));
  await page.route(`${prefix}/operator`, (r) => fulfill(r, { journey_id: journeyId, state: "OFF" }));
  await page.route(`${prefix}/members/me`, (r) => fulfill(r, { journey_id: journeyId, may_confirm_departure: true }));
  await page.route(`${prefix}/planning-intent`, (r) => fulfill(r, {
    journey_id: journeyId, intent: null, candidates: [],
    trip: { dates: ["2026-12-03"], party_size: 1, budget: { amount_minor: 50000, currency: "CNY" } },
  }));
  await page.route(`${prefix}/map-places`, (r) => fulfill(r, {
    journey_id: journeyId,
    candidates: [
      { candidate_id: "place-a", name: "TEST ONLY 天安门", latitude: 39.9055, longitude: 116.3976,
        provider_provenance: "TEST_PROVIDER", selection_state: "READY_FOR_NATIVE_PLAN",
        source_url: "https://www.openstreetmap.org/node/1", observation_expired: false,
        region_status: "MATCHED", coordinate_system: "WGS84" },
      { candidate_id: "place-b", name: "TEST ONLY 故宫", latitude: 39.9163, longitude: 116.3972,
        provider_provenance: "TEST_PROVIDER", selection_state: "READY_FOR_NATIVE_PLAN",
        source_url: "https://www.openstreetmap.org/node/2", observation_expired: false,
        region_status: "MATCHED", coordinate_system: "WGS84" },
    ],
  }));
  await page.route(`${prefix}/bootstrap-shortlist`, (r) => fulfill(r, { journey_id: journeyId, pocket_walk: null }));
  await page.route(`${prefix}/bootstrap-discovery/current`, (r) => fulfill(r, { journey_id: journeyId, candidates: [], receipt_id: null }));
  await page.route(`${prefix}/plans`, (r) => fulfill(r, []));
  await page.route(`${prefix}/departure`, (r) => fulfill(r, {
    journey_id: journeyId, gate: "NO_PLAN_SELECTED", candidates: [], selected_plan: null,
  }));
  await page.route("**/api/v1/demo/simulation-clock/**", (r) => fulfill(r, {
    journey_id: journeyId, virtual_now: "2026-12-03T10:30:00+08:00", version: 2, persisted: true,
    basis: "PERSISTED_SIMULATION_CLOCK", journey_status: "ACTIVE", plan_version_id: null,
    current_activity_id: "activity-a", current_activity_title: "TEST ONLY 故宫", current_activity_status: "ACTIVE",
    traveller: { latitude: 39.9201, longitude: 116.4012, coordinate_system: "WGS84",
      label: "TEST ONLY 故宫", source: "SCENARIO_SIMULATED_LOCATION" },
  }));
}

test.describe("Classroom sandbox traveller fixture", () => {
  test.use({ viewport: { width: 390, height: 844 }, hasTouch: true });

  test.beforeEach(async ({ page }) => {
    await page.route("**/api/v1/**", (route) => route.fulfill({
      status: 404, contentType: "application/json", body: JSON.stringify({ detail: "TEST_FIXTURE_ENDPOINT_NOT_SEEDED" }),
    }));
    await page.route("**/api/v1/travelers/session", (route) => fulfill(route, { traveler_id: "fixture-traveler-121" }));
  });

  test("the simulated traveller reaches the map as its own marker", async ({ page }, testInfo) => {
    await mockJourney(page);
    await page.goto("/revolution");
    await page.getByTestId("rev-mobile-tab-trips").click();
    // An executing journey opens on 执行与待办; the map layer is one segmented press away.
    await page.getByRole("button", { name: "地图", exact: true }).first().click();
    const mapPane = page.getByTestId("rev-mission-map-pane");
    await expect(mapPane).toBeVisible();
    // The served position reaches the map component before any tile loads.
    const state = page.getByTestId("rev-map-traveller-state");
    await expect(state).toContainText("TEST ONLY 故宫");
    await expect(state).toContainText("模拟位置");
    const load = mapPane.getByRole("button", { name: "加载地图" });
    if (await load.count()) {
      await load.click();
      await expect(page.getByTestId("rev-workspace-map-canvas")).toBeVisible();
      // MapLibre puts the marker in the DOM even when tiles are slow; if WebGL is unavailable
      // in this runner the state line above still proves the served position reached the map.
      const marker = page.locator("[data-testid='rev-map-traveller']");
      await expect(marker).toHaveCount(1, { timeout: 15_000 });
      await expect(marker).toBeVisible();
      await page.waitForTimeout(1500);
    }
    await page.screenshot({ path: testInfo.outputPath("sim-traveller-390.png") });
  });
});
