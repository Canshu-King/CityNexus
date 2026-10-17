import { expect, test, type Route } from "@playwright/test";

test.use({ viewport: { width: 390, height: 844 }, hasTouch: true, serviceWorkers: "block" });

const journeyId = "00000000-0000-4000-8000-000000000242";
const root = `**/api/v1/journeys/${journeyId}`;
const westLakeLink = "https://www.openstreetmap.org/#map=15/30.243/120.149";

function json(route: Route, value: object) {
  return route.fulfill({
    status: 200,
    contentType: "application/json",
    body: JSON.stringify(value),
  });
}

test("TEST_FIXTURE map-link center is identified as the selected search area on mobile", async ({ page }) => {
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

  // All API traffic stays inside this fixture; no geocoder, POI, AI, or payment service is reached.
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
    status: "READY",
    reason_code: "READY",
    provider_grade: "TEST_PROVIDER",
    capability_state: "TEST_CAPABLE",
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
  await page.route(`${root}/bootstrap-city-search`, (route) => {
    citySearchCalls += 1;
    return route.abort();
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
  const area = page.getByTestId("rev-quick-area");
  const mapLinkDisclosure = area.locator("details.rev-quick-internals");
  await mapLinkDisclosure.locator("summary").click();
  await page.getByLabel("公开地图链接").fill(westLakeLink);
  const applyLink = page.getByTestId("rev-quick-apply-map-link");
  await expect(applyLink).toBeVisible();
  const applyBox = await applyLink.boundingBox();
  expect(applyBox).not.toBeNull();
  expect(applyBox!.height).toBeGreaterThanOrEqual(44);
  await applyLink.click();

  const category = page.getByTestId("rev-quick-category");
  await expect(category).toBeVisible();
  const journeyTitle = page.getByTestId("rev-mobile-screen-explore").getByRole("heading", { level: 1 });
  await expect(journeyTitle).toBeVisible();
  await expect(journeyTitle).not.toContainText("连城");
  const storedJourneyCityName = await page.evaluate(() => {
    const storedJourney = window.localStorage.getItem("citynexus.revolution.firstlook.journey");
    return storedJourney
      ? (JSON.parse(storedJourney) as { cityName?: string }).cityName ?? null
      : null;
  });
  expect(storedJourneyCityName).toBe("连城");
  const exploration = page.getByTestId("rev-quick-explore");
  const currentLocationHeading = exploration.getByRole("heading", { level: 2 });
  const areaNotice = category.locator(".rev-quick-disclosure");
  await expect(currentLocationHeading).toContainText("本次探索位置");
  await expect(currentLocationHeading).toContainText("30.243");
  await expect(currentLocationHeading).toContainText("120.149");
  await expect(currentLocationHeading).not.toContainText("连城");
  await expect(areaNotice).toContainText("搜索按你选择的区域进行");
  await expect(areaNotice).not.toContainText("连城");
  await areaNotice.scrollIntoViewIfNeeded();
  await expect(areaNotice).toBeInViewport();

  const searchButton = category.getByTestId("rev-quick-find-places");
  await expect(searchButton).toBeVisible();
  await searchButton.scrollIntoViewIfNeeded();
  await expect(searchButton).toBeInViewport();
  const searchBox = await searchButton.boundingBox();
  expect(searchBox).not.toBeNull();
  expect(searchBox!.height).toBeGreaterThanOrEqual(44);

  expect(citySearchCalls).toBe(0);
  expect(poiSearchCalls).toBe(0);
  expect(aiCalls).toBe(0);
});
