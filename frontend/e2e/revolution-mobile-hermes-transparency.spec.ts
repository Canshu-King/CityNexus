import { expect, test, type Page, type Route } from "@playwright/test";

test.use({
  viewport: { width: 390, height: 844 },
  hasTouch: true,
  serviceWorkers: "block",
  storageState: { cookies: [], origins: [] },
});

const journeyId = "00000000-0000-4000-8000-000000000224";
const journeyRoot = `**/api/v1/journeys/${journeyId}`;

type FixtureEvent = {
  event_type: string;
  run_id: string;
  event_id: string;
  sequence: number;
  tool_name: string | null;
  friendly_label: string;
  status: string;
  timestamp: string;
  source: "HERMES_NATIVE";
  duration_ms?: number;
  result_summary?: Record<string, unknown> | string | null;
  approval_id?: string;
  approval_status?: string;
};

type RunFixture = {
  runId: string;
  status: "running" | "completed" | "failed";
  timelineEvents: FixtureEvent[];
  initialEvents?: FixtureEvent[];
  reasoningSummary?: string;
  operatorApproval?: boolean;
};

function fixtureEvent(
  runId: string,
  eventType: string,
  sequence: number,
  timestamp: string,
  options: Partial<FixtureEvent> = {},
): FixtureEvent {
  return {
    event_type: eventType,
    run_id: runId,
    event_id: `TEST_FIXTURE-${runId}-${sequence}`,
    sequence,
    tool_name: null,
    friendly_label: "TEST_FIXTURE",
    status: "completed",
    timestamp,
    source: "HERMES_NATIVE",
    ...options,
  };
}

async function json(route: Route, value: unknown) {
  await route.fulfill({
    status: 200,
    contentType: "application/json",
    body: JSON.stringify(value),
  });
}

function operatorFixture(withApproval: boolean) {
  const approvalId = "TEST_FIXTURE-approval-24";
  return {
    journey_id: journeyId,
    state: withApproval ? "WAITING_FOR_APPROVAL" : "WATCHING",
    headline: "TEST_FIXTURE operator projection",
    enabled: true,
    standing_mission_id: null,
    autonomy: null,
    incident: null,
    decision: withApproval
      ? { proposal_id: "TEST_FIXTURE-proposal", status: "PENDING", summary: "TEST_FIXTURE approval entry" }
      : null,
    approval: withApproval
      ? {
        required: true,
        approval_id: approvalId,
        status: "PENDING",
        action_label: "TEST_FIXTURE approval action",
        pending_action_id: "TEST_FIXTURE-action",
      }
      : null,
    brain: {
      state: "READY",
      headline: "TEST_FIXTURE",
      configured_runtimes: [],
      preferred_runtime: null,
      last_failure_reason: null,
      recovery_resume: { pending: false, safe_to_resume: false },
    },
    collective: {
      state: "SINGLE_TRAVELLER",
      mission_id: null,
      required_count: 1,
      response_count: 0,
      viewer_has_responded: false,
      members: [],
      options: [],
    },
    discovery: {
      state: "IDLE",
      attempt_count: 0,
      max_attempts: 0,
      raw_candidate_count: 0,
      materialized_place_count: 0,
    },
    operations: withApproval
      ? {
        plan_id: "TEST_FIXTURE-operations",
        status: "WAITING_FOR_APPROVAL",
        planned_action_count: 1,
        completed_action_count: 0,
        approval_id: approvalId,
        provider_label: "TEST_FIXTURE",
        actions: [],
      }
      : null,
    timeline: [],
    operator: { watching: true, will_continue_after_approval: false },
  };
}

