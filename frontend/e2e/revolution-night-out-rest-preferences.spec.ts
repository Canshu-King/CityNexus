import { expect, test, type Route } from "@playwright/test";

test.use({ viewport: { width: 390, height: 844 }, hasTouch: true, serviceWorkers: "block" });

const journeyId = "00000000-0000-4000-8000-000000000238";
const travelerId = "TEST_FIXTURE_TRAVELER_238";
const root = `**/api/v1/journeys/${journeyId}`;
const goal = "情侣凌晨03:00入睡，次日13:30醒；一人体力较低，午后按下雨场景规划两站。";
const restPreference = "时间窗：次日13:30起床，14:30后出发；上午不排活动，留足休息。";
const shortWalkPreference = "偏好：低体力同行，少走路，优先短路线。";
const rainConflictPreference = "只排已核实开放且可达的两站；未知标待核实。先核实午后雨情；若下雨，只排室内地点；冲突先问我改计划。";

function json(route: Route, value: object) {
  return route.fulfill({
    status: 200,
    contentType: "application/json",
    body: JSON.stringify(value),
  });
}

test("390x844 TEST_FIXTURE late-night couple can edit time, walking, and rain conflicts before submitting", async ({ page }) => {
  const configuredBaseURL = test.info().project.use.baseURL;
  if (typeof configuredBaseURL !== "string") throw new Error("mobile UI fixture baseURL is required");
  const localViteOrigin = new URL(configuredBaseURL).origin;
  let suggestionCalls = 0;
  let apiPostCalls = 0;
  let providerCalls = 0;
  let pocketGoWrites = 0;
  let blockedExternalRequests = 0;
  let submittedGoal = "";

  await page.addInitScript(({ id, travelerId }) => {
    window.sessionStorage.setItem("citynexus.traveler.bearer", "TEST_ONLY_SIGNED_FIXTURE_TOKEN");
    window.sessionStorage.setItem("citynexus.traveler.session-id", travelerId);
    window.localStorage.setItem("citynexus.locale", "zh-CN");
    window.localStorage.setItem("citynexus.revolution.firstlook.journey", JSON.stringify({
      id,
      cityCode: "CN-RV-TEST",
      cityName: "连城",
      status: "DRAFT",
      ownerTravelerId: travelerId,
    }));
  }, { id: journeyId, travelerId });

  page.on("request", (request) => {
    const url = new URL(request.url());
    if (request.method() === "POST" && url.pathname.startsWith("/api/v1/")) {
      apiPostCalls += 1;
      if (/pocket[-_]walk|\/go(?:\/|$)/i.test(url.pathname)) pocketGoWrites += 1;
    }
  });

  // Serve only from this isolated Vite origin; external network requests are always blocked.
  await page.route("**/*", (route) => {
    const url = new URL(route.request().url());
    if (url.origin === localViteOrigin) return route.continue();
    blockedExternalRequests += 1;
    return route.abort();
  });
  // Keep every API call local to this spec; unlisted routes cannot reach a live service.
  await page.route("**/api/v1/**", (route) => route.abort());
  await page.route("**/api/v1/agent/runtime-status", (route) => json(route, {
    runtime_identity: "HERMES_COMPAT_ENDPOINT",
    hermes_compat_configured: true,
    ai_state: "CONFIGURED_UNVERIFIED",
  }));
  await page.route(root, (route) => json(route, { id: journeyId, status: "DRAFT" }));
  await page.route(`${root}/planning-intent`, (route) => json(route, {
    journey_id: journeyId, intent: { goal: "" }, candidates: [],
    trip: { dates: ["2026-10-19", "2026-10-20"], party_size: 2, budget: {amount_minor: 50000, currency: "CNY"} },
  }));
  await page.route(`${root}/map-places`, (route) => json(route, {journey_id: journeyId, candidates: []}));
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
      reason: "TEST_FIXTURE · 天气、营业与可达性均待核实；不生成未核实两站。",
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
  expect(suggestionCalls).toBe(0);
  expect(apiPostCalls).toBe(0);
  expect(pocketGoWrites).toBe(0);

  await page.getByTestId("rev-quick-ask-ai-shortcut").click();
  await expect(prompt).toBeFocused();
  await expect(prompt).toBeInViewport();
  expect(suggestionCalls).toBe(0);
  expect(apiPostCalls).toBe(0);
  expect(pocketGoWrites).toBe(0);

  await prompt.fill(goal);
  await expect(prompt).toHaveValue(goal);
  const restPreferenceButton = page.getByTestId("rev-quick-ai-rest-preference");
  await expect(restPreferenceButton).toBeVisible();
  await expect(restPreferenceButton).toBeInViewport();
  await expect(restPreferenceButton).toHaveAttribute("aria-pressed", "false");
  await restPreferenceButton.tap();
  await expect(restPreferenceButton).toHaveAttribute("aria-pressed", "true");
  await expect(prompt).toHaveValue(`${goal}\n${restPreference}`);
  expect(suggestionCalls).toBe(0);
  expect(apiPostCalls).toBe(0);
  expect(pocketGoWrites).toBe(0);

  await restPreferenceButton.tap();
  await expect(restPreferenceButton).toHaveAttribute("aria-pressed", "false");
  await expect(prompt).toHaveValue(goal);
  expect(suggestionCalls).toBe(0);
  expect(apiPostCalls).toBe(0);

  await restPreferenceButton.tap();
  await expect(prompt).toHaveValue(`${goal}\n${restPreference}`);
  expect(suggestionCalls).toBe(0);
  expect(apiPostCalls).toBe(0);

  const shortWalkPreferenceButton = page.getByTestId("rev-quick-ai-short-walk-preference");
  await shortWalkPreferenceButton.scrollIntoViewIfNeeded();
  await expect(shortWalkPreferenceButton).toBeVisible();
  await expect(shortWalkPreferenceButton).toBeInViewport();
  await expect(shortWalkPreferenceButton).toHaveAttribute("aria-pressed", "false");
  await shortWalkPreferenceButton.tap();
  await expect(shortWalkPreferenceButton).toHaveAttribute("aria-pressed", "true");
  await expect(prompt).toHaveValue(`${goal}\n${restPreference}\n${shortWalkPreference}`);
  await expect(prompt).toHaveAttribute("rows", "8");
  expect(suggestionCalls).toBe(0);
  expect(apiPostCalls).toBe(0);

  await shortWalkPreferenceButton.tap();
  await expect(shortWalkPreferenceButton).toHaveAttribute("aria-pressed", "false");
  await expect(prompt).toHaveValue(`${goal}\n${restPreference}`);
  expect(suggestionCalls).toBe(0);
  expect(apiPostCalls).toBe(0);

  await shortWalkPreferenceButton.tap();
  await expect(prompt).toHaveValue(`${goal}\n${restPreference}\n${shortWalkPreference}`);
  expect(suggestionCalls).toBe(0);
  expect(apiPostCalls).toBe(0);
  expect(pocketGoWrites).toBe(0);

  const rainConflictPreferenceButton = page.getByTestId("rev-quick-ai-rain-conflict-preference");
  await rainConflictPreferenceButton.scrollIntoViewIfNeeded();
  await expect(rainConflictPreferenceButton).toBeVisible();
  await expect(rainConflictPreferenceButton).toBeInViewport();
  await expect(rainConflictPreferenceButton).toHaveAttribute("aria-pressed", "false");
  await rainConflictPreferenceButton.tap();
  await expect(rainConflictPreferenceButton).toHaveAttribute("aria-pressed", "true");
  const fullGoal = `${goal}\n${restPreference}\n${shortWalkPreference}\n${rainConflictPreference}`;
  await expect(prompt).toHaveValue(fullGoal);
  await expect(prompt).toHaveAttribute("rows", "12");
  const promptIsFullyVisible = await prompt.evaluate((element) => element.scrollHeight <= element.clientHeight + 1);
  expect(promptIsFullyVisible).toBe(true);
  expect(suggestionCalls).toBe(0);
  expect(apiPostCalls).toBe(0);
  expect(pocketGoWrites).toBe(0);

  await rainConflictPreferenceButton.tap();
  await expect(rainConflictPreferenceButton).toHaveAttribute("aria-pressed", "false");
  await expect(prompt).toHaveValue(`${goal}\n${restPreference}\n${shortWalkPreference}`);
  expect(suggestionCalls).toBe(0);
  expect(apiPostCalls).toBe(0);
  expect(pocketGoWrites).toBe(0);

  await rainConflictPreferenceButton.tap();
  await expect(prompt).toHaveValue(fullGoal);
  expect(suggestionCalls).toBe(0);
  expect(apiPostCalls).toBe(0);
  expect(pocketGoWrites).toBe(0);

  await page.getByTestId("rev-mobile-tab-trips").click();
  await expect(page.getByTestId("rev-mobile-screen-trips")).toBeVisible();
  await page.getByTestId("rev-mobile-tab-explore").click();
  await expect(prompt).toHaveValue(fullGoal);
  expect(suggestionCalls).toBe(0);
  expect(apiPostCalls).toBe(0);
  expect(pocketGoWrites).toBe(0);
  const screenshotPath = process.env.CITYNEXUS_SCREENSHOT_PATH?.trim();
  if (screenshotPath) {
    await prompt.scrollIntoViewIfNeeded();
    await page.screenshot({ path: screenshotPath, fullPage: false });
  }

  await askAi.click();
  const taskDialog = page.getByRole("region", {name: "Agent 命令台"});
  await expect(taskDialog.getByRole("textbox")).toHaveValue(fullGoal);
  await expect(taskDialog.getByRole("button", {name: "开始研究", exact: true})).toBeDisabled();
  expect(suggestionCalls).toBe(0);
  expect(apiPostCalls).toBe(0);
  expect(submittedGoal).toBe("");
  expect(providerCalls).toBe(0);
  expect(pocketGoWrites).toBe(0);
  expect(blockedExternalRequests).toBe(0);
});
