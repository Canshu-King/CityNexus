import { expect, test, type Page, type Route } from "@playwright/test";

test.use({
  viewport: { width: 390, height: 844 },
  hasTouch: true,
  storageState: { cookies: [], origins: [] },
});

const journeyId = "00000000-0000-4000-8000-000000000223";
const fixtureTravelerId = "00000000-0000-4000-8000-000000000224";
const prefix = `**/api/v1/journeys/${journeyId}`;
const fixtureBearer = "TEST_ONLY_SIGNED_FIXTURE_TOKEN";

async function fulfill(route: Route, value: unknown) {
  await route.fulfill({
    status: 200,
    contentType: "application/json",
    body: JSON.stringify(value),
  });
}

async function signedActiveJourney(
  page: Page,
  runtime: { aiState: string; compatConfigured: boolean } = { aiState: "DISABLED_BY_OPS", compatConfigured: false },
) {
  await page.addInitScript(({ id, travelerId }) => {
    window.sessionStorage.setItem("citynexus.traveler.bearer", "TEST_ONLY_SIGNED_FIXTURE_TOKEN");
    window.sessionStorage.setItem("citynexus.traveler.session-id", travelerId);
    window.localStorage.setItem("citynexus.locale", "zh-CN");
    window.localStorage.setItem("citynexus.revolution.firstlook.journey", JSON.stringify({
      id,
      cityCode: "CN-RV-TEST",
      cityName: "连城",
      status: "ACTIVE",
      ownerTravelerId: travelerId,
    }));
  }, { id: journeyId, travelerId: fixtureTravelerId });

  await page.route("**/api/v1/agent/runtime-status", (route) => fulfill(route, {
    runtime_identity: runtime.compatConfigured ? "HERMES_COMPAT_ENDPOINT" : "NOT_CONFIGURED",
    hermes_compat_configured: runtime.compatConfigured,
    ai_state: runtime.aiState,
    fixture_mode: "TEST_FIXTURE",
  }));
  await page.route(`${prefix}/operator`, (route) => fulfill(route, {
    journey_id: journeyId,
    state: "OFF",
    headline: "No standing operator",
    enabled: false,
    standing_mission_id: null,
    autonomy: "PLAN_ONLY",
    incident: null,
    decision: null,
    approval: null,
    brain: {
      state: "CONFIGURED_UNKNOWN",
      headline: "No standing run",
      configured_runtimes: [],
      preferred_runtime: null,
      last_failure_reason: null,
      recovery_resume: { pending: false, safe_to_resume: false },
    },
    collective: {
      state: "SINGLE_TRAVELLER", mission_id: null, required_count: 1,
      response_count: 0, viewer_has_responded: false, members: [], options: [],
    },
    discovery: {
      state: "IDLE", attempt_count: 0, max_attempts: 1,
      raw_candidate_count: 0, materialized_place_count: 0,
    },
    timeline: [],
    operator: { watching: false, will_continue_after_approval: false },
  }));

  // Read-only boot fixtures keep unrelated trip panels offline and deterministic.
  await page.route(`${prefix}/experience`, (route) => fulfill(route, {
    active_plan: { id: "TEST_FIXTURE_PLAN", status: "ACTIVE", activities: [], legs: [], disruptions: [] },
    recovery: null,
    experience_flags: { needs_review: false, recovery_required: false, staleness: false },
  }));
  await page.route(`${prefix}/twin`, (route) => fulfill(route, { id: "TEST_FIXTURE_TWIN", context: {} }));
  await page.route(`${prefix}/plans`, (route) => fulfill(route, []));
  await page.route(`${prefix}/replans`, (route) => fulfill(route, []));
  await page.route(`${prefix}/guardian/pulse/latest`, (route) => fulfill(route, { pulse: null }));
  await page.route(`${prefix}/launch-setup`, (route) => fulfill(route, {}));
  await page.route(`${prefix}/guardian/autopilot/status`, (route) => fulfill(route, {
    enrollment: { enabled: false },
    watch: null,
    readiness: null,
  }));
  await page.route(`${prefix}/bootstrap-discovery/readiness`, (route) => fulfill(route, {
    journey_id: journeyId,
    provider: "overpass",
    provider_name: "TEST_FIXTURE provider",
    expected_recipient: "TEST_FIXTURE",
    status: "BLOCKED",
    reason_code: "PROVIDER_DISABLED",
    provider_grade: "TEST_PROVIDER",
    capability_state: "LIVE_BLOCKED",
    external_request_allowed: false,
    test_only: true,
  }));
  await page.route(`${prefix}/bootstrap-shortlist`, (route) => fulfill(route, {
    journey_id: journeyId,
    limit: 3,
    items: [],
    resume: null,
    pocket_walk: null,
  }));
  await page.route(`${prefix}/agent/hermes/latest-run`, (route) => fulfill(route, {
    journey_id: journeyId,
    run: null,
  }));
}