async function installRunFixture(page: Page, fixture: RunFixture) {
  const { runId, status, timelineEvents, initialEvents = [] } = fixture;
  const run = {
    run_id: runId,
    status,
    runtime_identity: "HERMES_NATIVE_MCP",
    provider_key: "TEST_FIXTURE_ISSUE24",
    mission_id: "TEST_FIXTURE-only",
    reasoning_summary: fixture.reasoningSummary ?? "TEST_FIXTURE_REASONING_CANARY_DO_NOT_RENDER",
    events_url: `/api/v1/journeys/${journeyId}/agent/hermes/runs/${runId}/events`,
    timeline_url: `/api/v1/journeys/${journeyId}/agent/hermes/runs/${runId}/timeline`,
    initial_events: initialEvents,
  };
  const allEvents = [...timelineEvents, ...initialEvents];
  const sseBody = allEvents.map((event) =>
    `event: ${event.event_type}\r\ndata: ${JSON.stringify(event)}\r\n\r\n`,
  ).join("");
  const signedReads = { latestRun: 0, timeline: 0, events: 0 };

  await page.addInitScript((id) => {
    window.sessionStorage.setItem("citynexus.traveler.bearer", "TEST_FIXTURE_MEMBER_24");
    window.sessionStorage.setItem("citynexus.traveler.session-id", "TEST_FIXTURE_TRAVELER_24");
    window.localStorage.setItem("citynexus.locale", "zh-CN");
    window.localStorage.setItem("citynexus.revolution.firstlook.journey", JSON.stringify({
      id,
      cityCode: "CN-RV-HERMES-TEST-FIXTURE",
      cityName: "测试地区",
      status: "ACTIVE",
      ownerTravelerId: "TEST_FIXTURE_TRAVELER_24",
    }));
  }, journeyId);

  // The catch-all aborts all unlisted API requests; every response below is a TEST_FIXTURE.
  await page.route("**/api/v1/**", (route) => route.abort());
  await page.route("**/api/v1/agent/runtime-status", (route) => json(route, {
    runtime_identity: "TEST_FIXTURE",
    hermes_native_gateway: { configured: true, reachable: true, ready: true, runs: true, events: true },
    hermes_compat_configured: false,
    ai_state: "DISABLED",
  }));
  await page.route(`${journeyRoot}/agent/hermes/latest-run`, async (route) => {
    expect(route.request().method()).toBe("GET");
    expect(route.request().headers().authorization).toBe("Bearer TEST_FIXTURE_MEMBER_24");
    signedReads.latestRun += 1;
    await json(route, { journey_id: journeyId, run });
  });
  await page.route(`${journeyRoot}/agent/hermes/runs/${runId}/timeline`, async (route) => {
    expect(route.request().method()).toBe("GET");
    expect(route.request().headers().authorization).toBe("Bearer TEST_FIXTURE_MEMBER_24");
    signedReads.timeline += 1;
    await json(route, {
      run_id: runId,
      journey_id: journeyId,
      runtime_identity: "HERMES_NATIVE_MCP",
      events: timelineEvents,
      observability: {
        run_id: runId,
        runtime_identity: "HERMES_NATIVE_MCP",
        current_mission: "TEST_FIXTURE-only",
        tool_count: timelineEvents.filter((event) => event.event_type.startsWith("tool.")).length,
        current_tool: null,
        completion_status: status,
        gateway_decision: null,
        guardian_decision: null,
        total_duration_ms: 0,
      },
    });
  });
  await page.route(`${journeyRoot}/agent/hermes/runs/${runId}/events`, async (route) => {
    expect(route.request().method()).toBe("GET");
    expect(route.request().headers().authorization).toBe("Bearer TEST_FIXTURE_MEMBER_24");
    signedReads.events += 1;
    await route.fulfill({ status: 200, contentType: "text/event-stream", body: sseBody });
  });
  await page.route(`${journeyRoot}/operator`, (route) => json(route, operatorFixture(Boolean(fixture.operatorApproval))));
  return signedReads;
}

async function openRunTrace(page: Page) {
  await page.goto("/revolution");
  await page.getByTestId("rev-mobile-tab-trips").click();
  if (await page.getByTestId("rev-mission-layer-agent").isVisible()) await page.getByTestId("rev-mission-layer-agent").click();
  const hermes = page.getByTestId("rev-mobile-hermes");
  const run = hermes.getByTestId("rev-mobile-hermes-run");
  await expect(run).toBeVisible();
  await hermes.getByRole("button", { name: "查看工作过程" }).click();
  const sheet = hermes.getByTestId("rev-mobile-hermes-sheet");
  await expect(sheet).toBeVisible();
  await expect(sheet).toContainText("测试数据");
  return { hermes, run, sheet };
}

