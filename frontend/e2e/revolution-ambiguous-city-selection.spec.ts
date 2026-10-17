import { expect, test, type Route } from "@playwright/test";

test.use({ viewport: { width: 390, height: 844 }, hasTouch: true, serviceWorkers: "block" });

const journeyId = "00000000-0000-4000-8000-000000000241";
const root = `**/api/v1/journeys/${journeyId}`;
const promptText = "我们想轻松散步，优先安静绿地。";

function json(route: Route, value: object) {
  return route.fulfill({
    status: 200,
    contentType: "application/json",
    body: JSON.stringify(value),
  });
}

test("ambiguous Springfield requires a manual city choice before POI discovery", async ({ page }) => {
  let citySearchCalls = 0;
  let poiSearchCalls = 0;
  let aiCalls = 0;

  await page.addInitScript((id) => {
    window.sessionStorage.setItem("citynexus.traveler.bearer", "TEST_ONLY_SIGNED_FIXTURE_TOKEN");
    window.localStorage.setItem("citynexus.locale", "zh-CN");
    window.localStorage.setItem("citynexus.revolution.firstlook.journey", JSON.stringify({
      id,
      cityCode: "CN-RV-TEST",
      cityName: "连城",
      status: "DRAFT",
    }));
  }, journeyId);

  // Every API call is intercepted. Unlisted requests and any accidental AI/POI calls are blocked.
  await page.route("**/api/v1/**", (route) => route.abort());
  await page.route("**/api/v1/agent/runtime-status", (route) => json(route, {
    runtime_identity: "TEST_FIXTURE",
    hermes_compat_configured: false,
    ai_state: "DISABLED",
    fixture_mode: "TEST_FIXTURE",
  }));
  await page.route(`${root}/bootstrap-discovery/readiness`, (route) => json(route, {
    journey_id: journeyId,
    provider: "overpass",
    provider_name: "TEST_FIXTURE",
    expected_recipient: "TEST_FIXTURE",
    status: "BLOCKED",
    reason_code: "TEST_FIXTURE_PROVIDER_DISABLED",
    provider_grade: "TEST_PROVIDER",
    capability_state: "LIVE_BLOCKED",
    external_request_allowed: false,
    test_only: true,
  }));
  await page.route(`${root}/bootstrap-shortlist`, (route) => json(route, {
    journey_id: journeyId,
    limit: 3,
    items: [],
    resume: null,
    pocket_walk: null,
  }));
  await page.route(`${root}/bootstrap-city-search`, async (route) => {
    citySearchCalls += 1;
    expect(route.request().method()).toBe("POST");
    const body = route.request().postDataJSON() as { query?: unknown; provider_consent?: unknown };
    expect(body.query).toBe("Springfield");
    expect(body.provider_consent).toBe(true);
    await json(route, {
      journey_id: journeyId,
      status: "CITY_RESULTS",
      query: "Springfield",
      provider_provenance: "TEST_PROVIDER",
      provider_attempts: [],
      results: [
        {
          result_id: "TEST_FIXTURE_SPRINGFIELD_IL",
          name: "Springfield",
          display_name: "Springfield, Sangamon County, Illinois, United States",
          provider: "TEST_FIXTURE",
          provider_provenance: "TEST_PROVIDER",
          latitude: 39.7983,
          longitude: -89.6540,
          coordinate_system: "WGS84",
          confidence: "CITY_CENTROID_UNCERTAIN",
          selection_state: "CAMERA_ONLY_TAP_REQUIRED",
        },
        {
          result_id: "TEST_FIXTURE_SPRINGFIELD_MO",
          name: "Springfield",
          display_name: "Springfield, Greene County, Missouri, United States",
          provider: "TEST_FIXTURE",
          provider_provenance: "TEST_PROVIDER",
          latitude: 37.2089,
          longitude: -93.2923,
          coordinate_system: "WGS84",
          confidence: "CITY_CENTROID_UNCERTAIN",
          selection_state: "CAMERA_ONLY_TAP_REQUIRED",
        },
      ],
    });
  });
  await page.route(`${root}/bootstrap-discovery`, (route) => {
    poiSearchCalls += 1;
    return route.abort();
  });
  await page.route(`${root}/trial-ai-discovery`, (route) => {
    aiCalls += 1;
    return route.abort();
  });

  await page.goto("/revolution");
  const cityInput = page.getByLabel("城市或地区");
  const prompt = page.getByLabel("写下你的想法");
  await expect(cityInput).toBeVisible();
  await prompt.fill(promptText);
  await cityInput.fill("Springfield");
  await page.getByTestId("rev-quick-find-city").click();

  const results = page.getByTestId("rev-quick-city-results");
  await expect(results).toBeVisible();
  await expect(results).toContainText("Springfield, Sangamon County, Illinois, United States");
  await expect(results).toContainText("Springfield, Greene County, Missouri, United States");
  await expect(cityInput).toHaveValue("Springfield");
  await expect(prompt).toHaveValue(promptText);
  await expect(page.getByText("已经找到公开地区。选一个结果后可以直接按“从这一带附近找”，地图是可选的。")).toBeVisible();
  expect(citySearchCalls).toBe(1);
  expect(poiSearchCalls).toBe(0);
  await expect(page.getByTestId("rev-quick-use-approx-center")).toHaveCount(0);
  await expect(page.getByTestId("rev-quick-category")).toHaveCount(0);

  const options = results.getByRole("button");
  await expect(options).toHaveCount(2);
  for (const index of [0, 1]) {
    const option = options.nth(index);
    await expect(option).toBeVisible();
    const box = await option.boundingBox();
    expect(box).not.toBeNull();
    expect(box!.height).toBeGreaterThanOrEqual(44);
  }

  const illinois = results.getByRole("button", { name: /Springfield, Sangamon County, Illinois/ });
  await illinois.scrollIntoViewIfNeeded();
  await expect(illinois).toBeInViewport();
  await illinois.click();
  await expect(page.getByTestId("rev-quick-use-approx-center")).toBeVisible();
  await expect(page.getByTestId("rev-quick-use-approx-center")).toHaveText("直接从这片地区附近找 →");
  await expect(page.getByTestId("rev-quick-category")).toHaveCount(0);
  await expect(prompt).toHaveValue(promptText);
  await expect(page.getByText("已选中公开地区的大致中心。你可以直接从附近查找，也可以先打开地图微调。")).toBeVisible();
  expect(poiSearchCalls).toBe(0);

  await page.getByTestId("rev-quick-use-approx-center").click();
  await expect(page.getByTestId("rev-quick-category")).toBeVisible();
  expect(poiSearchCalls).toBe(0);

  await page.getByTestId("rev-quick-category").getByRole("button", { name: "换一个位置" }).click();
  await expect(cityInput).toHaveValue("Springfield");
  await expect(prompt).toHaveValue(promptText);
  expect(citySearchCalls).toBe(1);
  expect(poiSearchCalls).toBe(0);
  expect(aiCalls).toBe(0);
});
