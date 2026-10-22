import { expect, test, type APIRequestContext, type Page, type Route } from "@playwright/test";

const API = `http://127.0.0.1:${Number(process.env.CITYNEXUS_BACKEND_PORT ?? 8000)}`;
const placeId = "TEST_FIXTURE_PLACE_R86";
const planId = "TEST_FIXTURE_PLAN_R86";

test.use({ viewport: { width: 390, height: 844 }, hasTouch: true });

async function createSignedJourney(request: APIRequestContext): Promise<{
  journeyId: string;
  travelerId: string;
  bearer: string;
}> {
  const response = await request.post(`${API}/api/v1/travelers`, {
    data: {
      display_name: `TEST_FIXTURE R86 ${Date.now()}`,
      locale: "zh-CN",
      timezone: "Asia/Shanghai",
    },
  });
  if (!response.ok()) {
    throw new Error(`TEST_FIXTURE signed-session setup failed: HTTP ${response.status()}`);
  }
  const traveler = await response.json() as { id: string; access_token?: string };
  if (!traveler.access_token) {
    throw new Error("TEST_FIXTURE traveler response did not include a signed bearer.");
  }
  const cityCode = `CN-R86-TEST-${Date.now()}`;
  const created = await request.post(`${API}/api/v1/journeys`, {
    data: {
      traveler_id: traveler.id,
      title: "TEST_FIXTURE R86 Journey start status",
      city_code: cityCode,
      timezone: "Asia/Shanghai",
      start_at: new Date(Date.now() + 24 * 60 * 60 * 1000).toISOString(),
      end_at: new Date(Date.now() + 72 * 60 * 60 * 1000).toISOString(),
      budget: { amount_minor: 10000, currency: "CNY" },
    },
  });
  if (!created.ok()) {
    throw new Error(`TEST_FIXTURE Journey setup failed: HTTP ${created.status()}`);
  }
  const journey = await created.json() as { id?: string };
  if (!journey.id) {
    throw new Error("TEST_FIXTURE Journey response did not include an id.");
  }
  return { journeyId: journey.id, travelerId: traveler.id, bearer: traveler.access_token };
}

async function fulfill(route: Route, value: unknown): Promise<void> {
  await route.fulfill({
    status: 200,
    contentType: "application/json",
    body: JSON.stringify(value),
  });
}

