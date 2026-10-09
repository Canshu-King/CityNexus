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
  await panel.getByTestId("bootstrap-provider-consent").check();
  await panel.getByTestId("bootstrap-search").click();
  await expect(panel.getByTestId("bootstrap-results")).toContainText("Live Gallery Without Hours");
  await expect(panel.getByTestId(`bootstrap-opening-blocker-${unknownId}`)).toContainText("Verify the source");
  await expect(panel.getByTestId(`bootstrap-select-${unknownId}`)).toBeDisabled();
  await expect(panel.getByTestId(`bootstrap-select-${groundedId}`)).toBeEnabled();
  await panel.getByTestId(`bootstrap-select-${groundedId}`).click();
  expect(selectCalls).toBe(1);
});

