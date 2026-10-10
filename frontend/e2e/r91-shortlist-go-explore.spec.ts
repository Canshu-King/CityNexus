import { expect, test, type APIRequestContext } from "@playwright/test";

const API = `http://127.0.0.1:${Number(process.env.CITYNEXUS_BACKEND_PORT ?? 8000)}`;

test.use({ viewport: { width: 390, height: 844 } });

async function post<T>(request: APIRequestContext, path: string, data: unknown): Promise<T> {
  const response = await request.post(`${API}${path}`, { data });
  if (!response.ok()) throw new Error(`${path} -> ${response.status()}: ${(await response.text()).slice(0, 240)}`);
  return response.json() as Promise<T>;
}

test("R91 lets a saved public place launch destination-only walking directions and return to the board", async ({ page, request }) => {
  const traveler = await post<{ id: string; access_token: string }>(request, "/api/v1/travelers", {
    display_name: `R91 mobile ${Date.now()}`,
    locale: "en-GB",
    timezone: "Asia/Shanghai",
  });
  const journey = await post<{ id: string }>(request, "/api/v1/journeys", {
    traveler_id: traveler.id,
    title: "R91 go explore",
    city_code: `CN-R91-BROWSER-${Date.now()}`,
    timezone: "Asia/Shanghai",
    start_at: "2026-10-13T10:00:00+08:00",
    end_at: "2026-10-14T18:00:00+08:00",
    budget: { amount_minor: 10000, currency: "CNY" },
  });
  const candidateId = "00000000-0000-4000-8000-000000000911";
  const shortlistId = "00000000-0000-4000-8000-000000000912";
  const receiptId = "00000000-0000-4000-8000-000000000913";
  const coords = { latitude: 39.1205, longitude: 117.2005 };
  const item = {
    shortlist_id: shortlistId,
    journey_id: journey.id,
    provider_key: "overpass",
    external_id: "overpass:node/91001",
    name: "R91 Walkable Gallery",
    category: "gallery",
    ...coords,
    coordinate_system: "WGS84",
    source_url: "https://www.openstreetmap.org/node/91001",
    source_provenance: "LIVE_OPENSTREETMAP_OVERPASS",
    captured_at: "2026-10-10T10:00:00+00:00",
    opening_hours: { status: "UNKNOWN" },
    opening_state: "UNKNOWN",
    price_state: "UNKNOWN",
    eta_state: "UNKNOWN",
    source_tags: {},
    distance_m: null,
    distance_basis: null,
    status: "SAVED",
    created_at: "2026-10-10T10:00:00+00:00",
    updated_at: "2026-10-10T10:00:00+00:00",
  };
  let saved = false;
  let navigationCalls = 0;
  await page.route(`**/api/v1/journeys/${journey.id}/bootstrap-shortlist`, async (route) => {
    if (route.request().method() === "GET") {
      await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ journey_id: journey.id, limit: 3, items: saved ? [item] : [] }) });
      return;
    }
    expect(route.request().postDataJSON()).toEqual({ receipt_id: receiptId, candidate_id: candidateId });
    saved = true;
    await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(item) });
  });
  await page.route(`**/api/v1/journeys/${journey.id}/bootstrap-discovery`, async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        journey_id: journey.id,
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
          osm_id: "91001",
          source_url: item.source_url,
          ...coords,
          coordinate_system: "WGS84",
          distance_m: 80,
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
  await page.route(`**/api/v1/journeys/${journey.id}/bootstrap-shortlist/${shortlistId}/navigate`, async (route) => {
    navigationCalls += 1;
    expect(route.request().postDataJSON()).toEqual({ public_map_consent: true });
    const body = JSON.stringify({
      preview_id: "00000000-0000-4000-8000-000000000914",
      status: "PUBLIC_DESTINATION_READY",
      journey_id: journey.id,
      shortlist_id: shortlistId,
      authorization_basis: "SAVED_PUBLIC_IDENTITY",
      release_purpose: "WALKING",
      navigation_mode: "WALKING_DIRECTIONS",
      navigation_url: "https://www.google.com/maps/dir/?api=1&destination=39.1205000%2C117.2005000&travelmode=walking",
      destination: {
        name: item.name,
        external_id: item.external_id,
        source_url: item.source_url,
        ...coords,
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
    });
    await route.fulfill({ status: 200, contentType: "application/json", body });
  });
  await page.route("https://www.google.com/maps/**", async (route) => {
    await route.fulfill({ status: 200, contentType: "text/html", body: "walking destination" });
  });

  await page.addInitScript(({ journeyId, token }) => {
    localStorage.setItem("citynexus.v8.journey_id", journeyId);
    sessionStorage.setItem("citynexus.traveler.bearer", token);
  }, { journeyId: journey.id, token: traveler.access_token });
  await page.goto("/v8/hub", { waitUntil: "domcontentloaded" });
  const panel = page.getByTestId("bootstrap-discovery");
  await panel.getByTestId("bootstrap-provider-consent").check();
  await panel.getByTestId("bootstrap-search").click();
  await panel.getByTestId(`bootstrap-save-${candidateId}`).click();
  await expect(panel.getByTestId("bootstrap-shortlist")).toContainText("Saved 1 of 3");

  await panel.getByTestId(`bootstrap-shortlist-go-${shortlistId}`).click();
  await expect(panel.getByTestId(`bootstrap-shortlist-navigation-consent-${shortlistId}`)).toContainText("Opening, cost, route duration, and arrival remain unknown");
  await expect(panel.getByTestId("bootstrap-shortlist-navigation-confirm")).toBeDisabled();
  expect(navigationCalls).toBe(0);
  await panel.getByTestId("bootstrap-shortlist-navigation-consent-checkbox").check();
  const popupPromise = page.waitForEvent("popup");
  await panel.getByTestId("bootstrap-shortlist-navigation-confirm").click();
  const popup = await popupPromise;
  await popup.waitForURL(/google\.com\/maps\/dir/);
  expect(popup.url()).toContain("destination=39.1205000%2C117.2005000");
  expect(popup.url()).toContain("travelmode=walking");
  expect(popup.url()).not.toContain("origin");
  expect(popup.url()).not.toContain("receipt");
  await expect(panel.getByTestId("bootstrap-explore-state")).toContainText("no Place, PlanVersion, route ETA, arrival");
  expect(navigationCalls).toBe(1);
  await panel.getByTestId("bootstrap-back-to-board").click();
  await expect(panel.getByTestId("bootstrap-shortlist")).toContainText("R91 Walkable Gallery");
});