test("TEST_FIXTURE latest read restores saved mobile compatibility tool steps after reload", async ({ page }) => {
  await signedActiveJourney(page);

  let latestReads = 0;
  let serverHasSavedRun = false;
  let providerOrAiPosts = 0;
  page.on("request", (request) => {
    if (request.method() === "POST" && /agent\/mobile-compat-runs|trial-ai-discovery|copilot\/messages|bootstrap-city-search|bootstrap-discovery/.test(request.url())) {
      providerOrAiPosts += 1;
    }
  });

  const savedRun = {
    request_id: "TEST_FIXTURE_REQUEST_1",
    run_id: "TEST_FIXTURE_RUN_1",
    mission_id: "TEST_FIXTURE_MISSION_1",
    runtime_identity: "HERMES_COMPAT_ENDPOINT",
    provider_key: "TEST_FIXTURE",
    status: "PARTIAL",
    tool_call_recorded: true,
    verification: "WB2API_TOOL_CALL_RECORDED",
    tool_steps: [
      {
        sequence_no: 1,
        tool_name: "inspect_journey",
        status: "COMPLETED",
        created_at: "2026-10-17T00:00:01Z",
        completed_at: "2026-10-17T00:00:02Z",
      },
      {
        sequence_no: 2,
        tool_name: "inspect_twin",
        status: "FAILED",
        created_at: "2026-10-17T00:00:03Z",
        completed_at: "2026-10-17T00:00:04Z",
      },
    ],
    created_at: "2026-10-17T00:00:00Z",
    started_at: "2026-10-17T00:00:01Z",
    completed_at: "2026-10-17T00:00:04Z",
  };

  await page.route(`${prefix}/agent/mobile-compat-runs/latest`, async (route) => {
    expect(route.request().method()).toBe("GET");
    expect(route.request().headers()["authorization"]).toBe(`Bearer ${fixtureBearer}`);
    latestReads += 1;
    await fulfill(route, {
      runtime_identity: "TEST_FIXTURE",
      configured: false,
      run: serverHasSavedRun ? savedRun : null,
      fixture_mode: "TEST_FIXTURE",
    });
  });

  const waitForLatestResponse = () => page.waitForResponse((response) =>
    response.request().method() === "GET" && response.url().includes("/agent/mobile-compat-runs/latest"),
  );
  await page.goto("/revolution");
  await expect(page.getByTestId("rev-mobile-tab-explore")).toHaveAttribute("aria-current", "page");
  expect(latestReads).toBe(0);

  const firstTripsRead = waitForLatestResponse();
  await page.getByTestId("rev-mobile-tab-trips").click();
  await firstTripsRead;
  expect(latestReads).toBeGreaterThan(0);
  const emptyActivity = page.getByTestId("rev-mobile-compat-agent");
  await expect(emptyActivity).toBeVisible();
  await expect(emptyActivity.getByRole("status").first()).toHaveText("AI 暂未开启");
  await expect(emptyActivity.getByTestId("rev-mobile-compat-agent-empty")).toHaveText("暂无助手运行记录。");
  await expect(emptyActivity.getByTestId("rev-mobile-compat-agent-start")).toHaveCount(0);

  const readsAfterFirstTrips = latestReads;
  await page.getByTestId("rev-mobile-tab-explore").click();
  await expect(page.getByTestId("rev-mobile-tab-explore")).toHaveAttribute("aria-current", "page");
  expect(latestReads).toBe(readsAfterFirstTrips);

  serverHasSavedRun = true;
  const returningTripsRead = waitForLatestResponse();
  await page.getByTestId("rev-mobile-tab-trips").click();
  await returningTripsRead;
  const returningActivity = page.getByTestId("rev-mobile-compat-agent");
  await expect(returningActivity).toBeVisible();

  const readsBeforeRefresh = latestReads;
  await page.getByTestId("rev-mobile-tab-explore").click();
  await page.reload();
  await expect(page.getByTestId("rev-mobile-tab-explore")).toHaveAttribute("aria-current", "page");
  expect(latestReads).toBe(readsBeforeRefresh);

  const restoredTripsRead = waitForLatestResponse();
  await page.getByTestId("rev-mobile-tab-trips").click();
  await restoredTripsRead;

  const activity = page.getByTestId("rev-mobile-compat-agent");
  await expect(activity).toBeVisible();
  await expect(activity.getByRole("status")).toHaveText("行程检查未完成");
  expect(latestReads).toBeGreaterThan(readsBeforeRefresh);
  await activity.getByRole("button", { name: /查看工作记录/ }).click();

  const events = activity.getByTestId("rev-mobile-compat-agent-events");
  await expect(events.locator("li")).toHaveCount(2);
  await expect(events.locator("li").nth(0).locator("svg.lucide-circle-check")).toHaveCount(1);
  await expect(events.locator("li").nth(1).locator("svg.lucide-circle-alert")).toHaveCount(1);
  await expect(events).toContainText("检查当前行程");
  await expect(events).toContainText("核对行程状态");
  await expect(events).not.toContainText("inspect_journey");
  await expect(events).not.toContainText("inspect_twin");
  await expect(events).not.toContainText("list_replans");
  expect(providerOrAiPosts).toBe(0);
});

