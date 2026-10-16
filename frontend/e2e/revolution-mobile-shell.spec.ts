import { expect, test, type Page, type Route } from "@playwright/test";

/**
 * UI FIXTURE ONLY: verifies the new mobile shell/navigation semantics.
 * Every returned Journey is an explicitly fake TEST_PROVIDER stub.
 * This cannot prove signed backend access, physical arrival, real POI or AI.
 */
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

  test("an unstarted visitor sees a clean, usable destination CTA", async ({ page }, testInfo) => {
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
    await expect(page.getByTestId("rev-mobile-bottom-nav")).toHaveCount(0);
    const fits = await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 2);
    expect(fits).toBeTruthy();
  });

  test("three bottom tabs are tappable and never submit provider or model requests", async ({ page }, testInfo) => {
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

  test("ACTIVE Journey shows signed server Operator status and audited actions, not invented AgentRun", async ({ page }, testInfo) => {
    await page.addInitScript((id) => {
      window.sessionStorage.setItem("citynexus.traveler.bearer", "TEST_ONLY_SIGNED_FIXTURE_TOKEN");
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
    await expect(card.getByText("正在监测行程，不代表模型正在调用工具。")).toBeVisible();
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
    await expect(card).toContainText("营业与费用需自行核实");
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
    const mapCanvas = page.getByTestId("bootstrap-public-map-canvas");
    await mapCanvas.scrollIntoViewIfNeeded();
    const mapBounds = await mapCanvas.boundingBox();
    expect(mapBounds).not.toBeNull();
    await page.touchscreen.tap(
      (mapBounds?.x ?? 0) + (mapBounds?.width ?? 0) / 2,
      (mapBounds?.y ?? 0) + (mapBounds?.height ?? 0) / 2,
    );
    await expect(page.getByTestId("rev-quick-category")).toBeVisible();
    expect(discoveryCalls).toBe(0);
  });

  test("trip tab reflects only a saved TEST fixture, never a fabricated itinerary", async ({ page }) => {
    await signedMockJourney(page, true);
    await page.goto("/revolution");
    await page.getByTestId("rev-mobile-tab-trips").click();
    await expect(page.getByTestId("rev-mobile-screen-trips").getByText("TEST ONLY - 第一站")).toBeVisible();
    await expect(page.getByTestId("rev-mobile-screen-trips").getByText("TEST ONLY - 第二站")).toBeVisible();
    await expect(page.getByTestId("rev-mobile-screen-trips").getByText("正在前往第二站")).toBeVisible();
    await page.getByRole("button", { name: "查看路线并继续 GO" }).click();
    await expect(page.getByTestId("rev-quick-walk")).toBeVisible();
  });
});
