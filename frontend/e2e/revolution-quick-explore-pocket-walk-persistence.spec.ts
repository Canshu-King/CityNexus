import { expect, test, type Route } from "@playwright/test";

test.use({ viewport: { width: 390, height: 844 }, hasTouch: true, serviceWorkers: "block" });

const journeyId = "00000000-0000-4000-8000-000000000239";
const root = `**/api/v1/journeys/${journeyId}`;

function json(route: Route, value: object) {
  return route.fulfill({
    status: 200,
    contentType: "application/json",
    body: JSON.stringify(value),
  });
}

test("TEST_FIXTURE shortlist GET restores a saved Pocket Walk after refresh", async ({ page }) => {
  let shortlistReads = 0;
  let serverHasSavedWalk = false;
  let apiPostCalls = 0;

  const savedWalk = {
    status: "POCKET_WALK_SAVED",
    pocket_walk_id: "TEST_FIXTURE_POCKET_WALK_1",
    revision: 2,
    journey_id: journeyId,
    first_stop: { name: "TEST_FIXTURE · 河畔步道", shortlist_id: "TEST_FIXTURE_FIRST" },
    second_stop: { name: "TEST_FIXTURE · 城市公园", shortlist_id: "TEST_FIXTURE_SECOND" },
    plan_version_id: null,
    go_progress: {
      state: "HEADING_TO_FIRST",
      progress_revision: 1,
      pocket_walk_revision: 2,
      progress_class: "USER_REPORTED_PROGRESS",
      physical_arrival_state: "NOT_PHYSICAL_ARRIVAL_PROVEN",
    },
  };

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

  page.on("request", (request) => {
    const url = new URL(request.url());
    if (request.method() === "POST" && url.pathname.startsWith("/api/v1/")) apiPostCalls += 1;
  });

  // Unlisted API requests are aborted. The spec only serves local TEST_FIXTURE reads.
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
  await page.route(`${root}/bootstrap-shortlist`, async (route) => {
    expect(route.request().method()).toBe("GET");
    shortlistReads += 1;
    await json(route, {
      journey_id: journeyId,
      limit: 3,
      items: [],
      resume: null,
      pocket_walk: serverHasSavedWalk ? savedWalk : null,
      fixture_mode: "TEST_FIXTURE",
    });
  });

  const firstShortlistRead = page.waitForResponse((response) =>
    response.request().method() === "GET" && response.url().includes(`/journeys/${journeyId}/bootstrap-shortlist`),
  );
  await page.goto("/revolution");
  const firstResponse = await firstShortlistRead;
  expect((await firstResponse.json()).pocket_walk).toBeNull();
  await expect(page.getByTestId("rev-quick-area")).toBeVisible();
  expect(shortlistReads).toBe(1);

  // The earlier QuickExplore flow covers selecting two fixture candidates, saving them with the
  // discovery receipt, and showing the save/GO response. Here the fixture is already persisted;
  // this isolated assertion checks that a fresh page read restores that server-owned state.
  serverHasSavedWalk = true;
  const restoredShortlistRead = page.waitForResponse((response) =>
    response.request().method() === "GET" && response.url().includes(`/journeys/${journeyId}/bootstrap-shortlist`),
  );
  await page.reload({ waitUntil: "domcontentloaded" });
  const restoredResponse = await restoredShortlistRead;
  const restoredBody = await restoredResponse.json();
  expect(restoredBody.pocket_walk.pocket_walk_id).toBe("TEST_FIXTURE_POCKET_WALK_1");
  expect(shortlistReads).toBe(2);

  const walk = page.getByTestId("rev-quick-walk");
  await expect(walk).toBeVisible();
  await expect(walk).toContainText("TEST_FIXTURE · 河畔步道");
  await expect(walk).toContainText("TEST_FIXTURE · 城市公园");
  await expect(walk).toContainText("正前往第一站");
  expect(apiPostCalls).toBe(0);
});
