import { expect, test, type Page, type Route } from "@playwright/test";

/** Mobile shell UI coverage using explicit TEST_PROVIDER fixtures. */
const journeyId = "00000000-0000-4000-8000-000000000117";
const prefix = `**/api/v1/journeys/${journeyId}`;

async function fulfill(route: Route, value: unknown) {
  await route.fulfill({
    status: 200,
    contentType: "application/json",
    body: JSON.stringify(value),
  });
}

async function signedMockJourney(page: Page, saved = false) {
  await page.addInitScript(({ id }) => {
    window.sessionStorage.setItem("citynexus.traveler.bearer", "TEST_ONLY_SIGNED_FIXTURE_TOKEN");
    window.localStorage.setItem("citynexus.revolution.firstlook.journey", JSON.stringify({
      id,
      cityCode: "CN-RV-TEST",
      cityName: "连城",
      status: "DRAFT",
    }));
  }, { id: journeyId });
  await page.route("**/api/v1/agent/runtime-status", (r) => fulfill(r, {
    runtime_identity: "UNAVAILABLE",
    hermes_compat_configured: false,
    ai_state: "CONFIGURED_UNVERIFIED",
  }));
  await page.route(`${prefix}/bootstrap-discovery/readiness`, (r) => fulfill(r, {
    status: "READY",
    reason_code: "READY",
    expected_recipient: "TEST_PROVIDER",
    provider_grade: "TEST_PROVIDER",
    external_request_allowed: false,
    test_only: true,
  }));
  await page.route(`${prefix}/bootstrap-shortlist`, (r) => fulfill(r, {
    journey_id: journeyId,
    items: [],
    resume: null,
    pocket_walk: saved ? {
      pocket_walk_id: "test-only-walk",
      journey_id: journeyId,
      revision: 2,
      plan_version_id: null,
      first_stop: { name: "TEST ONLY - 第一站" },
      second_stop: { name: "TEST ONLY - 第二站" },
      go_progress: {
        state: "HEADING_TO_SECOND",
        progress_revision: 5,
        progress_class: "USER_REPORTED_PROGRESS",
        physical_arrival_state: "NOT_PHYSICAL_ARRIVAL_PROVEN",
      },
    } : null,
  }));
}

