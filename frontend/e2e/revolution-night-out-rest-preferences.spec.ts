import { expect, test, type Route } from "@playwright/test";

test.use({ viewport: { width: 390, height: 844 }, hasTouch: true, serviceWorkers: "block" });

const journeyId = "00000000-0000-4000-8000-000000000238";
const root = `**/api/v1/journeys/${journeyId}`;
const goal = "成年情侣晚间活动较晚，次日睡到中午，不安排早起";

function json(route: Route, value: object) {
  return route.fulfill({
    status: 200,
    contentType: "application/json",
    body: JSON.stringify(value),
  });
}

test("390x844 TEST_FIXTURE challenge submits the complete late-night rest request to AI DRAFT", async ({ page }) => {
  let suggestionCalls = 0;
  let providerCalls = 0;
  let submittedGoal = "";

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

  // Keep every API call local to this spec; unlisted routes cannot reach a live service.
  await page.route("**/api/v1/**", (route) => route.abort());
  await page.route("**/api/v1/agent/runtime-status", (route) => json(route, {
    runtime_identity: "HERMES_COMPAT_ENDPOINT",
    hermes_compat_configured: true,
    ai_state: "CONFIGURED_UNVERIFIED",
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
  await page.route(`${root}/trial-ai-discovery`, async (route) => {
    suggestionCalls += 1;
    expect(route.request().method()).toBe("POST");
    expect(route.request().url()).toContain("/trial-ai-discovery");
    const body = route.request().postDataJSON() as { goal?: unknown };
    submittedGoal = String(body.goal ?? "");
    await json(route, {
      status: "MODEL_TOOL_SUGGESTION",
      category: "park/garden",
      reason: "TEST_FIXTURE · 明天中午后再出发，留足休息时间。",
      model: "TEST_FIXTURE",
      evidence: "TEST_FIXTURE",
      provider_calls: 0,
      agent_run_created: false,
    });
  });
  await page.route(`${root}/bootstrap-city-search`, (route) => {
    providerCalls += 1;
    return route.abort();
  });
  await page.route(`${root}/bootstrap-discovery`, (route) => {
    providerCalls += 1;
    return route.abort();
  });

  await page.goto("/revolution");
  const prompt = page.getByLabel("写下你的想法");
  const askAi = page.getByTestId("rev-quick-consult-ai");
  await expect(prompt).toBeVisible();
  await expect(askAi).toBeEnabled();

  await page.getByTestId("rev-quick-ask-ai-shortcut").click();
  await expect(prompt).toBeFocused();
  await expect(prompt).toBeInViewport();
  expect(suggestionCalls).toBe(0);

  await prompt.fill(goal);
  await expect(prompt).toHaveValue(goal);
  await page.getByTestId("rev-mobile-tab-trips").click();
  await expect(page.getByTestId("rev-mobile-screen-trips")).toBeVisible();
  await page.getByTestId("rev-mobile-tab-explore").click();
  await expect(prompt).toHaveValue(goal);
  const screenshotPath = process.env.CITYNEXUS_SCREENSHOT_PATH?.trim();
  if (screenshotPath) {
    await prompt.scrollIntoViewIfNeeded();
    await page.screenshot({ path: screenshotPath, fullPage: false });
  }

  const suggestionResponse = page.waitForResponse((response) =>
    response.request().method() === "POST" && response.url().includes("/trial-ai-discovery"),
  );
  await askAi.click();
  await suggestionResponse;

  await expect(page.getByTestId("rev-quick-ai-response")).toBeVisible();
  await expect(page.getByTestId("rev-quick-ai-response")).toContainText("TEST_FIXTURE · 明天中午后再出发，留足休息时间。");
  expect(suggestionCalls).toBe(1);
  expect(submittedGoal).toBe(goal);
  expect(providerCalls).toBe(0);
});
