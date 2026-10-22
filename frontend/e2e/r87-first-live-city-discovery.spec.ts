import { expect, test, type APIRequestContext } from "@playwright/test";

const API = `http://127.0.0.1:${Number(process.env.CITYNEXUS_BACKEND_PORT ?? 8000)}`;

async function post<T>(request: APIRequestContext, path: string, data: unknown): Promise<T> {
  const response = await request.post(`${API}${path}`, { data });
  if (!response.ok()) throw new Error(`${path} -> ${response.status()}: ${(await response.text()).slice(0, 240)}`);
  return response.json() as Promise<T>;
}

test("R87 keeps an ungrounded live candidate out of native start and leaves a grounded choice actionable", async ({ page, request }) => {
  const traveler = await post<{ id: string; access_token: string }>(request, "/api/v1/travelers", {
    display_name: `R87 browser ${Date.now()}`,
    locale: "en-GB",
    timezone: "Asia/Shanghai",
  });
  const journey = await post<{ id: string }>(request, "/api/v1/journeys", {
    traveler_id: traveler.id,
    title: "R87 browser live discovery",
    city_code: `CN-R87-BROWSER-${Date.now()}`,
    timezone: "Asia/Shanghai",
    start_at: "2026-10-13T10:00:00+08:00",
    end_at: "2026-10-14T18:00:00+08:00",
    budget: { amount_minor: 10000, currency: "CNY" },
  });
  const unknownId = "00000000-0000-4000-8000-000000000871";
  const groundedId = "00000000-0000-4000-8000-000000000872";
  let selectCalls = 0;
  let discoveryCalls = 0;
  await page.addInitScript(({ journeyId, token }) => {
    localStorage.setItem("citynexus.v8.journey_id", journeyId);
    sessionStorage.setItem("citynexus.traveler.bearer", token);
  }, { journeyId: journey.id, token: traveler.access_token });
  await page.route(`**/api/v1/journeys/${journey.id}/bootstrap-discovery/readiness`, async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        journey_id: journey.id,
        provider: "overpass",
        provider_name: "R87 fixture provider",
        expected_recipient: "R87 fixture provider",
        status: "READY",
        reason_code: "READY",
        provider_grade: "TEST_PROVIDER",
        capability_state: "TEST_CAPABLE",
        external_request_allowed: true,
        test_only: true,
      }),
    });
  });
  await page.route(`**/api/v1/journeys/${journey.id}/bootstrap-discovery`, async (route) => {
    discoveryCalls += 1;
    if (discoveryCalls <= 2) {
      const categoryRejection = discoveryCalls === 1;
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          journey_id: journey.id,
          status: "LIVE_ZERO_RESULTS",
          result_state: "ZERO",
          receipt_id: categoryRejection
            ? "00000000-0000-4000-8000-000000000874"
            : "00000000-0000-4000-8000-000000000875",
          expires_at: "2026-10-14T00:00:00+00:00",
          source_kind: "MANUAL_PUBLIC_CENTER",
          provider: "overpass",
          provider_provenance: "TEST_PROVIDER",
          attempts: [{ endpoint: "https://overpass-api.de/api/interpreter", answered: true, http_status: 200 }],
          candidates: [],
          filter_summary: {
            raw_count: 1,
            accepted_count: 0,
            rejected_by_reason: {
              provider_mismatch: 0,
              invalid_identity: 0,
              missing_name: categoryRejection ? 1 : 0,
              invalid_coordinates: categoryRejection ? 0 : 1,
              invalid_distance: 0,
              out_of_radius: 0,
              restricted_access: 0,
              duplicate: 0,
            },
          },
        }),
      });
      return;
    }
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        journey_id: journey.id,
        status: "LIVE_RESULTS",
        receipt_id: "00000000-0000-4000-8000-000000000873",
        expires_at: "2026-10-14T00:00:00+00:00",
        source_kind: "MANUAL_PUBLIC_CENTER",
        provider: "overpass",
        provider_provenance: "LIVE_OPENSTREETMAP_OVERPASS",
        attempts: [{ endpoint: "https://overpass-api.de/api/interpreter", answered: true, http_status: 200 }],
        candidates: [
          {
            candidate_id: unknownId,
            name: "Live Gallery Without Hours",
            category: "gallery",
            external_id: "overpass:node/87001",
            osm_type: "node",
            osm_id: "87001",
            source_url: "https://www.openstreetmap.org/node/87001",
            latitude: 39.12,
            longitude: 117.2,
            coordinate_system: "WGS84",
            distance_m: 80,
            opening_state: "UNKNOWN",
            selection_state: "OPENING_UNVERIFIED",
            selection_action: "VERIFY_OPENING_SOURCE_OR_CHOOSE_ANOTHER_CANDIDATE",
            availability_confidence: "UNVERIFIED",
            price_state: "UNKNOWN",
            eta_state: "UNKNOWN",
            tags: ["gallery", "real_city"],
          },
          {
            candidate_id: groundedId,
            name: "Live Gallery With Hours",
            category: "gallery",
            external_id: "overpass:node/87002",
            osm_type: "node",
            osm_id: "87002",
            source_url: "https://www.openstreetmap.org/node/87002",
            latitude: 39.121,
            longitude: 117.201,
            coordinate_system: "WGS84",
            distance_m: 120,
            opening_state: "VERIFIED_PROVIDER",
            selection_state: "READY_FOR_NATIVE_PLAN",
            selection_action: null,
            availability_confidence: "UNVERIFIED",
            price_state: "UNKNOWN",
            eta_state: "UNKNOWN",
            tags: ["gallery", "real_city"],
          },
        ],
      }),
    });
  });
  await page.route(`**/api/v1/journeys/${journey.id}/bootstrap-discovery/select`, async (route) => {
    selectCalls += 1;
    const body = route.request().postDataJSON() as { candidate_id: string };
    expect(body.candidate_id).toBe(groundedId);
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        journey_id: journey.id,
        selected_place_id: groundedId,
        plan_version_id: null,
        journey_status: "DRAFT",
        provider_provenance: "LIVE_OPENSTREETMAP_OVERPASS",
      }),
    });
  });
  await page.goto("/v8/hub", { waitUntil: "domcontentloaded" });
  const panel = page.getByTestId("bootstrap-discovery");
  await expect(panel).toBeVisible();
  await panel.locator("details.rev-manual-coordinates summary").click();
  await panel.getByTestId("bootstrap-latitude").fill("39.12");
  await panel.getByTestId("bootstrap-longitude").fill("117.2");
  await panel.getByTestId("bootstrap-city-label-confirm").check();
  await panel.getByTestId("bootstrap-intent-ART_HISTORY").click();
  await panel.getByTestId("bootstrap-provider-consent").check();
  await expect(panel.getByTestId("bootstrap-search")).toBeEnabled();
  await panel.getByTestId("bootstrap-search").click();
  const zeroResultGuidance = panel.getByTestId("bootstrap-zero-result-guidance");
  await expect(zeroResultGuidance.locator('[role="status"]')).toHaveText("附近暂时没有合适的地点，试试更换地点类型。");
  const categoryAction = zeroResultGuidance.getByTestId("bootstrap-zero-result-change-category");
  await expect(categoryAction).toHaveText("更换地点类型");
  const categoryActionBounds = await categoryAction.boundingBox();
  expect(categoryActionBounds?.width ?? 0).toBeGreaterThanOrEqual(44);
  expect(categoryActionBounds?.height ?? 0).toBeGreaterThanOrEqual(44);
  await expect(panel.getByTestId("revolution-next-action")).toHaveCount(0);
  await expect(panel.getByTestId("bootstrap-discovery-outcome")).toHaveCount(0);
  expect(discoveryCalls).toBe(1);
  await zeroResultGuidance.getByTestId("bootstrap-zero-result-change-category").click();
  expect(discoveryCalls).toBe(1);
  await expect(panel.getByTestId("bootstrap-intent-required")).toBeVisible();
  await panel.getByTestId("bootstrap-intent-GREEN_WALK").click();
  await panel.getByTestId("bootstrap-provider-consent").check();
  await expect(panel.getByTestId("bootstrap-search")).toBeEnabled();
  await panel.getByTestId("bootstrap-search").click();
  const centerGuidance = panel.getByTestId("bootstrap-zero-result-guidance");
  await expect(centerGuidance.locator('[role="status"]')).toHaveText("附近暂时没有合适的地点，试试更换搜索中心。");
  const centerAction = centerGuidance.getByTestId("bootstrap-zero-result-change-center");
  await expect(centerAction).toHaveText("更换搜索中心");
  const centerActionBounds = await centerAction.boundingBox();
  expect(centerActionBounds?.width ?? 0).toBeGreaterThanOrEqual(44);
  expect(centerActionBounds?.height ?? 0).toBeGreaterThanOrEqual(44);
  expect(discoveryCalls).toBe(2);
  await centerGuidance.getByTestId("bootstrap-zero-result-change-center").click();
  expect(discoveryCalls).toBe(2);
  await expect(panel.getByTestId("bootstrap-public-area-picker")).toBeVisible();
  await panel.getByTestId("bootstrap-public-area-cancel").click();
  await panel.getByTestId("bootstrap-provider-consent").check();
  await expect(panel.getByTestId("bootstrap-search")).toBeEnabled();
  await panel.getByTestId("bootstrap-search").click();
  await expect(panel.getByTestId("bootstrap-results")).toContainText("Live Gallery Without Hours");
  await expect(panel.getByTestId(`bootstrap-opening-blocker-${unknownId}`)).toHaveText("Check opening times before choosing this place.");
  await expect(panel.getByTestId(`bootstrap-select-${unknownId}`)).toBeDisabled();
  await expect(panel.getByTestId(`bootstrap-select-${groundedId}`)).toBeEnabled();
  await panel.getByTestId(`bootstrap-select-${groundedId}`).click();
  expect(selectCalls).toBe(1);
});

