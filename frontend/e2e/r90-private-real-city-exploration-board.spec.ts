import { expect, test, type APIRequestContext, type Page } from "@playwright/test";

const API = `http://127.0.0.1:${Number(process.env.CITYNEXUS_BACKEND_PORT ?? 8000)}`;

test.use({ viewport: { width: 390, height: 844 } });

async function post<T>(request: APIRequestContext, path: string, data: unknown): Promise<T> {
  const response = await request.post(`${API}${path}`, { data });
  if (!response.ok()) throw new Error(`${path} -> ${response.status()}: ${(await response.text()).slice(0, 240)}`);
  return response.json() as Promise<T>;
}

async function mockR90Board(page: Page, journeyId: string) {
  const candidateId = "00000000-0000-4000-8000-000000000901";
  const shortlistId = "00000000-0000-4000-8000-000000000902";
  const receiptId = "00000000-0000-4000-8000-000000000903";
  let saved = false;
  let previewCalls = 0;
  const item = {
    shortlist_id: shortlistId,
    journey_id: journeyId,
    provider_key: "overpass",
    external_id: "overpass:node/90001",
    name: "R90 Mobile Gallery",
    category: "gallery",
    latitude: 39.1205,
    longitude: 117.2005,
    coordinate_system: "WGS84",
    source_url: "https://www.openstreetmap.org/node/90001",
    source_provenance: "LIVE_OPENSTREETMAP_OVERPASS",
    captured_at: "2026-10-10T10:00:00+00:00",
    opening_hours: { status: "UNKNOWN" },
    opening_state: "UNKNOWN",
    price_state: "UNKNOWN",
    eta_state: "UNKNOWN",
    source_tags: {},
    distance_m: 80,
    distance_basis: "MANUAL_PUBLIC_CENTER",
    status: "SAVED",
    created_at: "2026-10-10T10:00:00+00:00",
    updated_at: "2026-10-10T10:00:00+00:00",
  };
  await page.route(`**/api/v1/journeys/${journeyId}/bootstrap-shortlist`, async (route) => {
    if (route.request().method() === "GET") {
      await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ journey_id: journeyId, limit: 3, items: saved ? [item] : [] }) });
      return;
    }
    const body = route.request().postDataJSON() as Record<string, unknown>;
    expect(body).toEqual({ receipt_id: receiptId, candidate_id: candidateId });
    saved = true;
    await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(item) });
  });
  await page.route(`**/api/v1/journeys/${journeyId}/bootstrap-shortlist/${shortlistId}`, async (route) => {
    expect(route.request().method()).toBe("DELETE");
    saved = false;
    await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ journey_id: journeyId, shortlist_id: shortlistId, removed: true, place_id: null }) });
  });
  await page.route(`**/api/v1/journeys/${journeyId}/bootstrap-shortlist/${shortlistId}/preview`, async (route) => {
    previewCalls += 1;
    expect(route.request().postDataJSON()).toEqual({ public_map_consent: true });
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        preview_id: "00000000-0000-4000-8000-000000000904",
        status: "PUBLIC_DESTINATION_READY",
        journey_id: journeyId,
        shortlist_id: shortlistId,
        authorization_basis: "SAVED_PUBLIC_IDENTITY",
        destination: {
          name: item.name,
          external_id: item.external_id,
          source_url: item.source_url,
          latitude: item.latitude,
          longitude: item.longitude,
          coordinate_system: "WGS84",
          map_url: "https://www.openstreetmap.org/?mlat=39.1205000&mlon=117.2005000#map=18/39.1205000/117.2005000",
        },
        opening: {
          state: "UNKNOWN",
          raw: null,
          source_tags: {},
          source: "LIVE_OPENSTREETMAP_OVERPASS",
          observed_at: item.captured_at,
          claim: "NO_OPENING_TAG",
          verification_state: "EXTERNAL_NOT_ATTESTED",
          verification_action: "OPEN_SOURCE_PAGE",
        },
        explore_state: "DRAFT_EXPLORE_ONLY",
        shared_fields: ["public_destination", "osm_id", "source_url"],
        withheld_fields: ["origin", "foreground_gps", "query_center", "member_id", "traveler_id", "receipt_id"],
        plan_version_id: null,
        selected_place_id: null,
      }),
    });
  });
  await page.route(`**/api/v1/journeys/${journeyId}/bootstrap-discovery`, async (route) => {
    expect(route.request().postDataJSON()).toMatchObject({ provider_consent: true, source_kind: "MANUAL_PUBLIC_CENTER" });
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        journey_id: journeyId,
        status: "LIVE_RESULTS",
        receipt_id: receiptId,
        expires_at: "2026-10-14T00:00:00+00:00",
        source_kind: "MANUAL_PUBLIC_CENTER",
        provider: "overpass",
        provider_provenance: "LIVE_OPENSTREETMAP_OVERPASS",
        attempts: [{ endpoint: "TEST_PROVIDER", answered: true, http_status: 200 }],
        candidates: [{
          candidate_id: candidateId,
          name: item.name,
          category: item.category,
          external_id: item.external_id,
          osm_type: "node",
          osm_id: "90001",
          source_url: item.source_url,
          latitude: item.latitude,
          longitude: item.longitude,
          coordinate_system: "WGS84",
          distance_m: item.distance_m,
          opening_state: "UNKNOWN",
          selection_state: "OPENING_UNVERIFIED",
          selection_action: "VERIFY_OPENING_SOURCE_OR_CHOOSE_ANOTHER_CANDIDATE",
          availability_confidence: "UNVERIFIED",
          price_state: "UNKNOWN",
          eta_state: "UNKNOWN",
          tags: ["gallery"],
          opening_hours: { status: "UNKNOWN" },
          opening_observed_at: item.captured_at,
          opening_source: "OpenStreetMap/Overpass",
          opening_claim: "NO_OPENING_TAG",
          opening_verification_state: "EXTERNAL_NOT_ATTESTED",
          opening_verification_action: "OPEN_SOURCE_PAGE",
          source_tags: {},
        }],
      }),
    });
  });
  await page.route("https://www.openstreetmap.org/**", async (route) => {
    await route.fulfill({ status: 200, contentType: "text/html", body: "public destination" });
  });
  return { candidateId, shortlistId, getPreviewCalls: () => previewCalls };
}