test.describe("Revolution Mobile-First UI fixture", () => {
  test.use({ viewport: { width: 390, height: 844 }, hasTouch: true });

  test("an unstarted visitor can reach all three mobile tabs", async ({ page }, testInfo) => {
    let providerOrAiPosts = 0;
    page.on("request", (request) => {
      if (request.method() === "POST" && /bootstrap-city-search|trial-ai-discovery|bootstrap-discovery/.test(request.url())) {
        providerOrAiPosts += 1;
      }
    });
    await page.route("**/api/v1/agent/runtime-status", (r) => fulfill(r, {
      runtime_identity: "UNAVAILABLE",
      hermes_compat_configured: false,
      ai_state: "DISABLED",
    }));
    await page.goto("/revolution");
    await expect(page.getByTestId("rev-mobile-welcome")).toBeVisible();
    await expect(page.getByTestId("rev-firstlook-city")).toHaveValue("连城");
    await expect(page.getByTestId("rev-firstlook-start")).toBeVisible();
    const destinationBounds = await page.getByTestId("rev-firstlook-city").boundingBox();
    expect(destinationBounds?.height ?? 999).toBeLessThanOrEqual(64);
    await page.screenshot({ path: testInfo.outputPath("mobile-welcome-TEST-FIXTURE.png"), fullPage: true });
    const nav = page.getByTestId("rev-mobile-bottom-nav");
    await expect(nav).toBeVisible();
    await page.getByTestId("rev-mobile-tab-trips").click();
    await expect(page.getByTestId("rev-mobile-empty-trips")).toBeVisible();
    await page.getByTestId("rev-mobile-empty-start").click();
    await expect(page.getByTestId("rev-mobile-welcome")).toBeVisible();
    await page.getByTestId("rev-mobile-tab-me").click();
    await expect(page.getByTestId("rev-mobile-empty-me")).toBeVisible();
    await page.getByTestId("rev-mobile-tab-explore").click();
    await expect(page.getByTestId("rev-mobile-welcome")).toBeVisible();
    expect(providerOrAiPosts).toBe(0);
    const fits = await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 2);
    expect(fits).toBeTruthy();
  });

  test("does not call AI disabled while the local runtime check is still loading", async ({ page }) => {
    await signedMockJourney(page);
    let releaseRuntime!: () => void;
    const runtimeGate = new Promise<void>((resolve) => { releaseRuntime = resolve; });
    await page.route("**/api/v1/agent/runtime-status", async (route) => {
      await runtimeGate;
      await fulfill(route, {
        runtime_identity: "HERMES_COMPAT_ENDPOINT",
        hermes_compat_configured: true,
        ai_state: "CONFIGURED_UNVERIFIED",
      });
    });
    await page.goto("/revolution");
    await expect(page.getByTestId("revolution-agent-runtime").locator("summary")).toHaveText("正在连接 AI…");
    await expect(page.getByTestId("rev-quick-ai-guide").locator("small")).toHaveText("正在连接 AI…");
    await expect(page.getByTestId("rev-quick-consult-ai")).toBeDisabled();
    releaseRuntime();
    await expect(page.getByTestId("revolution-agent-runtime").locator("summary")).toHaveText("AI 网关已配置");
    await expect(page.getByTestId("rev-quick-ai-guide").locator("small")).toHaveText("可请求 AI 建议");
    await expect(page.getByTestId("rev-quick-consult-ai")).toBeEnabled();
  });

  test("three bottom tabs are tappable without submitting requests", async ({ page }, testInfo) => {
    await signedMockJourney(page);
    let upstreamCalls = 0;
    page.on("request", (request) => {
      if (/bootstrap-city-search|trial-ai-discovery|bootstrap-discovery\/pocket-walk|\/bootstrap-discovery$/.test(request.url()) && request.method() === "POST") {
        upstreamCalls += 1;
      }
    });
    await page.goto("/revolution");
    const bar = page.getByTestId("rev-mobile-bottom-nav");
    await expect(bar).toBeVisible();
    await expect(page.getByTestId("rev-mobile-screen-explore")).toBeVisible();
    await expect(page.getByTestId("rev-quick-explore")).toBeVisible();
    await expect(page.getByTestId("rev-quick-find-city")).toBeVisible();
    const searchBounds = await page.getByTestId("rev-quick-find-city").boundingBox();
    expect((searchBounds?.y ?? 9999) + (searchBounds?.height ?? 0)).toBeLessThan(820);
    await page.screenshot({ path: testInfo.outputPath("mobile-explore-TEST-FIXTURE.png"), fullPage: true });

    for (const tab of ["trips", "me", "explore"] as const) {
      const button = page.getByTestId("rev-mobile-tab-" + tab);
      const bounds = await button.boundingBox();
      expect(bounds?.height ?? 0).toBeGreaterThanOrEqual(44);
      await button.click();
      await expect(button).toHaveAttribute("aria-current", "page");
      await expect(page.getByTestId("rev-mobile-screen-" + tab)).toBeVisible();
      if (tab === "trips" || tab === "me") {
        await page.screenshot({ path: testInfo.outputPath("mobile-" + tab + "-TEST-FIXTURE.png"), fullPage: true });
      }
    }
    await expect(page.getByTestId("rev-quick-explore")).toBeVisible();
    expect(upstreamCalls).toBe(0);
    const fits = await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 2);
    expect(fits).toBeTruthy();
  });

  test("ACTIVE Journey shows signed Operator status and actions", async ({ page }, testInfo) => {
    await page.addInitScript((id) => {
      window.sessionStorage.setItem("citynexus.traveler.bearer", "TEST_ONLY_SIGNED_FIXTURE_TOKEN");
      window.localStorage.setItem("citynexus.locale", "zh-CN");
      window.localStorage.setItem("citynexus.revolution.firstlook.journey", JSON.stringify({
        id, cityCode: "CN-RV-TEST", cityName: "连城", status: "ACTIVE",
      }));
    }, journeyId);

    let signedOperatorReads = 0;
    let unrequestedModelWrites = 0;
    page.on("request", (request) => {
      if (request.method() !== "GET" && /agent\/commands|\/trial-ai-discovery|bootstrap-discovery/.test(request.url())) {
        unrequestedModelWrites += 1;
      }
    });

    await page.route("**/api/v1/agent/runtime-status", (route) => fulfill(route, {
      runtime_identity: "HERMES_COMPAT_ENDPOINT",
      hermes_compat_configured: true,
      ai_state: "CONFIGURED_UNVERIFIED",
    }));

    await page.route(`${prefix}/operator`, (route) => {
      signedOperatorReads += 1;
      expect(route.request().headers()["authorization"]).toBe("Bearer TEST_ONLY_SIGNED_FIXTURE_TOKEN");
      return fulfill(route, {
        journey_id: journeyId,
        state: "WATCHING",
        headline: "Watching your trip",
        enabled: true,
        standing_mission_id: "ONLY_A_FIXTURE",
        autonomy: "PLAN_ONLY",
        incident: null,
        decision: null,
        approval: null,
        brain: {
          state: "CONFIGURED_UNKNOWN", headline: "No verified AgentRun",
          configured_runtimes: ["HERMES_COMPAT_ENDPOINT"], preferred_runtime: null,
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
        timeline: [{
          at: "2026-10-16T06:00:00Z",
          kind: "operator.started", label: "Watching your trip",
        }],
        operator: { watching: true, will_continue_after_approval: false },
      });
    });

    await page.goto("/revolution");
    await page.getByTestId("rev-mobile-tab-trips").click();
    const card = page.getByTestId("rev-mobile-agent-work");
    await expect(card).toBeVisible();
    await expect(card.getByText("正在留意行程变化")).toBeVisible();
    await expect(card.getByText("行程监测中。")).toBeVisible();
    await card.getByText("查看最近工作记录").click();
    await expect(card.getByText("行程监测已启动")).toBeVisible();
    expect(signedOperatorReads).toBeGreaterThan(0);
    expect(unrequestedModelWrites).toBe(0);
    await page.screenshot({ path: testInfo.outputPath("mobile-active-operator-TEST-FIXTURE.png"), fullPage: true });
  });

  test("public place cards show provenance, uncertainty and a source link using TEST_PROVIDER data", async ({ page }, testInfo) => {
    await signedMockJourney(page);
    await page.route(`**/api/v1/journeys/${journeyId}/bootstrap-city-search`, (route) => fulfill(route, {
      journey_id: journeyId,
      status: "CITY_RESULTS",
      query: "连城",
      provider_provenance: "TEST_PROVIDER",
      provider_attempts: [],
      results: [{
        result_id: "fixture-area-1",
        name: "连城县",
        display_name: "连城县, 龙岩市",
        provider: "test",
        provider_provenance: "TEST_PROVIDER",
        osm_type: "node",
        osm_id: "10001",
        source_url: "https://www.openstreetmap.org/node/10001",
        latitude: 25.71,
        longitude: 116.75,
        coordinate_system: "WGS84",
        confidence: "CITY_CENTROID_UNCERTAIN",
        selection_state: "CAMERA_ONLY_TAP_REQUIRED",
        uncertainty: "TEST ONLY",
      }],
    }));
    await page.route(`**/api/v1/journeys/${journeyId}/bootstrap-discovery/readiness`, (route) => fulfill(route, {
      journey_id: journeyId,
      provider: "overpass",
      provider_name: "Controlled fixture provider",
      expected_recipient: "TEST_PROVIDER",
      status: "READY",
      reason_code: "READY",
      provider_grade: "TEST_PROVIDER",
      capability_state: "TEST_CAPABLE",
      external_request_allowed: false,
      test_only: true,
    }));
    await page.route(`**/api/v1/journeys/${journeyId}/bootstrap-discovery`, (route) => fulfill(route, {
      journey_id: journeyId,
      status: "LIVE_RESULTS",
      result_state: "FOUND_2+",
      receipt_id: "test-only-receipt",
      expires_at: "2099-01-01T00:00:00+00:00",
      source_kind: "MANUAL_PUBLIC_CENTER",
      provider: "overpass",
      provider_provenance: "TEST_PROVIDER",
      attempts: [],
      candidates: [{
        candidate_id: "test-place-1",
        name: "TEST ONLY · 连城步道",
        category: "park/garden",
        external_id: "overpass:node/10001",
        osm_type: "node",
        osm_id: "10001",
        source_url: "https://www.openstreetmap.org/node/10001",
        latitude: 25.71,
        longitude: 116.75,
        coordinate_system: "WGS84",
        distance_m: 420,
        opening_state: "UNKNOWN",
        selection_state: "OPENING_UNVERIFIED",
        selection_action: null,
        availability_confidence: "UNVERIFIED",
        price_state: "UNKNOWN",
        eta_state: "UNKNOWN",
        tags: [],
        opening_hours: {},
        opening_observed_at: "2026-10-16T00:00:00+00:00",
        opening_source: "TEST_PROVIDER",
        opening_claim: "NO_OPENING_TAG",
        opening_verification_state: "EXTERNAL_NOT_ATTESTED",
        opening_verification_action: "OPEN_SOURCE_PAGE",
        source_tags: {},
        public_access_state: "PUBLIC_ACCESS_UNVERIFIED",
        provider_provenance: "TEST_PROVIDER",
      }],
    }));

    await page.goto("/revolution");
    await page.getByTestId("rev-quick-find-city").click();
    await page.getByText("连城县, 龙岩市").click();
    await page.getByTestId("rev-quick-use-approx-center").click();
    await page.getByTestId("rev-quick-find-places").click();
    const card = page.getByTestId("rev-quick-place-card");
    await expect(card).toContainText("TEST ONLY · 连城步道");
    await expect(card).toContainText("测试地点");
    await expect(card).toContainText("营业与费用信息待补充");
    await expect(card.getByRole("link", { name: "查看 OpenStreetMap 来源" })).toHaveAttribute(
      "href",
      "https://www.openstreetmap.org/node/10001",
    );
    const chooseBounds = await card.getByRole("button", { name: /选择地点/ }).boundingBox();
    expect(chooseBounds?.height ?? 0).toBeGreaterThanOrEqual(44);
    await card.scrollIntoViewIfNeeded();
    await page.screenshot({
      path: testInfo.outputPath("mobile-place-card-TEST-PROVIDER-390x844.png"),
      fullPage: false,
    });
  });

  test("map tiles are opt-in, touch places a pin, and the approximate-area action remains available", async ({ page }) => {
    await signedMockJourney(page);
    let discoveryCalls = 0;
    await page.route("https://tile.openstreetmap.org/**", (route) => route.abort());
    await page.route(`**/api/v1/journeys/${journeyId}/bootstrap-city-search`, (route) => fulfill(route, {
      journey_id: journeyId,
      status: "CITY_RESULTS",
      query: "连城",
      provider_provenance: "TEST_PROVIDER",
      provider_attempts: [],
      results: [{
        result_id: "fixture-area-1",
        name: "连城县",
        display_name: "连城县, 龙岩市",
        provider: "test",
        provider_provenance: "TEST_PROVIDER",
        osm_type: "node",
        osm_id: "10001",
        source_url: "https://www.openstreetmap.org/node/10001",
        latitude: 25.71,
        longitude: 116.75,
        coordinate_system: "WGS84",
        confidence: "CITY_CENTROID_UNCERTAIN",
        selection_state: "CAMERA_ONLY_TAP_REQUIRED",
        uncertainty: "TEST ONLY",
      }],
    }));
    await page.route(`**/api/v1/journeys/${journeyId}/bootstrap-discovery`, async (route) => {
      discoveryCalls += 1;
      await fulfill(route, { status: "PROVIDER_DISABLED", candidates: [] });
    });

    await page.goto("/revolution");
    await page.getByTestId("rev-quick-find-city").click();
    await page.getByText("连城县, 龙岩市").click();
    await expect(page.getByTestId("rev-quick-use-approx-center")).toBeVisible();
    await page.getByText("想换具体位置？可以打开地图（可选）").click();
    await expect(page.getByTestId("rev-quick-load-map")).toBeVisible();
    await page.getByTestId("rev-quick-load-map").click();
    await expect(page.getByTestId("bootstrap-public-map-canvas")).toBeVisible();
    await expect(page.getByTestId("rev-quick-use-approx-center")).toBeVisible();
    await page.waitForFunction(() => {
      const host = document.querySelector<HTMLDivElement>("[data-testid='bootstrap-public-map-canvas']");
      const map = (host as (HTMLDivElement & { citynexusMap?: { isStyleLoaded?: () => boolean } }) | null)?.citynexusMap;
      return typeof map?.isStyleLoaded === "function" && map.isStyleLoaded();
    });
    const mapCanvas = page.locator("[data-testid='bootstrap-public-map-canvas'] canvas.maplibregl-canvas").first();
    await mapCanvas.scrollIntoViewIfNeeded();
    const mapBounds = await mapCanvas.boundingBox();
    expect(mapBounds).not.toBeNull();
    await mapCanvas.tap({
      position: {
        x: (mapBounds?.width ?? 0) / 2,
        y: (mapBounds?.height ?? 0) / 2,
      },
    });
    await expect(page.getByTestId("rev-quick-category")).toBeVisible();
    expect(discoveryCalls).toBe(0);
  });

  test("trip tab displays a saved TEST fixture itinerary", async ({ page }) => {
    await signedMockJourney(page, true);
    await page.goto("/revolution");
    await page.getByTestId("rev-mobile-tab-trips").click();
    await expect(page.getByTestId("rev-mobile-screen-trips").getByText("TEST ONLY - 第一站")).toBeVisible();
    await expect(page.getByTestId("rev-mobile-screen-trips").getByText("TEST ONLY - 第二站")).toBeVisible();
    await expect(page.getByTestId("rev-mobile-screen-trips").getByText("正在前往第二站")).toBeVisible();
    await page.getByRole("button", { name: "查看路线并继续 GO" }).click();
    await expect(page.getByTestId("rev-quick-walk")).toBeVisible();
  });

  test("ACTIVE mobile shows the signed Hermes run and returned tool events", async ({ page }, testInfo) => {
    const pageErrors: string[] = [];
    page.on("pageerror", (error) => pageErrors.push(error.message));
    page.on("console", (message) => { if (message.type() === "error") pageErrors.push(message.text()); });
    await page.addInitScript((id) => {
      window.sessionStorage.setItem("citynexus.traveler.bearer", "TEST_ONLY_SIGNED_FIXTURE_TOKEN");
      window.localStorage.setItem("citynexus.revolution.firstlook.journey", JSON.stringify({
        id, cityCode: "CN-RV-TEST", cityName: "连城", status: "ACTIVE",
      }));
    }, journeyId);
    await page.route("**/api/v1/agent/runtime-status", (route) => fulfill(route, {
      runtime_identity: "HERMES_NATIVE_MCP",
      hermes_native_gateway: { configured: true, reachable: true, ready: true, runs: true, events: true },
      hermes_compat_configured: false,
      ai_state: "CONFIGURED_UNVERIFIED",
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
      collective: { state: "SINGLE_TRAVELLER", mission_id: null, required_count: 1, response_count: 0, viewer_has_responded: false, members: [], options: [] },
      discovery: { state: "IDLE", attempt_count: 0, max_attempts: 1, raw_candidate_count: 0, materialized_place_count: 0 },
      timeline: [],
      operator: { watching: false, will_continue_after_approval: false },
    }));

    // This page also mounts LiveRecovery. Keep its read-only boot endpoints
    // explicit so missing TEST_FIXTURE data cannot turn a timeline test into
    // an unrelated React error boundary.
    await page.route(`${prefix}/experience`, (route) => fulfill(route, {
      active_plan: { id: "test-plan", status: "ACTIVE", activities: [], legs: [], disruptions: [] },
      recovery: null,
      experience_flags: { needs_review: false, recovery_required: false, staleness: false },
    }));
    await page.route(`${prefix}/twin`, (route) => fulfill(route, { id: "test-twin", context: {} }));
    await page.route(`${prefix}/plans`, (route) => fulfill(route, []));
    await page.route(`${prefix}/replans`, (route) => fulfill(route, []));
    await page.route(`${prefix}/guardian/pulse/latest`, (route) => fulfill(route, { pulse: null }));
    await page.route(`${prefix}/launch-setup`, (route) => fulfill(route, {}));
    await page.route(`${prefix}/guardian/autopilot/status`, (route) => fulfill(route, {
      enrollment: { enabled: false },
      watch: null,
      readiness: null,
    }));

    const runId = "hermes-test-run-21";
    const events = [
      { event_type: "semantic.interpreted", run_id: runId, event_id: "evt-0", sequence: 0, tool_name: null, friendly_label: "Interpret traveler request", status: "completed", timestamp: "2026-10-16T07:09:59Z", source: "HERMES_NATIVE" },
      { event_type: "mission.planned", run_id: runId, event_id: "evt-1", sequence: 1, tool_name: null, friendly_label: "Mission plan prepared", status: "completed", timestamp: "2026-10-16T07:09:59Z", source: "HERMES_NATIVE" },
      { event_type: "run.started", run_id: runId, event_id: "evt-2", sequence: 2, tool_name: null, friendly_label: "Hermes runtime", status: "started", timestamp: "2026-10-16T07:10:00Z", source: "HERMES_NATIVE" },
      { event_type: "tool.started", run_id: runId, event_id: "evt-3", sequence: 3, tool_name: "inspect_journey", friendly_label: "Inspect current Journey", status: "started", timestamp: "2026-10-16T07:10:01Z", source: "HERMES_NATIVE" },
      { event_type: "tool.completed", run_id: runId, event_id: "evt-4", sequence: 4, tool_name: "inspect_journey", friendly_label: "Inspect current Journey", status: "completed", timestamp: "2026-10-16T07:10:02Z", duration_ms: 850, source: "HERMES_NATIVE" },
      { event_type: "run.completed", run_id: runId, event_id: "evt-5", sequence: 5, tool_name: null, friendly_label: "Hermes runtime", status: "completed", timestamp: "2026-10-16T07:10:03Z", source: "HERMES_NATIVE" },
    ];
    let latestRun: NonNullable<import("../src/api/citynexus").CopilotResponse["agent_run"]> | null = null;
    let latestRunReads = 0;
    let copilotPosts = 0;
    await page.route(`${prefix}/agent/hermes/latest-run`, async (route) => {
      expect(route.request().headers()["authorization"]).toBe("Bearer TEST_ONLY_SIGNED_FIXTURE_TOKEN");
      latestRunReads += 1;
      await fulfill(route, { journey_id: journeyId, run: latestRun });
    });
    await page.route(`${prefix}/copilot/messages`, async (route) => {
      expect(route.request().headers()["authorization"]).toBe("Bearer TEST_ONLY_SIGNED_FIXTURE_TOKEN");
      expect(route.request().method()).toBe("POST");
      copilotPosts += 1;
      latestRun = {
        run_id: runId,
        status: "running",
        runtime_identity: "HERMES_NATIVE_MCP",
        provider_key: "TEST_FIXTURE",
        mission_id: "test-mission",
        reasoning_summary: "正在检查行程安排。",
        events_url: `${prefix}/agent/hermes/runs/${runId}/events`,
        timeline_url: `${prefix}/agent/hermes/runs/${runId}/timeline`,
        initial_events: [],
      };
      await fulfill(route, {
        message: "TEST FIXTURE：本次工具事件用于界面验证。",
        mode: "AI",
        verified_context_used: true,
        intent: { name: "REPLAN_REQUEST", confidence: 1, reason: "TEST_FIXTURE", entities: {}, provider: "TEST_FIXTURE", mode: "AI" },
        action: { type: "REQUEST_REPLAN" },
        what_if: null,
        event: null,
        verification: null,
        discovery: null,
        agent_run: latestRun,
        protected_commitments: [],
        evidence: { fixture: true },
        recommendations: [],
      });
    });
    await page.route(`${prefix}/agent/hermes/runs/${runId}/timeline`, async (route) => {
      expect(route.request().headers()["authorization"]).toBe("Bearer TEST_ONLY_SIGNED_FIXTURE_TOKEN");
      await fulfill(route, {
        run_id: runId,
        journey_id: journeyId,
        runtime_identity: "HERMES_NATIVE_MCP",
        events: [],
        observability: {
          run_id: runId, runtime_identity: "HERMES_NATIVE_MCP", current_mission: "test-mission",
          tool_count: 0, current_tool: "inspect_journey", completion_status: "running",
          gateway_decision: null, guardian_decision: null, total_duration_ms: 0,
        },
      });
    });
    await page.route(`${prefix}/agent/hermes/runs/${runId}/events`, async (route) => {
      expect(route.request().headers()["authorization"]).toBe("Bearer TEST_ONLY_SIGNED_FIXTURE_TOKEN");
      const body = events.map((event) =>
        `event: ${event.event_type}\r\ndata: ${JSON.stringify(event)}\r\n\r\n`,
      ).join("");
      await route.fulfill({ status: 200, contentType: "text/event-stream", body });
    });

    await page.goto("/revolution");
    await expect(page.getByTestId("revolution-agent-runtime").locator("summary")).toHaveText("Hermes 工具已就绪");
    if (await page.getByTestId("product-error-boundary").count()) {
      throw new Error("Mobile shell mounted its error boundary: " + (pageErrors.join(" | ") || "no pageerror captured"));
    }
    await page.getByTestId("rev-mobile-tab-trips").click();
    await expect.poll(() => latestRunReads).toBe(1);
    await expect(page.getByTestId("rev-mobile-hermes-empty-state")).toContainText("暂无助手运行记录");
    await page.getByTestId("rev-mobile-hermes-submit").click();
    const run = page.getByTestId("rev-mobile-hermes-run");
    await expect(run).toBeVisible();
    const sheet = page.getByTestId("rev-mobile-hermes-sheet");
    await expect(sheet).toBeVisible();
    await expect(sheet.getByText("测试数据")).toBeVisible();
    await expect(sheet.getByText("已完成", { exact: true })).toBeVisible();
    await expect(sheet.getByText("正在检查行程安排。")).toBeVisible();
    await expect(sheet.getByText("已理解你的需求")).toBeVisible();
    await expect(sheet.getByText("已形成执行计划")).toBeVisible();
    await expect(sheet.getByText("正在检查当前行程")).toBeVisible();
    await expect(sheet.getByText("检查当前行程：已完成")).toBeVisible();
    await expect(sheet.getByText("850 毫秒")).toBeVisible();
    await expect(run.getByText("inspect_journey")).toHaveCount(0);
    await page.screenshot({ path: testInfo.outputPath("mobile-hermes-run-TEST-FIXTURE-390x844.png"), fullPage: false });
    await page.getByRole("button", { name: "关闭工作过程" }).click();
    await expect(sheet).not.toBeVisible();
    await expect(run).toContainText(/\d+ 条示例事件/);
    await page.getByRole("button", { name: "查看工作过程" }).click();
    await expect(sheet).toBeVisible();

    await page.reload();
    await page.getByTestId("rev-mobile-tab-trips").click();
    await expect.poll(() => latestRunReads).toBe(2);
    await expect(page.getByTestId("rev-mobile-hermes-run")).toBeVisible();
    const restoredSheet = page.getByTestId("rev-mobile-hermes-sheet");
    await expect(restoredSheet).not.toBeVisible();
    await page.getByRole("button", { name: "查看工作过程" }).click();
    await expect(restoredSheet).toBeVisible();
    await expect(restoredSheet.getByText("检查当前行程：已完成")).toBeVisible();
    await expect(restoredSheet.getByRole("button", { name: "停止本次运行" })).toHaveCount(0);
    expect(copilotPosts).toBe(1);
    await page.screenshot({ path: testInfo.outputPath("mobile-hermes-resume-TEST-FIXTURE-390x844.png"), fullPage: false });
    const fits = await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 2);
    expect(fits).toBeTruthy();
  });
});
