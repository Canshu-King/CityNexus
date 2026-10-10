import { expect, test, type APIRequestContext } from "@playwright/test";

const API = `http://127.0.0.1:${Number(process.env.CITYNEXUS_BACKEND_PORT ?? 8000)}`;

async function post<T>(request: APIRequestContext, path: string, data: unknown): Promise<T> {
  const response = await request.post(`${API}${path}`, { data });
  if (!response.ok()) throw new Error(`${path} -> ${response.status()}: ${(await response.text()).slice(0, 240)}`);
  return response.json() as Promise<T>;
}

test("R86 turns one source-linked place into an explicit native Journey start", async ({ page, request }) => {
  const traveler = await post<{ id: string; access_token: string }>(request, "/api/v1/travelers", {
    display_name: `R86 browser ${Date.now()}`,
    locale: "en-GB",
    timezone: "Asia/Shanghai",
  });
  const journey = await post<{ id: string }>(request, "/api/v1/journeys", {
    traveler_id: traveler.id,
    title: "R86 browser first native Journey",
    city_code: `CN-R86-BROWSER-${Date.now()}`,
    timezone: "Asia/Shanghai",
    start_at: "2026-10-11T10:00:00+08:00",
    end_at: "2026-10-12T18:00:00+08:00",
    budget: { amount_minor: 10000, currency: "CNY" },
  });
  const placeId = "00000000-0000-4000-8000-000000000086";
  const planId = "00000000-0000-4000-8000-000000000087";
  const activityId = "00000000-0000-4000-8000-000000000088";
  const requestPaths: string[] = [];
  page.on("request", (incoming) => {
    const url = new URL(incoming.url());
    if (url.pathname.includes(`/journeys/${journey.id}/`)) requestPaths.push(`${incoming.method()} ${url.pathname}`);
  });
  await page.addInitScript(({ journeyId, token }) => {
    localStorage.setItem("citynexus.v8.journey_id", journeyId);
    sessionStorage.setItem("citynexus.traveler.bearer", token);
  }, { journeyId: journey.id, token: traveler.access_token });

  await page.route(`**/api/v1/journeys/${journey.id}/bootstrap-discovery`, async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        journey_id: journey.id,
        status: "LIVE_RESULTS",
        receipt_id: "00000000-0000-4000-8000-000000000089",
        expires_at: "2026-10-10T00:00:00+00:00",
        source_kind: "MANUAL_PUBLIC_CENTER",
        provider: "overpass",
        provider_provenance: "LIVE_OPENSTREETMAP_OVERPASS",
        attempts: [{ endpoint: "https://overpass.test/api/interpreter", answered: true, http_status: 200 }],
        candidates: [{
          candidate_id: placeId,
          name: "R86 Browser Gallery",
          category: "gallery",
          external_id: "overpass:node/86001",
          osm_type: "node",
          osm_id: "86001",
          source_url: "https://www.openstreetmap.org/node/86001",
          latitude: 39.12,
          longitude: 117.2,
          coordinate_system: "WGS84",
          distance_m: 80,
          opening_state: "VERIFIED_PROVIDER",
          selection_state: "READY_FOR_NATIVE_PLAN",
          selection_action: null,
          availability_confidence: "UNVERIFIED",
          price_state: "UNKNOWN",
          eta_state: "UNKNOWN",
          tags: ["gallery", "real_city"],
        }],
      }),
    });
  });
  await page.route(`**/api/v1/journeys/${journey.id}/bootstrap-discovery/select`, async (route) => {
    const body = route.request().postDataJSON() as { candidate_id: string };
    expect(body.candidate_id).toBe(placeId);
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        journey_id: journey.id,
        selected_place_id: placeId,
        plan_version_id: null,
        journey_status: "DRAFT",
        provider_provenance: "LIVE_OPENSTREETMAP_OVERPASS",
      }),
    });
  });
  await page.route(`**/api/v1/journeys/${journey.id}/plans/generate`, async (route) => {
    const body = route.request().postDataJSON() as Record<string, unknown>;
    expect(body.allow_single_place).toBe(true);
    expect(body.allow_unknown_cost).toBe(true);
    expect(body.place_ids).toEqual([placeId]);
    await route.fulfill({
      status: 201,
      contentType: "application/json",
      body: JSON.stringify([{
        id: planId,
        journey_id: journey.id,
        version_no: 1,
        planning_mode: "balanced",
        status: "CANDIDATE",
        source: "INITIAL",
        parent_plan_version_id: null,
        total_cost: { amount_minor: 0, currency: "CNY" },
        total_cost_status: "PARTIAL_UNKNOWN",
        utility_score: 0.5,
        score_breakdown: null,
        activities: [{
          id: activityId,
          sequence_no: 1,
          title: "R86 Browser Gallery",
          activity_type: "visit",
          place_id: placeId,
          city_service_id: null,
          start_at: "2026-10-11T10:00:00+08:00",
          end_at: "2026-10-11T11:00:00+08:00",
          travel_from_prev_min: 0,
          estimated_cost: { amount_minor: 0, currency: "CNY" },
          cost_status: "UNKNOWN",
          status: "PLANNED",
          locked: false,
          metadata: { price_known: false, cost_included_in_total: false },
        }],
        explanation: {
          authority_state: "COST_UNKNOWN_ACCEPTED",
          cost_unknown_policy: "USER_ACCEPTS_UNKNOWN_PRICE_NOT_INCLUDED",
          cost_summary: { known_subtotal_minor: 0, unknown_item_count: 1, unknown_cost_included: false },
        },
      }]),
    });
  });
  await page.route(`**/api/v1/journeys/${journey.id}/plans/${planId}/select`, async (route) => {
    await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ id: journey.id }) });
  });
  await page.route(`**/api/v1/journeys/${journey.id}/start`, async (route) => {
    await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ journey_id: journey.id, active_plan_version_id: planId, projection_status: "READY", snapshot_at: "2026-10-10T00:00:00Z", context: {} }) });
  });

  await page.goto("/v8/hub", { waitUntil: "domcontentloaded" });
  const discovery = page.getByTestId("bootstrap-discovery");
  await expect(discovery).toBeVisible();
  await discovery.getByTestId("bootstrap-provider-consent").check();
  await discovery.getByTestId("bootstrap-search").click();
  await expect(discovery.getByTestId("bootstrap-results")).toContainText("R86 Browser Gallery");
  await discovery.getByTestId(`bootstrap-select-${placeId}`).click();

  const nativeStart = page.getByTestId("bootstrap-native-start");
  await expect(nativeStart).toBeVisible();
  await nativeStart.getByTestId("bootstrap-native-start-submit").click();
  await expect(nativeStart.getByTestId("bootstrap-native-start-message")).toContainText("Confirm");
  await nativeStart.getByTestId("bootstrap-unknown-cost-ack").check();
  await nativeStart.getByTestId("bootstrap-native-start-submit").click();
  await expect(nativeStart).toBeHidden();
  expect(requestPaths.some((path) => path.includes("/agent/commands"))).toBe(false);
  expect(requestPaths.some((path) => path.includes("/bookings"))).toBe(false);
});

