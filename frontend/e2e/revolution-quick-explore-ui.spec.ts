import { expect, test, type Route } from "@playwright/test";

/**
 * UI-only consent / navigation regression. All provider responses are isolated
 * Playwright TEST_PROVIDER fixtures. This does NOT prove live OSM, an AgentRun,
 * a signed backend mutation, or physical arrival. Those require separate runs.
 */
test.use({ viewport: { width: 390, height: 844 }, hasTouch: true });

const journey = "00000000-0000-4000-8000-000000000117";
const root = `**/api/v1/journeys/${journey}`;
const firstId = "sample-spot-1";
const secondId = "sample-spot-2";

function json(route: Route, object: object) {
  return route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(object) });
}

test("plain Chinese first-user journey preserves separate intentional provider releases", async ({ page }) => {
  let citySearchCalls = 0;
  let poiSearchCalls = 0;
  let saved = false;
  let progressRevision = 0;
  let goState = "NOT_STARTED";

  const pocket = () => ({
    status: "POCKET_WALK_SAVED",
    pocket_walk_id: "pocket-quick-1",
    revision: 1,
    journey_id: journey,
    first_stop: { name: "SAMPLE ONLY - Trailhead", shortlist_id: "s1" },
    second_stop: { name: "SAMPLE ONLY - Park", shortlist_id: "s2" },
    plan_version_id: null,
    go_progress: {
      state: goState,
      progress_revision: progressRevision,
      pocket_walk_revision: 1,
      progress_class: "USER_REPORTED_PROGRESS",
      physical_arrival_state: "NOT_PHYSICAL_ARRIVAL_PROVEN",
    },
  });

  await page.addInitScript((id) => {
    window.sessionStorage.setItem("citynexus.traveler.bearer", "signed-only-fixture-token");
    window.localStorage.setItem("citynexus.revolution.firstlook.journey", JSON.stringify({
      id, cityCode: "CN-RV-TEST", cityName: "连城", status: "DRAFT",
    }));
  }, journey);
  await page.route(`${root}/bootstrap-discovery/readiness`, (route) => json(route, {
    status: "READY", reason_code: "READY", provider: "overpass",
    provider_name: "Playwright fixture", expected_recipient: "TEST_PROVIDER",
    capability_state: "TEST_CAPABLE", provider_grade: "TEST_PROVIDER",
    external_request_allowed: true, test_only: true,
  }));
  await page.route(`${root}/bootstrap-shortlist`, (route) => json(route, {
    journey_id: journey, limit: 3, items: [], resume: null,
    pocket_walk: saved ? pocket() : null,
  }));
  await page.route(`${root}/bootstrap-city-search`, async (route) => {
    citySearchCalls += 1;
    const payload = route.request().postDataJSON();
    expect(payload.provider_consent).toBe(true);
    expect(payload.query).toBe("连城");
    await json(route, {
      journey_id: journey, status: "CITY_RESULTS", query: "连城", provider_attempts: [],
      results: [{
        result_id: "city-fixture-1", name: "连城县", display_name: "连城县（测试地名结果）",
        provider: "test", provider_provenance: "TEST_PROVIDER",
        latitude: 25.7, longitude: 116.75, coordinate_system: "WGS84",
        confidence: "CITY_CENTROID_UNCERTAIN", selection_state: "CAMERA_ONLY_TAP_REQUIRED",
      }],
    });
  });
  await page.route(`${root}/bootstrap-discovery`, async (route) => {
    poiSearchCalls += 1;
    const payload = route.request().postDataJSON();
    expect(payload.provider_consent).toBe(true);
    expect(payload.source_kind).toBe("MANUAL_PUBLIC_CENTER");
    expect(payload.latitude).toBe(25.7);
    expect(payload.longitude).toBe(116.75);
    await json(route, {
      journey_id: journey, status: "LIVE_RESULTS", source_kind: "MANUAL_PUBLIC_CENTER",
      provider: "overpass", provider_provenance: "TEST_PROVIDER", receipt_id: "receipt-quick",
      attempts: [{ http_status: 200 }],
      candidates: [
        { candidate_id: firstId, name: "SAMPLE ONLY - Trailhead",
          category: "park", source_url: "https://www.openstreetmap.org/node/123",
          provider_provenance: "TEST_PROVIDER" },
        { candidate_id: secondId, name: "SAMPLE ONLY - Park",
          category: "park", source_url: "https://www.openstreetmap.org/node/124",
          provider_provenance: "TEST_PROVIDER" },
      ],
    });
  });
  await page.route(`${root}/bootstrap-discovery/pocket-walk`, async (route) => {
    const payload = route.request().postDataJSON();
    expect(payload.receipt_id).toBe("receipt-quick");
    expect(payload.first_candidate_id).toBe(firstId);
    expect(payload.second_candidate_id).toBe(secondId);
    saved = true;
    await json(route, { pocket_walk: pocket(), items: [] });
  });
  await page.route(`${root}/bootstrap-shortlist/pocket-walk/go`, async (route) => {
    const payload = route.request().postDataJSON();
    expect(payload.action).toBe("START");
    expect(payload.expected_revision).toBe(0);
    goState = "HEADING_TO_FIRST";
    progressRevision = 1;
    await json(route, { journey_id: journey, pocket_walk: pocket(), go_progress: pocket().go_progress });
  });

  await page.goto("/revolution");
  await expect(page.getByTestId("rev-quick-explore")).toBeVisible();
  expect(citySearchCalls).toBe(0);
  expect(poiSearchCalls).toBe(0);

  await page.getByTestId("rev-quick-find-city").click();
  await expect(page.getByTestId("rev-quick-city-results")).toBeVisible();
  expect(citySearchCalls).toBe(1);
  expect(poiSearchCalls).toBe(0);

  // The geocoder center is CAMERA ONLY. The user must independently select a
  // public search center, here via a strict OSM link without map tile traffic.
  await page.getByText("地图打不开？用公开 OpenStreetMap 链接定位").click();
  await page.locator("#rev-quick-map-link").fill("https://www.openstreetmap.org/#map=13/25.7/116.75");
  await page.getByTestId("rev-quick-apply-map-link").click();
  await expect(page.getByTestId("rev-quick-category")).toBeVisible();
  expect(poiSearchCalls).toBe(0);

  await page.getByTestId("rev-quick-find-places").click();
  await expect(page.getByTestId("rev-quick-results")).toBeVisible();
  expect(poiSearchCalls).toBe(1);
  await page.getByTestId(`rev-quick-select-${firstId}`).click();
  await page.getByTestId(`rev-quick-select-${secondId}`).click();
  await page.getByTestId("rev-quick-save").click();
  await expect(page.getByTestId("rev-quick-walk")).toBeVisible();
  await page.getByRole("button", { name: "开始散步" }).click();
  await expect(page.getByText("正前往第一站", { exact: false })).toBeVisible();

  await page.reload();
  await expect(page.getByTestId("rev-quick-walk")).toBeVisible();
  await expect(page.getByText("正前往第一站", { exact: false })).toBeVisible();
});