test("TEST_FIXTURE running trace shows server state, timestamp, and tool identity without reasoning summary", async ({ page }) => {
  const runId = "TEST_FIXTURE-running-24";
  const signedReads = await installRunFixture(page, {
    runId,
    status: "running",
    timelineEvents: [
      fixtureEvent(runId, "run.started", 1, "2026-10-17T09:10:00+08:00", { status: "running" }),
      fixtureEvent(runId, "tool.started", 2, "2026-10-17T09:10:04+08:00", {
        event_id: "TEST_FIXTURE-tool-search-city-services",
        tool_name: "search_city_services",
        status: "started",
      }),
    ],
  });

  const { run, sheet } = await openRunTrace(page);
  await expect(run).toContainText(/正在运行|运行中/);
  await expect(sheet).toContainText("Hermes 已开始处理");
  await expect(sheet).toContainText("正在搜索地点与服务");
  await expect(sheet.getByText("search_city_services", { exact: true })).toBeVisible();
  const startedAt = sheet.locator('time[datetime="2026-10-17T09:10:00+08:00"]');
  await expect(startedAt).toBeVisible();
  await expect(startedAt).toHaveText(/\d{1,2}.*\d{1,2}.*\d{2}:\d{2}:\d{2}/);
  await expect(page.getByText("TEST_FIXTURE_REASONING_CANARY_DO_NOT_RENDER", { exact: true })).toHaveCount(0);
  await expect.poll(() => signedReads.latestRun).toBeGreaterThan(0);
  await expect.poll(() => signedReads.timeline).toBeGreaterThan(0);
  await expect.poll(() => signedReads.events).toBeGreaterThan(0);
});

test("TEST_FIXTURE DRAFT activity entry only reads signed plans without starting a run or provider lookup", async ({ page }, testInfo) => {
  let nativeRunReads = 0;
  const apiRequests: string[] = [];
  const startupReads = { runtime: 0, readiness: 0, shortlist: 0, citySearch: 0 };
  await page.addInitScript((id) => {
    window.sessionStorage.setItem("citynexus.traveler.bearer", "TEST_FIXTURE_MEMBER_24");
    window.sessionStorage.setItem("citynexus.traveler.session-id", "TEST_FIXTURE_TRAVELER_24");
    window.localStorage.setItem("citynexus.locale", "zh-CN");
    window.localStorage.setItem("citynexus.revolution.firstlook.journey", JSON.stringify({
      id, cityCode: "CN-RV-DRAFT-TEST-FIXTURE", cityName: "测试地区", status: "DRAFT",
      ownerTravelerId: "TEST_FIXTURE_TRAVELER_24",
    }));
  }, journeyId);
  await page.route("**/api/v1/**", (route) => route.abort());
  await page.route(journeyRoot, async (route) => {
    expect(route.request().headers().authorization).toBe("Bearer TEST_FIXTURE_MEMBER_24");
    await json(route, { id: journeyId, status: "DRAFT", timezone: "Asia/Shanghai" });
  });
  await page.route(`${journeyRoot}/plans`, async (route) => {
    expect(route.request().headers().authorization).toBe("Bearer TEST_FIXTURE_MEMBER_24");
    await json(route, []);
  });
  await page.route("**/api/v1/agent/runtime-status", async (route) => {
    startupReads.runtime += 1;
    await json(route, {
      runtime_identity: "TEST_FIXTURE", hermes_native_gateway: { configured: true },
      hermes_compat_configured: false, ai_state: "DISABLED",
    });
  });
  await page.route(`${journeyRoot}/bootstrap-discovery/readiness`, async (route) => {
    startupReads.readiness += 1;
    await json(route, {
      status: "READY", reason_code: "READY", provider: "overpass", provider_grade: "TEST_PROVIDER",
    });
  });
  await page.route(`${journeyRoot}/bootstrap-shortlist`, async (route) => {
    startupReads.shortlist += 1;
    await json(route, {
      journey_id: journeyId, limit: 3, items: [], resume: null, pocket_walk: null,
    });
  });
  let releaseCityLookup: () => void = () => {};
  const cityLookupResponse = new Promise<void>((resolve) => {
    releaseCityLookup = resolve;
  });
  await page.route(`${journeyRoot}/bootstrap-city-search`, async (route) => {
    startupReads.citySearch += 1;
    await cityLookupResponse;
    await json(route, {
      journey_id: journeyId, status: "CITY_NO_RESULTS", query: "测试地区",
      provider_provenance: "TEST_PROVIDER", provider_attempts: [], results: [],
    });
  });
  page.on("request", (request) => {
    const requestUrl = new URL(request.url());
    if (requestUrl.pathname.startsWith("/api/v1/")) {
      apiRequests.push(`${request.method()} ${requestUrl.pathname}`);
    }
    if (requestUrl.pathname.includes("/agent/hermes/latest-run") || requestUrl.pathname.includes("/agent/hermes/runs/")) {
      nativeRunReads += 1;
    }
  });

  await page.goto("/revolution");
  await expect(page.getByTestId("rev-mobile-screen-explore")).toBeVisible();
  await page.getByTestId("rev-quick-area-secondary").locator("summary").first().click();
  const activityEntry = page.getByTestId("rev-mission-layer-agent");
  await expect(activityEntry).toContainText("对话");
  await expect(page.getByTestId("revolution-agent-runtime")).toContainText("AI 暂未开启");
  await expect.poll(() => startupReads.runtime).toBeGreaterThan(0);
  await expect.poll(() => startupReads.readiness).toBeGreaterThan(0);
  await expect.poll(() => startupReads.shortlist).toBeGreaterThan(0);

  await page.getByLabel("城市或地区").fill("测试地区");
  const cityLookup = page.getByTestId("rev-quick-find-city");
  await cityLookup.click();
  await expect(cityLookup).toBeDisabled();
  await expect(cityLookup).toHaveText("查询中…");
  await expect(page.locator("#rev-quick-ai-prompt")).toHaveCount(0);
  await expect.poll(() => startupReads.citySearch).toBe(1);
  releaseCityLookup();
  await expect(cityLookup).toBeEnabled();

  const apiRequestsBeforeClick = apiRequests.length;
  await activityEntry.click();
  await expect(page.getByTestId("rev-mission-cockpit")).toBeVisible();
  if (await page.getByTestId("rev-mission-layer-agent").isVisible()) await page.getByTestId("rev-mission-layer-agent").click();
  else await expect(page.locator(".cn-mission-agent-disclosure")).toBeVisible();
  await expect(page.getByRole("region", {name: "Agent 命令台"})).toBeVisible();
  await expect(page.locator("dialog[open]")).toHaveCount(0);
  expect(apiRequests.slice(apiRequestsBeforeClick).every((request) => request.startsWith("GET "))).toBe(true);
  expect(nativeRunReads).toBe(0);
  await page.screenshot({
    path: testInfo.outputPath("issue24-draft-agent-activity-entry-390x844.png"),
    fullPage: false,
    animations: "disabled",
  });
});