async function useSignedFixtureJourney(
  page: Page,
  journeyId: string,
  travelerId: string,
  bearer: string,
): Promise<{
  setStartJourneyStatus: (status: "PLANNED" | "ACTIVE") => void;
  setPlanSelectionFailure: (reasonCode: string | null) => void;
}> {
  const journeyPath = `/api/v1/journeys/${journeyId}`;
  await page.addInitScript(({ journeyId, travelerId, bearer }) => {
    window.sessionStorage.setItem("citynexus.traveler.bearer", bearer);
    window.sessionStorage.setItem("citynexus.traveler.session-id", travelerId);
    window.localStorage.setItem("citynexus.locale", "zh-CN");
    window.localStorage.setItem("citynexus.revolution.firstlook.journey", JSON.stringify({
      id: journeyId,
      cityCode: "CN-TEST-FIXTURE",
      cityName: "连城",
      status: "DRAFT",
      ownerTravelerId: travelerId,
    }));
  }, { journeyId, travelerId, bearer });

  let startJourneyStatus: "PLANNED" | "ACTIVE" = "PLANNED";
  let planSelectionFailure: string | null = null;
  await page.route("**/api/v1/**", async (route) => {
    const { pathname } = new URL(route.request().url());

    if (pathname === "/api/v1/agent/runtime-status") {
      await fulfill(route, {
        runtime_identity: "TEST_FIXTURE",
        hermes_compat_configured: false,
        ai_state: "DISABLED",
        fixture_mode: "TEST_FIXTURE",
      });
      return;
    }
    if (pathname === `${journeyPath}/bootstrap-discovery/readiness`) {
      await fulfill(route, {
        journey_id: journeyId,
        provider: "overpass",
        provider_name: "TEST_FIXTURE provider",
        expected_recipient: "TEST_FIXTURE",
        status: "READY",
        reason_code: "READY",
        provider_grade: "TEST_PROVIDER",
        capability_state: "TEST_CAPABLE",
        external_request_allowed: false,
        test_only: true,
      });
      return;
    }
    if (pathname === `${journeyPath}/bootstrap-shortlist`) {
      await fulfill(route, {
        journey_id: journeyId,
        limit: 3,
        items: [],
        resume: null,
        pocket_walk: null,
      });
      return;
    }
    if (pathname === `${journeyPath}/bootstrap-discovery` && route.request().method() === "POST") {
      await fulfill(route, {
        journey_id: journeyId,
        status: "LIVE_RESULTS",
        receipt_id: "TEST_FIXTURE_RECEIPT_R86",
        expires_at: "2026-10-18T00:00:00+00:00",
        source_kind: "MANUAL_PUBLIC_CENTER",
        provider: "overpass",
        provider_provenance: "TEST_PROVIDER",
        attempts: [{ endpoint: "TEST_FIXTURE", answered: true, http_status: 200 }],
        candidates: [{
          candidate_id: placeId,
          provider_key: "overpass",
          name: "TEST_FIXTURE Gallery",
          category: "museum/gallery",
          external_id: "TEST_FIXTURE:node/86001",
          osm_type: "node",
          osm_id: "86001",
          source_url: null,
          latitude: 39.12,
          longitude: 117.2,
          coordinate_system: "WGS84",
          distance_m: 80,
          opening_state: "UNVERIFIED",
          selection_state: "READY_FOR_NATIVE_PLAN",
          selection_action: null,
          availability_confidence: "UNVERIFIED",
          price_state: "UNKNOWN",
          eta_state: "UNKNOWN",
          tags: ["TEST_FIXTURE"],
          opening_hours: {},
          opening_observed_at: "2026-10-17T00:00:00+00:00",
          opening_source: "TEST_FIXTURE",
          opening_claim: "NO_OPENING_TAG",
          opening_verification_state: "EXTERNAL_NOT_ATTESTED",
          opening_verification_action: "OPEN_SOURCE_PAGE",
          source_tags: {},
          public_access_state: "PUBLIC_ACCESS_UNVERIFIED",
          provider_provenance: "TEST_PROVIDER",
        }],
      });
      return;
    }
    if (pathname === `${journeyPath}/bootstrap-discovery/select`) {
      await fulfill(route, {
        journey_id: journeyId,
        selected_place_id: placeId,
        provider_key: "overpass",
        external_id: "TEST_FIXTURE:node/86001",
        plan_version_id: null,
        journey_status: "DRAFT",
        provider_provenance: "TEST_PROVIDER",
      });
      return;
    }
    if (pathname === `${journeyPath}/plans/generate`) {
      await fulfill(route, [{ id: planId, selectable: !planSelectionFailure }]);
      return;
    }
    if (pathname === `${journeyPath}/plans/${planId}/select`) {
      if (planSelectionFailure) {
        await route.fulfill({
          status: 409,
          contentType: "application/json",
          body: JSON.stringify({
            error: {
              code: "PLAN_NOT_SELECTABLE",
              reason_code: planSelectionFailure,
              message: "TEST_FIXTURE plan refusal",
            },
          }),
        });
        return;
      }
      await fulfill(route, { journey_id: journeyId, status: "PLANNED" });
      return;
    }
    if (pathname === `${journeyPath}/start`) {
      await fulfill(route, {
        journey_id: journeyId,
        active_plan_version_id: planId,
        current_activity_id: null,
        latest_event_id: null,
        projection_status: "READY",
        snapshot_at: "2026-10-17T00:00:00+00:00",
        upcoming_commitments: [],
        context: { journey_status: startJourneyStatus },
      });
      return;
    }

    await route.fulfill({
      status: 404,
      contentType: "application/json",
      body: JSON.stringify({ detail: "TEST_FIXTURE: no external or unconfigured API call" }),
    });
  });

  return {
    setStartJourneyStatus: (status) => {
      startJourneyStatus = status;
    },
    setPlanSelectionFailure: (reasonCode) => {
      planSelectionFailure = reasonCode;
    },
  };
}

