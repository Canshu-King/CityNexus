import { expect, test, type Route } from "@playwright/test";

test.use({ viewport: { width: 390, height: 844 }, hasTouch: true, serviceWorkers: "block" });

const journey = "00000000-0000-4000-8000-000000000225";
const root = `**/api/v1/journeys/${journey}`;
const candidateA = "fixture-candidate-a";
const candidateB = "fixture-candidate-b";

async function json(route: Route, value: unknown) {
  await route.fulfill({
    status: 200,
    contentType: "application/json",
    body: JSON.stringify(value),
  });
}

test("TEST_FIXTURE reorders, clears, reselects, and saves two stops in the final A/B order", async ({ page }) => {
  let citySearchCalls = 0;
  let discoveryCalls = 0;
  const saveRequests: Array<Record<string, unknown>> = [];

  const pocket = () => ({
    status: "POCKET_WALK_SAVED",
    pocket_walk_id: "test-fixture-pocket-walk",
    revision: 1,
    journey_id: journey,
    first_stop: { name: "TEST_FIXTURE A", shortlist_id: "fixture-shortlist-a" },
    second_stop: { name: "TEST_FIXTURE B", shortlist_id: "fixture-shortlist-b" },
    plan_version_id: null,
    go_progress: {
      state: "NOT_STARTED",
      progress_revision: 0,
      pocket_walk_revision: 1,
      progress_class: "USER_REPORTED_PROGRESS",
      physical_arrival_state: "NOT_PHYSICAL_ARRIVAL_PROVEN",
    },
  });

  await page.addInitScript((id) => {
    window.sessionStorage.setItem("citynexus.traveler.bearer", "TEST_FIXTURE_SIGNED_MEMBER");
    window.localStorage.setItem("citynexus.locale", "zh-CN");
    window.localStorage.setItem("citynexus.revolution.firstlook.journey", JSON.stringify({
      id,
      cityCode: "CN-RV-TEST-FIXTURE",
      cityName: "连城",
      status: "DRAFT",
    }));
  }, journey);

  await page.route("**/api/v1/**", (route) => route.abort());
  await page.route("https://tile.openstreetmap.org/**", (route) => route.abort());
  await page.route("**/api/v1/agent/runtime-status", (route) => json(route, {
    runtime_identity: "TEST_FIXTURE",
    hermes_compat_configured: false,
    ai_state: "DISABLED",
    fixture_mode: "TEST_FIXTURE",
  }));
  await page.route(`${root}/bootstrap-discovery/readiness`, (route) => json(route, {
    journey_id: journey,
    provider: "overpass",
    provider_name: "TEST_FIXTURE",
    expected_recipient: "TEST_FIXTURE",
    status: "READY",
    reason_code: "READY",
    provider_grade: "TEST_PROVIDER",
    capability_state: "TEST_CAPABLE",
    external_request_allowed: true,
    test_only: true,
  }));
  await page.route(`${root}/bootstrap-shortlist`, (route) => json(route, {
    journey_id: journey,
    limit: 3,
    items: [],
    resume: null,
    pocket_walk: null,
  }));
  await page.route(`${root}/bootstrap-city-search`, async (route) => {
    citySearchCalls += 1;
    const payload = route.request().postDataJSON();
    expect(payload.query).toBe("连城");
    await json(route, {
      journey_id: journey,
      status: "CITY_RESULTS",
      query: "连城",
      provider_attempts: [],
      results: [{
        result_id: "fixture-city-result",
        name: "TEST_FIXTURE 城区",
        display_name: "TEST_FIXTURE 城区",
        provider: "test",
        provider_provenance: "TEST_PROVIDER",
        latitude: 25.7,
        longitude: 116.75,
        coordinate_system: "WGS84",
        confidence: "CITY_CENTROID_UNCERTAIN",
        selection_state: "CAMERA_ONLY_TAP_REQUIRED",
      }],
    });
  });
  await page.route(`${root}/bootstrap-discovery`, async (route) => {
    discoveryCalls += 1;
    const payload = route.request().postDataJSON();
    expect(payload.provider_consent).toBe(true);
    expect(payload.latitude).toBe(25.7);
    expect(payload.longitude).toBe(116.75);
    await json(route, {
      journey_id: journey,
      status: "LIVE_RESULTS",
      source_kind: "MANUAL_PUBLIC_CENTER",
      provider: "overpass",
      provider_provenance: "TEST_PROVIDER",
      receipt_id: "test-fixture-receipt-a-b",
      attempts: [{ http_status: 200 }],
      candidates: [
        {
          candidate_id: candidateA,
          name: "TEST_FIXTURE A",
          category: "park",
          source_url: "https://www.openstreetmap.org/node/fixture-a",
          provider_provenance: "TEST_PROVIDER",
        },
        {
          candidate_id: candidateB,
          name: "TEST_FIXTURE B",
          category: "park",
          source_url: "https://www.openstreetmap.org/node/fixture-b",
          provider_provenance: "TEST_PROVIDER",
        },
      ],
    });
  });
  await page.route(`${root}/bootstrap-discovery/pocket-walk`, async (route) => {
    saveRequests.push(route.request().postDataJSON() as Record<string, unknown>);
    await json(route, { pocket_walk: pocket(), items: [] });
  });

  await page.goto("/revolution");
  const quickExplore = page.getByTestId("rev-quick-explore");
  await expect(quickExplore).toBeVisible();
  await quickExplore.getByTestId("rev-quick-find-city").click();
  await expect(quickExplore.getByTestId("rev-quick-city-results")).toBeVisible();
  await quickExplore.getByTestId("rev-quick-city-results").getByRole("button").first().click();
  await quickExplore.getByTestId("rev-quick-use-approx-center").click();
  await quickExplore.getByTestId("rev-quick-category").getByTestId("rev-quick-find-places").click();

  const results = quickExplore.getByTestId("rev-quick-results");
  await expect(results).toBeVisible();
  expect(citySearchCalls).toBe(1);
  expect(discoveryCalls).toBe(1);
  await expect(results.getByText("尚未选地点。点选一处加入第 1 站，再点另一处加入第 2 站。", { exact: true })).toBeVisible();
  const selectA = results.getByTestId(`rev-quick-select-${candidateA}`);
  const selectB = results.getByTestId(`rev-quick-select-${candidateB}`);
  await expect(selectA).toContainText("＋ 选择地点");
  await expect(selectA).toHaveAttribute("aria-pressed", "false");
  await expect(selectB).toContainText("＋ 选择地点");
  await expect(selectB).toHaveAttribute("aria-pressed", "false");

  await selectA.click();
  await expect(results.getByText("第 1 站已选；点另一处加入第 2 站。", { exact: true })).toBeVisible();
  await expect(selectA).toContainText("第一站");
  await expect(selectA).toHaveAttribute("aria-pressed", "true");
  await expect(selectB).toContainText("＋ 选择地点");
  await expect(selectB).toHaveAttribute("aria-pressed", "false");

  await selectB.click();
  await expect(results.getByText("第 1 站和第 2 站已选；点选卡片可调整选择。", { exact: true })).toBeVisible();
  await expect(selectA).toContainText("第一站");
  await expect(selectA).toHaveAttribute("aria-pressed", "true");
  await expect(selectB).toContainText("第二站");
  await expect(selectB).toHaveAttribute("aria-pressed", "true");
  await expect(results.getByTestId("rev-quick-save")).toHaveText("保存这两个地点为我的私人散步 →");
  await expect(results).toContainText("第一站：TEST_FIXTURE A");
  await expect(results).toContainText("第二站：TEST_FIXTURE B");
  expect(saveRequests).toHaveLength(0);

  await selectA.click();
  await expect(results.getByText("第 1 站已选；点另一处加入第 2 站。", { exact: true })).toBeVisible();
  await expect(selectB).toContainText("第一站");
  await expect(selectB).toHaveAttribute("aria-pressed", "true");
  await expect(selectA).toContainText("＋ 选择地点");
  await expect(selectA).toHaveAttribute("aria-pressed", "false");
  await expect(selectA).not.toContainText("第二站");
  await expect(selectB).not.toContainText("第二站");
  await expect(results.getByTestId("rev-quick-save")).toHaveCount(0);
  expect(saveRequests).toHaveLength(0);

  // Clear the remaining B-first choice before selecting A then B again.
  await selectB.click();
  await expect(results.getByText("尚未选地点。点选一处加入第 1 站，再点另一处加入第 2 站。", { exact: true })).toBeVisible();
  await expect(selectA).toHaveAttribute("aria-pressed", "false");
  await expect(selectB).toHaveAttribute("aria-pressed", "false");
  await expect(results.getByTestId("rev-quick-save")).toHaveCount(0);

  await selectA.click();
  await expect(selectA).toContainText("第一站");
  await selectB.click();
  await expect(results.getByText("第 1 站和第 2 站已选；点选卡片可调整选择。", { exact: true })).toBeVisible();
  await expect(selectA).toContainText("第一站");
  await expect(selectB).toContainText("第二站");
  await expect(selectA).toHaveAttribute("aria-pressed", "true");
  await expect(selectB).toHaveAttribute("aria-pressed", "true");
  await expect(results.getByTestId("rev-quick-save")).toHaveText("保存这两个地点为我的私人散步 →");

  await results.getByTestId("rev-quick-save").click();
  await expect(quickExplore.getByTestId("rev-quick-walk")).toBeVisible();
  expect(saveRequests).toHaveLength(1);
  expect(saveRequests[0]).toMatchObject({
    receipt_id: "test-fixture-receipt-a-b",
    first_candidate_id: candidateA,
    second_candidate_id: candidateB,
    max_walk_minutes: null,
  });
  await expect(quickExplore.getByTestId("rev-quick-walk")).toContainText("TEST_FIXTURE A");
  await expect(quickExplore.getByTestId("rev-quick-walk")).toContainText("TEST_FIXTURE B");
});
