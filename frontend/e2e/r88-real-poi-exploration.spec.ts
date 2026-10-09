import { expect, test, type APIRequestContext } from "@playwright/test";

const API = `http://127.0.0.1:${Number(process.env.CITYNEXUS_BACKEND_PORT ?? 8000)}`;

async function post<T>(request: APIRequestContext, path: string, data: unknown): Promise<T> {
  const response = await request.post(`${API}${path}`, { data });
  if (!response.ok()) throw new Error(`${path} -> ${response.status()}: ${(await response.text()).slice(0, 240)}`);
  return response.json() as Promise<T>;
}

test("R88 lets a signed traveller explore an unknown-opening real POI without starting a Journey", async ({ page, request }) => {
  const traveler = await post<{ id: string; access_token: string }>(request, "/api/v1/travelers", {
    display_name: `R88 browser ${Date.now()}`,
    locale: "en-GB",
    timezone: "Asia/Shanghai",
  });
  const journey = await post<{ id: string }>(request, "/api/v1/journeys", {
    traveler_id: traveler.id,
    title: "R88 browser public POI exploration",
    city_code: `CN-R88-BROWSER-${Date.now()}`,
    timezone: "Asia/Shanghai",
    start_at: "2026-10-13T10:00:00+08:00",
    end_at: "2026-10-14T18:00:00+08:00",
    budget: { amount_minor: 10000, currency: "CNY" },
  });
  const candidateId = "00000000-0000-4000-8000-000000000881";
  const receiptId = "00000000-0000-4000-8000-000000000882";
  let previewCalls = 0;
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
        receipt_id: receiptId,
        expires_at: "2026-10-14T00:00:00+00:00",
        source_kind: "MANUAL_PUBLIC_CENTER",
        provider: "overpass",
        provider_provenance: "LIVE_OPENSTREETMAP_OVERPASS",
        attempts: [{ endpoint: "https://overpass-api.de/api/interpreter", answered: true, http_status: 200 }],
        candidates: [{
          candidate_id: candidateId,
          name: "R88 Gallery Without Opening Proof",
          category: "gallery",
          external_id: "overpass:node/88001",
          osm_type: "node",
          osm_id: "88001",
          source_url: "https://www.openstreetmap.org/node/88001",
          latitude: 39.1205,
          longitude: 117.2005,
          coordinate_system: "WGS84",
          distance_m: 80,
          opening_state: "UNKNOWN",
          selection_state: "OPENING_UNVERIFIED",
          selection_action: "VERIFY_OPENING_SOURCE_OR_CHOOSE_ANOTHER_CANDIDATE",
          availability_confidence: "UNVERIFIED",
          price_state: "UNKNOWN",
          eta_state: "UNKNOWN",
          tags: ["gallery", "real_city"],
          opening_hours: { status: "UNKNOWN", raw: "Mo-Fr 09:00-18:00" },
          opening_observed_at: "2026-10-10T10:00:00+00:00",
          opening_source: "OpenStreetMap/Overpass",
          opening_claim: "OSM_TAG_CLAIM",
          opening_verification_state: "EXTERNAL_NOT_ATTESTED",
          opening_verification_action: "OPEN_SOURCE_PAGE",
          source_tags: {
            opening_hours: "Mo-Fr 09:00-18:00",
            website: "https://gallery.example.test",
            "contact:phone": "+86 13800000000",
          },
        }],
      }),
    });
  });
  await page.route(`**/api/v1/journeys/${journey.id}/bootstrap-discovery/preview`, async (route) => {
    previewCalls += 1;
    const body = route.request().postDataJSON() as Record<string, unknown>;
    expect(body.public_map_consent).toBe(true);
    expect(body.candidate_id).toBe(candidateId);
    expect(body).not.toHaveProperty("origin");
    expect(body).not.toHaveProperty("query");
    expect(body).not.toHaveProperty("query_center");
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        preview_id: "00000000-0000-4000-8000-000000000883",
        status: "PUBLIC_DESTINATION_READY",
        journey_id: journey.id,
        receipt_id: receiptId,
        candidate_id: candidateId,
        expires_at: "2026-10-14T00:00:00+00:00",
        provider: "overpass",
        provider_provenance: "LIVE_OPENSTREETMAP_OVERPASS",
        destination: {
          name: "R88 Gallery Without Opening Proof",
          external_id: "overpass:node/88001",
          osm_type: "node",
          osm_id: "88001",
          latitude: 39.1205,
          longitude: 117.2005,
          coordinate_system: "WGS84",
          source_url: "https://www.openstreetmap.org/node/88001",
          map_url: "https://www.openstreetmap.org/?mlat=39.1205000&mlon=117.2005000#map=18/39.1205000/117.2005000",
        },
        opening: {
          state: "UNKNOWN",
          raw: "Mo-Fr 09:00-18:00",
          source_tags: { opening_hours: "Mo-Fr 09:00-18:00", website: "https://gallery.example.test" },
          source: "OpenStreetMap/Overpass",
          observed_at: "2026-10-10T10:00:00+00:00",
          claim: "OSM_TAG_CLAIM",
          verification_state: "EXTERNAL_NOT_ATTESTED",
          verification_action: "OPEN_SOURCE_PAGE",
        },
        explore_state: "DRAFT_EXPLORE_ONLY",
        shared_fields: ["public_destination", "osm_id", "source_url"],
        withheld_fields: ["origin", "foreground_gps", "query_center", "member_id", "traveler_id"],
        plan_version_id: null,
        selected_place_id: null,
      }),
    });
  });
  await page.route("https://www.openstreetmap.org/**", async (route) => {
    await route.fulfill({ status: 200, contentType: "text/html", body: "public map preview" });
  });

  await page.goto("/v8/hub", { waitUntil: "domcontentloaded" });
  const panel = page.getByTestId("bootstrap-discovery");
  await expect(panel).toBeVisible();
  await panel.getByTestId("bootstrap-provider-consent").check();
  await panel.getByTestId("bootstrap-search").click();
  await expect(panel.getByTestId("bootstrap-results")).toContainText("R88 Gallery Without Opening Proof");
  await expect(panel.getByTestId(`bootstrap-source-facts-${candidateId}`)).toContainText("OSM_TAG_CLAIM");
  await expect(panel.getByTestId(`bootstrap-source-facts-${candidateId}`)).toContainText("website");
  await expect(panel.getByTestId(`bootstrap-select-${candidateId}`)).toBeDisabled();

  await panel.getByTestId(`bootstrap-map-preview-${candidateId}`).click();
  await expect(panel.getByTestId(`bootstrap-map-consent-${candidateId}`)).toContainText("only this public destination");
  await expect(panel.getByTestId("bootstrap-map-preview-confirm")).toBeDisabled();
  await panel.getByTestId("bootstrap-map-preview-cancel").click();
  await expect(panel.getByTestId(`bootstrap-map-consent-${candidateId}`)).toHaveCount(0);
  expect(previewCalls).toBe(0);

  await panel.getByTestId(`bootstrap-map-preview-${candidateId}`).click();
  await panel.getByTestId("bootstrap-map-consent-checkbox").check();
  const popupPromise = page.waitForEvent("popup");
  await panel.getByTestId("bootstrap-map-preview-confirm").click();
  const popup = await popupPromise;
  await popup.waitForURL(/openstreetmap\.org\/\?mlat=39\.1205000/);
  expect(popup.url()).toContain("openstreetmap.org/?mlat=39.1205000&mlon=117.2005000");
  expect(popup.url()).not.toContain("origin");
  expect(popup.url()).not.toContain("center");
  await expect(panel.getByTestId("bootstrap-explore-state")).toContainText("EXTERNAL_NOT_ATTESTED");
  await expect(panel.getByTestId("bootstrap-explore-state")).toContainText("no Place, PlanVersion");
  expect(previewCalls).toBe(1);
});