test("TEST_FIXTURE configured endpoint with no run shows idle state without sending a request", async ({ page }) => {
  await signedActiveJourney(page, { aiState: "CONFIGURED_UNVERIFIED", compatConfigured: true });
  await page.route(`${prefix}/agent/mobile-compat-runs/latest`, async (route) => {
    expect(route.request().method()).toBe("GET");
    expect(route.request().headers()["authorization"]).toBe(`Bearer ${fixtureBearer}`);
    await fulfill(route, { runtime_identity: "TEST_FIXTURE", configured: true, run: null, fixture_mode: "TEST_FIXTURE" });
  });
  let providerOrAiPosts = 0;
  page.on("request", (request) => {
    if (request.method() === "POST" && /agent\/mobile-compat-runs|trial-ai-discovery|copilot\/messages/.test(request.url())) {
      providerOrAiPosts += 1;
    }
  });

  await page.goto("/revolution");
  const latestRead = page.waitForResponse((response) =>
    response.request().method() === "GET" && response.url().includes("/agent/mobile-compat-runs/latest"),
  );
  await page.getByTestId("rev-mobile-tab-trips").click();
  await latestRead;
  const activity = page.getByTestId("rev-mobile-compat-agent");
  await expect(activity.getByRole("status").first()).toHaveText("AI 当前没有执行中的任务");
  await expect(activity.getByTestId("rev-mobile-compat-agent-start")).toBeVisible();
  expect(providerOrAiPosts).toBe(0);
});