test("R90 restores a private shortlist and requires fresh consent for its public map", async ({ page, request }) => {
  const traveler = await post<{ id: string; access_token: string }>(request, "/api/v1/travelers", {
    display_name: `R90 mobile ${Date.now()}`,
    locale: "en-GB",
    timezone: "Asia/Shanghai",
  });
  const journey = await post<{ id: string }>(request, "/api/v1/journeys", {
    traveler_id: traveler.id,
    title: "R90 private board",
    city_code: `CN-R90-BROWSER-${Date.now()}`,
    timezone: "Asia/Shanghai",
    start_at: "2026-10-13T10:00:00+08:00",
    end_at: "2026-10-14T18:00:00+08:00",
    budget: { amount_minor: 10000, currency: "CNY" },
  });
  const mocks = await mockR90Board(page, journey.id);
  await page.addInitScript(({ journeyId, token }) => {
    localStorage.setItem("citynexus.v8.journey_id", journeyId);
    sessionStorage.setItem("citynexus.traveler.bearer", token);
  }, { journeyId: journey.id, token: traveler.access_token });

  await page.goto("/v8/hub", { waitUntil: "domcontentloaded" });
  const panel = page.getByTestId("bootstrap-discovery");
  await expect(panel.getByTestId("bootstrap-shortlist")).toContainText("Saved 0 of 3");
  await panel.getByTestId("bootstrap-provider-consent").check();
  await panel.getByTestId("bootstrap-search").click();
  await expect(panel.getByTestId(`bootstrap-candidate-${mocks.candidateId}`)).toContainText("price UNKNOWN");
  await panel.getByTestId(`bootstrap-save-${mocks.candidateId}`).click();
  await expect(panel.getByTestId("bootstrap-shortlist")).toContainText("Saved 1 of 3");

  await page.reload({ waitUntil: "domcontentloaded" });
  await expect(page.getByTestId("bootstrap-shortlist")).toContainText("R90 Mobile Gallery");
  await expect(page.getByTestId(`bootstrap-shortlist-item-${mocks.shortlistId}`)).toContainText("route ETA UNKNOWN");
  await page.getByTestId(`bootstrap-shortlist-map-${mocks.shortlistId}`).click();
  await expect(page.getByTestId(`bootstrap-shortlist-map-consent-${mocks.shortlistId}`)).toContainText("Fresh");
  await expect(page.getByTestId("bootstrap-shortlist-map-confirm")).toBeDisabled();
  expect(mocks.getPreviewCalls()).toBe(0);

  await page.getByTestId("bootstrap-shortlist-map-consent-checkbox").check();
  const popupPromise = page.waitForEvent("popup");
  await page.getByTestId("bootstrap-shortlist-map-confirm").click();
  const popup = await popupPromise;
  await popup.waitForURL(/openstreetmap\.org\/\?mlat=39\.1205000/);
  expect(popup.url()).toContain("mlon=117.2005000");
  expect(popup.url()).not.toContain("receipt");
  await expect(page.getByTestId("bootstrap-explore-state")).toContainText("no Place, PlanVersion");
  expect(mocks.getPreviewCalls()).toBe(1);

  await page.getByTestId(`bootstrap-shortlist-remove-${mocks.shortlistId}`).click();
  await expect(page.getByTestId("bootstrap-shortlist")).toContainText("Saved 0 of 3");
});
