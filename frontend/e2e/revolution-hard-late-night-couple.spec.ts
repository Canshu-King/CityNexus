import { expect, test, type Route } from "@playwright/test";

test.use({ viewport: { width: 390, height: 844 }, hasTouch: true, serviceWorkers: "block" });

const journeyId = "00000000-0000-4000-8000-000000000240";
const root = `**/api/v1/journeys/${journeyId}`;
const goal = "我们是情侣，今晚逛夜市到凌晨03:00才休息。明天请让我们睡到12:30以后，14:00再出发；一人想去热闹夜市，另一人想去安静绿地，尽量少走路。";

function json(route: Route, value: object) {
  return route.fulfill({
    status: 200,
    contentType: "application/json",
    body: JSON.stringify(value),
  });
}

test("late-night couple preferences survive tab return and submit only on explicit ask", async ({ page }) => {
  let suggestionCalls = 0;
  let apiPostCalls = 0;
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

  page.on("request", (request) => {
    const url = new URL(request.url());
    if (request.method() === "POST" && url.pathname.startsWith("/api/v1/")) apiPostCalls += 1;
  });

  // The API fallback aborts any request without a local fixture handler.
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
  await page.route(`${root}/trial-ai-discovery`, async (route) => {
    suggestionCalls += 1;
    expect(route.request().method()).toBe("POST");
    const body = route.request().postDataJSON() as { goal?: unknown };
    submittedGoal = String(body.goal ?? "");
    await json(route, {
      status: "MODEL_TOOL_SUGGESTION",
      category: "park/garden",
      reason: "TEST_FIXTURE · 兼顾安静绿地、少步行和较晚出发。",
      model: "TEST_FIXTURE",
      evidence: "TEST_FIXTURE",
      provider_calls: 0,
      agent_run_created: false,
    });
  });

  await page.goto("/revolution");
  const prompt = page.getByLabel("写下你的想法");
  const shortcut = page.getByTestId("rev-quick-ask-ai-shortcut");
  const askAi = page.getByTestId("rev-quick-consult-ai");
  await expect(prompt).toBeVisible();
  await expect(askAi).toBeEnabled();

  await shortcut.click();
  await expect(prompt).toBeFocused();
  await expect(prompt).toBeInViewport();
  expect(suggestionCalls).toBe(0);
  expect(apiPostCalls).toBe(0);

  await prompt.fill(goal);
  await expect(prompt).toHaveValue(goal);
  await page.getByTestId("rev-mobile-tab-trips").click();
  await expect(page.getByTestId("rev-mobile-screen-trips")).toBeVisible();
  await page.getByTestId("rev-mobile-tab-explore").click();
  await expect(prompt).toHaveValue(goal);
  expect(suggestionCalls).toBe(0);
  expect(apiPostCalls).toBe(0);

  await shortcut.click();
  await expect(prompt).toBeFocused();
  await expect(prompt).toBeInViewport();
  expect(suggestionCalls).toBe(0);
  expect(apiPostCalls).toBe(0);

  const suggestionResponse = page.waitForResponse((response) =>
    response.request().method() === "POST" && response.url().includes("/trial-ai-discovery"),
  );
  await askAi.click();
  await suggestionResponse;

  await expect(page.getByTestId("rev-quick-ai-response")).toBeVisible();
  expect(suggestionCalls).toBe(1);
  expect(apiPostCalls).toBe(1);
  expect(submittedGoal).toBe(goal);
  expect(submittedGoal).toContain("凌晨03:00才休息");
  expect(submittedGoal).toContain("睡到12:30以后");
  expect(submittedGoal).toContain("14:00再出发");
  expect(submittedGoal).toContain("一人想去热闹夜市");
  expect(submittedGoal).toContain("另一人想去安静绿地");
  expect(submittedGoal).toContain("尽量少走路");
});
