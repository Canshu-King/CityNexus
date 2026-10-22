import { expect, test, type Route } from "@playwright/test";

test.use({ viewport: { width: 390, height: 844 }, hasTouch: true });

const journey = "00000000-0000-4000-8000-000000000219";
const candidateId = "partial-live-place-1";
const root = `**/api/v1/journeys/${journey}`;

function json(route: Route, object: object) {
  return route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(object) });
}

test("one live candidate stays partial and category/area actions do not search", async ({ page }) => {
  let citySearchCalls = 0;
  let discoveryCalls = 0;
  let tileRequests = 0;

  await page.addInitScript((id) => {
    window.sessionStorage.setItem("citynexus.traveler.bearer", "signed-only-fixture-token");
    window.localStorage.setItem("citynexus.revolution.firstlook.journey", JSON.stringify({
      id,
      cityCode: "CN-RV-PARTIAL-TEST",
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
    provider: "overpass",
    provider_name: "R87 partial-result fixture",
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
  await page.route(`${root}/bootstrap-city-search`, async (route) => {
    citySearchCalls += 1;
    expect(route.request().postDataJSON().provider_consent).toBe(true);
    await json(route, {
      journey_id: journey,
      status: "CITY_RESULTS",
      query: "连城",
      provider_attempts: [],
      results: [{
        result_id: "partial-city-result",
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
    });
  });
  await page.route(`${root}/bootstrap-discovery`, async (route) => {
    discoveryCalls += 1;
    const request = route.request().postDataJSON();
    expect(request.provider_consent).toBe(true);
    expect(request.source_kind).toBe("MANUAL_PUBLIC_CENTER");
    await json(route, {
      journey_id: journey,
      status: "LIVE_RESULTS",
      source_kind: "MANUAL_PUBLIC_CENTER",
      provider: "overpass",
      provider_provenance: "TEST_PROVIDER",
      receipt_id: `partial-receipt-${discoveryCalls}`,
      attempts: [{ http_status: 200 }],
      candidates: [{
        candidate_id: candidateId,
        name: "TEST_FIXTURE 连城公园甲",
        category: "park",
        source_url: "https://www.openstreetmap.org/node/21901",
        provider_provenance: "TEST_PROVIDER",
      }],
    });
  });
  await page.route("https://tile.openstreetmap.org/**", (route) => {
    tileRequests += 1;
    return route.abort();
  });

  await page.goto("/revolution");
  const quickExplore = page.getByTestId("rev-quick-explore");
  await expect(quickExplore).toBeVisible();
  expect(citySearchCalls).toBe(0);
  expect(discoveryCalls).toBe(0);
  expect(tileRequests).toBe(0);

  await quickExplore.getByTestId("rev-quick-find-city").click();
  await expect(quickExplore.getByTestId("rev-quick-city-results")).toContainText("连城县");
  expect(citySearchCalls).toBe(1);
  await quickExplore.getByRole("button", { name: /连城县.*2\.5公里/ }).click();
  await quickExplore.getByTestId("rev-quick-use-approx-center").click();
  const category = quickExplore.getByTestId("rev-quick-category");
  await expect(category).toBeVisible();

  await category.getByTestId("rev-quick-find-places").click();
  const results = quickExplore.getByTestId("rev-quick-results");
  await expect(results.getByTestId("rev-quick-partial-result")).toHaveText("已找到 1 处；换类别或地图位置继续找第二处。");
  await expect(results).toContainText("TEST_FIXTURE 连城公园甲");
  await expect(results.locator("[data-testid^='rev-quick-select-']")).toHaveCount(1);
  await expect(results.getByTestId("rev-quick-save")).toHaveCount(0);
  await expect(results.locator(".rev-quick-disclosure")).toContainText("测试来源");
  await expect(quickExplore.locator(".rev-quick-header")).not.toContainText("选两个真实返回的地点");
  expect(discoveryCalls).toBe(1);

  await results.getByRole("button", { name: "换个兴趣重找" }).click();
  await expect(quickExplore.getByTestId("rev-quick-category")).toBeVisible();
  expect(discoveryCalls).toBe(1);
  expect(citySearchCalls).toBe(1);

  await quickExplore.getByTestId("rev-quick-find-places").click();
  await expect(quickExplore.getByTestId("rev-quick-partial-result")).toHaveText("已找到 1 处；换类别或地图位置继续找第二处。");
  expect(discoveryCalls).toBe(2);
  await quickExplore.getByTestId("rev-quick-results").getByRole("button", { name: "换地图位置" }).click();
  const area = quickExplore.getByTestId("rev-quick-area");
  await expect(area).toBeVisible();
  await expect(area).toContainText("已找到：连城县");
  expect(discoveryCalls).toBe(2);
  expect(citySearchCalls).toBe(1);
  expect(tileRequests).toBe(0);
});

test("320x844 keeps the partial prompt and both return actions within the viewport", async ({ page }) => {
  await page.setViewportSize({ width: 320, height: 844 });
  let citySearchCalls = 0;
  let discoveryCalls = 0;

  await page.addInitScript((id) => {
    window.sessionStorage.setItem("citynexus.traveler.bearer", "signed-only-fixture-token");
    window.localStorage.setItem("citynexus.revolution.firstlook.journey", JSON.stringify({
      id,
      cityCode: "CN-RV-PARTIAL-320-TEST",
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
    provider: "overpass",
    provider_name: "R87 partial-result fixture",
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
  await page.route(`${root}/bootstrap-city-search`, async (route) => {
    citySearchCalls += 1;
    await json(route, {
      journey_id: journey,
      status: "CITY_RESULTS",
      query: "连城",
      provider_attempts: [],
      results: [{
        result_id: "partial-city-result-320",
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
    });
  });
  await page.route(`${root}/bootstrap-discovery`, async (route) => {
    discoveryCalls += 1;
    await json(route, {
      journey_id: journey,
      status: "LIVE_RESULTS",
      source_kind: "MANUAL_PUBLIC_CENTER",
      provider: "overpass",
      provider_provenance: "TEST_PROVIDER",
      receipt_id: `partial-receipt-320-${discoveryCalls}`,
      attempts: [{ http_status: 200 }],
      candidates: [{
        candidate_id: candidateId,
        name: "TEST_FIXTURE 连城公园甲",
        category: "park",
        source_url: "https://www.openstreetmap.org/node/21901",
        provider_provenance: "TEST_PROVIDER",
      }],
    });
  });

  await page.goto("/revolution");
  const quickExplore = page.getByTestId("rev-quick-explore");
  await expect(quickExplore).toBeVisible();
  await quickExplore.getByTestId("rev-quick-find-city").click();
  await expect(quickExplore.getByTestId("rev-quick-city-results")).toContainText("连城县");
  expect(citySearchCalls).toBe(1);
  await quickExplore.getByRole("button", { name: /连城县.*2\.5公里/ }).click();
  await quickExplore.getByTestId("rev-quick-use-approx-center").click();
  await quickExplore.getByTestId("rev-quick-category").getByTestId("rev-quick-find-places").click();

  const results = quickExplore.getByTestId("rev-quick-results");
  const partialPrompt = results.getByTestId("rev-quick-partial-result");
  const categoryAction = results.getByRole("button", { name: "换个兴趣重找" });
  const areaAction = results.getByRole("button", { name: "换地图位置" });
  await expect(partialPrompt).toHaveText("已找到 1 处；换类别或地图位置继续找第二处。");
  await expect(categoryAction).toBeVisible();
  await expect(categoryAction).toBeEnabled();
  await expect(areaAction).toBeVisible();
  await expect(areaAction).toBeEnabled();

  const promptBounds = await partialPrompt.boundingBox();
  const categoryBounds = await categoryAction.boundingBox();
  const areaBounds = await areaAction.boundingBox();
  for (const bounds of [promptBounds, categoryBounds, areaBounds]) {
    expect(bounds?.x ?? -1).toBeGreaterThanOrEqual(0);
    expect((bounds?.x ?? 0) + (bounds?.width ?? 0)).toBeLessThanOrEqual(320);
  }
  for (const bounds of [categoryBounds, areaBounds]) {
    expect(bounds?.width ?? 0).toBeGreaterThanOrEqual(44);
    expect(bounds?.height ?? 0).toBeGreaterThanOrEqual(44);
  }
  const resultPaneWidth = await results.evaluate((element) => ({
    clientWidth: element.clientWidth,
    scrollWidth: element.scrollWidth,
  }));
  expect(resultPaneWidth.scrollWidth).toBeLessThanOrEqual(resultPaneWidth.clientWidth);
  expect(discoveryCalls).toBe(1);

  await categoryAction.click();
  await expect(quickExplore.getByTestId("rev-quick-category")).toBeVisible();
  expect(discoveryCalls).toBe(1);
  await quickExplore.getByTestId("rev-quick-find-places").click();
  await expect(quickExplore.getByTestId("rev-quick-partial-result")).toBeVisible();
  expect(discoveryCalls).toBe(2);

  await quickExplore.getByTestId("rev-quick-results").getByRole("button", { name: "换地图位置" }).click();
  const area = quickExplore.getByTestId("rev-quick-area");
  await expect(area).toBeVisible();
  await expect(area).toContainText("已找到：连城县");
  expect(discoveryCalls).toBe(2);
  expect(citySearchCalls).toBe(1);
});
