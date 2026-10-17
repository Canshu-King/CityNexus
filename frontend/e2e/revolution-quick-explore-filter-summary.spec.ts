import { expect, test, type Page, type Route } from "@playwright/test";

test.use({ viewport: { width: 390, height: 844 }, hasTouch: true });

const journey = "00000000-0000-4000-8000-000000000220";
const root = `**/api/v1/journeys/${journey}`;

function json(route: Route, object: object) {
  return route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(object) });
}

async function openZeroResult(page: Page, filterSummary?: object) {
  await page.addInitScript((id) => {
    window.sessionStorage.setItem("citynexus.traveler.bearer", "signed-only-fixture-token");
    window.localStorage.setItem("citynexus.revolution.firstlook.journey", JSON.stringify({
      id,
      cityCode: "CN-RV-FILTER-SUMMARY-TEST",
      cityName: "连城",
      status: "DRAFT",
    }));
  }, journey);
  await page.route("**/api/v1/agent/runtime-status", (route) => json(route, {
    runtime_identity: "UNCONFIGURED",
    hermes_compat_configured: false,
    ai_state: "DISABLED",
  }));
  await page.route(`${root}/bootstrap-discovery/readiness`, (route) => json(route, {
    journey_id: journey,
    provider: "photon",
    provider_name: "Photon test fixture",
    expected_recipient: "TEST_PROVIDER",
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
  await page.route(`${root}/bootstrap-city-search`, (route) => json(route, {
    journey_id: journey,
    status: "CITY_RESULTS",
    query: "连城",
    provider_attempts: [],
    results: [{
      result_id: "filter-summary-city-result",
      name: "连城县",
      display_name: "连城县（测试地名结果）",
      provider: "test",
      provider_provenance: "TEST_PROVIDER",
      latitude: 25.7,
      longitude: 116.75,
      coordinate_system: "WGS84",
      confidence: "CITY_CENTROID_UNCERTAIN",
      selection_state: "CAMERA_ONLY_TAP_REQUIRED",
    }],
  }));
  await page.route(`${root}/bootstrap-discovery`, (route) => json(route, {
    journey_id: journey,
    status: "LIVE_ZERO_RESULTS",
    result_state: "ZERO",
    source_kind: "MANUAL_PUBLIC_CENTER",
    provider: "photon",
    provider_provenance: "TEST_PROVIDER",
    receipt_id: "filter-summary-receipt",
    attempts: [{ provider_key: "photon", answered: true, elements: 3, returned: 3 }],
    ...(filterSummary ? { filter_summary: filterSummary } : {}),
    candidates: [],
  }));
  await page.route("https://tile.openstreetmap.org/**", (route) => route.abort());

  await page.goto("/revolution");
  const quickExplore = page.getByTestId("rev-quick-explore");
  await expect(quickExplore).toBeVisible();
  await quickExplore.getByTestId("rev-quick-find-city").click();
  await expect(quickExplore.getByTestId("rev-quick-city-results")).toContainText("连城县");
  await quickExplore.getByRole("button", { name: /连城县.*2\.5公里/ }).click();
  await quickExplore.getByTestId("rev-quick-use-approx-center").click();
  await quickExplore.getByTestId("rev-quick-category").getByTestId("rev-quick-find-places").click();
  const results = quickExplore.getByTestId("rev-quick-results");
  if (filterSummary) {
    await expect(quickExplore.getByTestId("rev-quick-filter-result")).toHaveText("地图返回 3 条，符合条件 0 处。");
  } else {
    await expect(results).toContainText("没有匹配地点。换个类别或搜索区域。");
  }
  await expect(results).not.toContainText("连城县");
  await expect(results).not.toContainText("25.7");
  await expect(results).not.toContainText("116.75");
  return quickExplore;
}

test("technical information shows only server filter counts", async ({ page }) => {
  const quickExplore = await openZeroResult(page, {
    raw_count: 3,
    accepted_count: 0,
    rejected_by_reason: {
      provider_mismatch: 0,
      invalid_identity: 0,
      missing_name: 1,
      invalid_coordinates: 0,
      invalid_distance: 0,
      out_of_radius: 2,
      restricted_access: 0,
      duplicate: 0,
    },
  });
  const results = quickExplore.getByTestId("rev-quick-results");
  await expect(results).not.toContainText("没有匹配地点");
  const technicalInfo = quickExplore.locator(".rev-quick-internals");
  await technicalInfo.locator("summary").click();

  const filterSummary = technicalInfo.getByTestId("rev-quick-filter-summary");
  await expect(filterSummary).toHaveText("原始候选：3 条 · 可用地点：0 处");
  await expect(technicalInfo).not.toContainText("rejected_by_reason");
  await expect(technicalInfo).not.toContainText("missing_name");
  await expect(technicalInfo).not.toContainText("out_of_radius");
});

test("technical information stays unchanged when filter counts are absent", async ({ page }) => {
  const quickExplore = await openZeroResult(page);
  const results = quickExplore.getByTestId("rev-quick-results");
  await expect(results.getByTestId("rev-quick-filter-result")).toHaveCount(0);
  await expect(results).not.toContainText("地图返回");
  await expect(results).not.toContainText("符合条件");
  const technicalInfo = quickExplore.locator(".rev-quick-internals");
  await technicalInfo.locator("summary").click();

  await expect(technicalInfo).toContainText("数据状态：LIVE_ZERO_RESULTS · TEST_PROVIDER");
  await expect(technicalInfo).toContainText("地点来源：TEST_PROVIDER。私人路线与进度来自当前行程。");
  await expect(technicalInfo.getByTestId("rev-quick-filter-summary")).toHaveCount(0);
});