test("TEST_FIXTURE pending approval opens the existing Journey authorization area", async ({ page }) => {
  const runId = "TEST_FIXTURE-approval-24";
  const approval = fixtureEvent(runId, "approval.required", 3, "2026-10-17T09:11:00+08:00", {
    status: "approval_required",
    approval_id: "TEST_FIXTURE-approval-24",
    approval_status: "PENDING",
  });
  await installRunFixture(page, {
    runId,
    status: "running",
    operatorApproval: true,
    timelineEvents: [
      fixtureEvent(runId, "run.started", 1, "2026-10-17T09:10:00+08:00", { status: "running" }),
      fixtureEvent(runId, "tool.started", 2, "2026-10-17T09:10:04+08:00", {
        event_id: "TEST_FIXTURE-tool-approval",
        tool_name: "request_replan",
        status: "started",
      }),
    ],
    initialEvents: [approval],
  });

  const { sheet } = await openRunTrace(page);
  await expect(sheet).toContainText("等待你确认");
  await expect(sheet).toContainText("有操作待确认。");
  const authorizationLink = sheet.getByRole("link", { name: "前往行程操作与授权审核 →" });
  await expect(authorizationLink).toHaveAttribute("href", "#journey-operator-operations");
  await expect(page.getByTestId("journey-operator-operations")).toBeAttached();
  await expect(page.getByTestId("journey-operator-approval")).toBeAttached();
  await authorizationLink.click();
  await expect(page).toHaveURL(/#journey-operator-operations$/);
});

test("TEST_FIXTURE completed trace retains the start and end events", async ({ page }) => {
  const runId = "TEST_FIXTURE-completed-24";
  await installRunFixture(page, {
    runId,
    status: "completed",
    timelineEvents: [
      fixtureEvent(runId, "run.started", 1, "2026-10-17T09:10:00+08:00", { status: "running" }),
      fixtureEvent(runId, "tool.started", 2, "2026-10-17T09:10:04+08:00", {
        event_id: "TEST_FIXTURE-tool-inspect-start",
        tool_name: "inspect_journey",
        status: "started",
      }),
      fixtureEvent(runId, "tool.completed", 3, "2026-10-17T09:10:06+08:00", {
        event_id: "TEST_FIXTURE-tool-inspect-end",
        tool_name: "inspect_journey",
        status: "completed",
        duration_ms: 1800,
      }),
      fixtureEvent(runId, "run.completed", 4, "2026-10-17T09:10:07+08:00", { status: "completed" }),
    ],
  });

  const { run, sheet } = await openRunTrace(page);
  await expect(run).toContainText("已完成");
  await expect(sheet).toContainText("Hermes 已开始处理");
  await expect(sheet).toContainText("Hermes 已完成本次运行");
  await expect(sheet).toContainText("1.8 秒");
  await expect(sheet.locator('time[datetime="2026-10-17T09:10:07+08:00"]')).toBeVisible();
});

test("TEST_FIXTURE tool failures show only a recognized stable error code", async ({ page }) => {
  const runId = "TEST_FIXTURE-tool-errors-24";
  const privateError = "provider detail PRIVATE_TOOL_ERROR_CANARY";
  const privateCanary = "PRIVATE_TOOL_RESULT_CANARY_24";
  await installRunFixture(page, {
    runId,
    status: "failed",
    timelineEvents: [
      fixtureEvent(runId, "tool.completed", 1, "2026-10-17T09:10:01+08:00", {
        tool_name: "inspect_journey",
        result_summary: { status: "COMPLETED" },
      }),
      fixtureEvent(runId, "tool.failed", 2, "2026-10-17T09:10:02+08:00", {
        tool_name: "inspect_journey",
        status: "failed",
        result_summary: { error_code: "MALFORMED_TOOL_ARGUMENTS" },
      }),
      fixtureEvent(runId, "tool.failed", 3, "2026-10-17T09:10:03+08:00", {
        tool_name: "inspect_journey",
        status: "failed",
        result_summary: { keys: ["error", "detail"] },
      }),
      fixtureEvent(runId, "run.failed", 4, "2026-10-17T09:10:04+08:00", { status: "failed" }),
    ],
  });

  const { sheet } = await openRunTrace(page);
  const completedTool = sheet.locator('[aria-label="Hermes 运行轨迹"] li').filter({
    hasText: "检查当前行程：已完成",
  });
  await expect(completedTool).toHaveCount(1);
  await expect(completedTool).not.toContainText("失败代码：");
  await expect(sheet.getByText("参数格式不正确", { exact: true })).toBeVisible();
  const failedToolsWithoutCode = sheet
    .locator('[aria-label="Hermes 运行轨迹"] li')
    .filter({ hasText: "检查当前行程：未完成" });
  await expect(failedToolsWithoutCode).toHaveCount(2);
  await expect(failedToolsWithoutCode.last()).not.toContainText("失败代码：");
  await expect(sheet.getByText("MALFORMED_TOOL_ARGUMENTS", { exact: true })).toHaveCount(0);
  await expect(sheet.getByText(privateError, { exact: true })).toHaveCount(0);
  await expect(sheet.getByText(privateCanary, { exact: true })).toHaveCount(0);
});

test("TEST_FIXTURE failed trace keeps start and failure milestones in a long event list", async ({ page }) => {
  const runId = "TEST_FIXTURE-failed-long-24";
  const toolEvents = Array.from({ length: 13 }, (_, index) => fixtureEvent(
    runId,
    "tool.completed",
    index + 2,
    `2026-10-17T09:10:${String(index + 1).padStart(2, "0")}+08:00`,
    {
      event_id: `TEST_FIXTURE-tool-${index + 1}`,
      tool_name: "inspect_journey",
      status: "completed",
      duration_ms: 300,
    },
  ));
  await installRunFixture(page, {
    runId,
    status: "failed",
    timelineEvents: [
      fixtureEvent(runId, "run.started", 1, "2026-10-17T09:10:00+08:00", { status: "running" }),
      ...toolEvents,
      fixtureEvent(runId, "run.failed", 15, "2026-10-17T09:11:00+08:00", { status: "failed" }),
    ],
  });

  const { run, sheet } = await openRunTrace(page);
  await expect(run).toContainText("运行失败");
  await expect(sheet).toContainText("Hermes 已开始处理");
  await expect(sheet).toContainText("Hermes 本次运行失败");
  await expect(sheet.locator('[aria-label="Hermes 运行轨迹"] li')).toHaveCount(13);
});