test("TEST_FIXTURE on /revolution switches only after the signed start response is ACTIVE", async ({ page, request }) => {
  const { journeyId, travelerId, bearer } = await createSignedJourney(request);
  const controls = await useSignedFixtureJourney(page, journeyId, travelerId, bearer);

  await page.goto("/revolution");
  const quickExplore = page.getByTestId("rev-quick-explore");
  await expect(quickExplore).toBeVisible();

  await quickExplore.locator("details").filter({ hasText: "公开 OpenStreetMap 链接定位" }).locator("summary").click();
  await quickExplore.getByLabel("公开地图链接").fill("https://www.openstreetmap.org/#map=13/39.12/117.2");
  await quickExplore.getByTestId("rev-quick-apply-map-link").click();

  await page.getByTestId("rev-quick-find-places").click();
  await expect(page.getByTestId("rev-quick-results")).toContainText("TEST_FIXTURE Gallery");
  await page.getByTestId(`rev-quick-formal-${placeId}`).click();

  const startPanel = page.getByTestId("bootstrap-native-start");
  await expect(startPanel).toBeVisible();
  await startPanel.getByTestId("bootstrap-unknown-cost-ack").check();
  await startPanel.getByTestId("bootstrap-native-start-submit").click();
  await expect(startPanel.getByTestId("bootstrap-native-start-message")).toHaveText(
    "行程还没启动成功。请稍后再试。",
  );
  await expect(startPanel).toBeVisible();

  controls.setStartJourneyStatus("ACTIVE");
  await startPanel.getByTestId("bootstrap-native-start-submit").click();
  await expect(startPanel).toBeHidden();
  await expect(page.getByTestId("revolution-real-operator")).toBeVisible();
});
test("TEST_FIXTURE opening-hours refusal gives a clear next step and returns to Explore", async ({ page, request }) => {
  const { journeyId, travelerId, bearer } = await createSignedJourney(request);
  const controls = await useSignedFixtureJourney(page, journeyId, travelerId, bearer);
  controls.setPlanSelectionFailure("UNRESOLVED_ACTIVITY_FACTS");

  await page.goto("/revolution");
  const quickExplore = page.getByTestId("rev-quick-explore");
  await expect(quickExplore).toBeVisible();
  await quickExplore.locator("details").filter({ hasText: "公开 OpenStreetMap 链接定位" }).locator("summary").click();
  await quickExplore.getByLabel("公开地图链接").fill("https://www.openstreetmap.org/#map=13/39.12/117.2");
  await quickExplore.getByTestId("rev-quick-apply-map-link").click();
  await quickExplore.getByTestId("rev-quick-find-places").click();
  await expect(page.getByTestId("rev-quick-results")).toContainText("TEST_FIXTURE Gallery");
  await quickExplore.getByTestId("rev-quick-formal-TEST_FIXTURE_PLACE_R86").click();

  const startPanel = page.getByTestId("bootstrap-native-start");
  await startPanel.getByTestId("bootstrap-unknown-cost-ack").check();
  await startPanel.getByTestId("bootstrap-native-start-submit").click();
  await expect(startPanel.getByTestId("bootstrap-native-start-message")).toHaveText(
    "营业时间没有可靠来源，暂时无法生成行程。查看地点信息或更换地点后再试。",
  );

  await startPanel.getByTestId("bootstrap-native-start-cancel").click();
  await expect(startPanel).toBeHidden();
  await expect(page.getByTestId("rev-mobile-screen-explore")).toBeVisible();
});
