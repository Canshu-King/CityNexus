import { expect, test, type APIRequestContext } from "@playwright/test";

const API = `http://127.0.0.1:${Number(process.env.CITYNEXUS_BACKEND_PORT ?? 8000)}`;

test.use({ viewport: { width: 390, height: 844 } });

async function post<T>(request: APIRequestContext, path: string, data: unknown): Promise<T> {
  const response = await request.post(`${API}${path}`, { data });
  if (!response.ok()) throw new Error(`${path} -> ${response.status()}: ${(await response.text()).slice(0, 240)}`);
  return response.json() as Promise<T>;
}

test("R92 restores a private outing choice after mobile return and fails closed after removal", async ({ page, request }) => {
  const traveler = await post<{ id: string; access_token: string }>(request, "/api/v1/travelers", {
    display_name: `R92 mobile ${Date.now()}`,
    locale: "en-GB",
    timezone: "Asia/Shanghai",
  });
  const journey = await post<{ id: string }>(request, "/api/v1/journeys", {
    traveler_id: traveler.id,
    title: "R92 private outing resume",
    city_code: `CN-R92-BROWSER-${Date.now()}`,
    timezone: "Asia/Shanghai",
    start_at: "2026-10-13T10:00:00+08:00",
    end_at: "2026-10-14T18:00:00+08:00",
    budget: { amount_minor: 10000, currency: "CNY" },
  });
  const candidateId = "00000000-0000-4000-8000-000000000921";
  const shortlistId = "00000000-0000-4000-8000-000000000922";
  const receiptId = "00000000-0000-4000-8000-000000000923";
  const coords = { latitude: 39.1215, longitude: 117.2015 };
  const item = {
    shortlist_id: shortlistId,
    journey_id: journey.id,
    provider_key: "overpass",
    external_id: "overpass:node/92001",
    name: "R92 Resume Gallery",
    category: "gallery",
    ...coords,
    coordinate_system: "WGS84",
    source_url: "https://www.openstreetmap.org/node/92001",
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
  let resumeIntent: Record<string, unknown> | null = null;
  let navigationCalls = 0;
  await page.route(`**/api/v1/journeys/${journey.id}/bootstrap-shortlist`, async (route) => {
    if (route.request().method() === "GET") {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ journey_id: journey.id, limit: 3, items: saved ? [item] : [], resume: resumeIntent }),
      });
      return;
    }
    expect(route.request().postDataJSON()).toEqual({ receipt_id: receiptId, candidate_id: candidateId });
    saved = true;
    await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(item) });
  });
  await page.route(`**/api/v1/journeys/${journey.id}/bootstrap-shortlist/${shortlistId}/resume`, async (route) => {
    resumeIntent = {
      shortlist_id: shortlistId,
      journey_id: journey.id,
      name: item.name,
      category: item.category,
      ...coords,
      coordinate_system: "WGS84",
      source_url: item.source_url,
      source_provenance: item.source_provenance,
      captured_at: item.captured_at,
      selected_at: "2026-10-10T10:05:00+00:00",
      status: "CHOSEN",
    };
    await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(resumeIntent) });
  });
  await page.route(`**/api/v1/journeys/${journey.id}/bootstrap-shortlist/${shortlistId}`, async (route) => {
    expect(route.request().method()).toBe("DELETE");
    saved = false;
    resumeIntent = null;
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ journey_id: journey.id, shortlist_id: shortlistId, removed: true, place_id: null }),
    });
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
        provider: "TEST_PROVIDER",
        provider_provenance: "TEST_PROVIDER",
        attempts: [{ endpoint: "TEST_PROVIDER", answered: true, http_status: 200 }],
        candidates: [{
          candidate_id: candidateId,
          name: item.name,
          category: item.category,
          external_id: item.external_id,
          osm_type: "node",
          osm_id: "92001",
          source_url: item.source_url,
          ...coords,
          coordinate_system: "WGS84",
          distance_m: 90,
          opening_state: "UNKNOWN",
          selection_state: "OPENING_UNVERIFIED",
          selection_action: "VERIFY_OPENING_SOURCE_OR_CHOOSE_ANOTHER_CANDIDATE",
          availability_confidence: "UNVERIFIED",
          price_state: "UNKNOWN",
          eta_state: "UNKNOWN",
          tags: ["gallery"],
          opening_hours: { status: "UNKNOWN" },
          opening_observed_at: item.captured_at,
          opening_source: "TEST_PROVIDER",
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
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        preview_id: `00000000-0000-4000-8000-00000000092${navigationCalls + 3}`,
        status: "PUBLIC_DESTINATION_READY",
        journey_id: journey.id,
        shortlist_id: shortlistId,
        authorization_basis: "SAVED_PUBLIC_IDENTITY",
        release_purpose: "WALKING",
        navigation_mode: "WALKING_DIRECTIONS",
        navigation_url: "https://www.google.com/maps/dir/?api=1&destination=39.1215000%2C117.2015000&travelmode=walking",
        destination: {
          name: item.name,
          external_id: item.external_id,
          source_url: item.source_url,
          ...coords,
          coordinate_system: "WGS84",
          map_url: "https://www.openstreetmap.org/?mlat=39.1215000&mlon=117.2015000#map=18/39.1215000/117.2015000",
        },
        opening: {
          state: "UNKNOWN",
          raw: null,
          source_tags: {},
          source: "TEST_PROVIDER",
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
  await page.route("https://www.google.com/maps/**", async (route) => {
    await route.fulfill({ status: 200, contentType: "text/html", body: "walking destination" });
  });

  await page.addInitScript(({ journeyId, token }) => {
    localStorage.setItem("citynexus.v8.journey_id", journeyId);
    sessionStorage.setItem("citynexus.traveler.bearer", token);
  }, { journeyId: journey.id, token: traveler.access_token });
  await page.goto("/v8/hub", { waitUntil: "domcontentloaded" });
  let panel = page.getByTestId("bootstrap-discovery");
  await panel.getByTestId("bootstrap-provider-consent").check();
  await panel.getByTestId("bootstrap-search").click();
  await panel.getByTestId(`bootstrap-save-${candidateId}`).click();
  await expect(panel.getByTestId("bootstrap-shortlist")).toContainText("Saved 1 of 3");

  await panel.getByTestId(`bootstrap-shortlist-go-${shortlistId}`).click();
  await expect(panel.getByTestId(`bootstrap-shortlist-navigation-consent-${shortlistId}`)).toContainText("Opening, cost, route duration, and arrival remain unknown");
  await panel.getByTestId("bootstrap-shortlist-navigation-consent-checkbox").check();
  const firstPopupPromise = page.waitForEvent("popup");
  await panel.getByTestId("bootstrap-shortlist-navigation-confirm").click();
  const firstPopup = await firstPopupPromise;
  await firstPopup.waitForURL(/google\.com\/maps\/dir/);
  expect(firstPopup.url()).toContain("destination=39.1215000%2C117.2015000");
  expect(firstPopup.url()).not.toContain("origin");
  await firstPopup.close();

  await page.reload({ waitUntil: "domcontentloaded" });
  panel = page.getByTestId("bootstrap-discovery");
  await expect(panel.getByTestId("bootstrap-resume")).toContainText("R92 Resume Gallery");
  await expect(panel.getByTestId("bootstrap-resume")).toContainText("physical arrival remains unverified");
  await expect(panel.getByTestId("bootstrap-resume-source")).toHaveAttribute("href", item.source_url);
  await panel.getByTestId("bootstrap-resume-walking").click();
  await panel.getByTestId("bootstrap-shortlist-navigation-consent-checkbox").check();
  const secondPopupPromise = page.waitForEvent("popup");
  await panel.getByTestId("bootstrap-shortlist-navigation-confirm").click();
  const secondPopup = await secondPopupPromise;
  await secondPopup.waitForURL(/google\.com\/maps\/dir/);
  expect(secondPopup.url()).toContain("travelmode=walking");
  expect(navigationCalls).toBe(2);
  await secondPopup.close();

  await panel.getByTestId(`bootstrap-shortlist-remove-${shortlistId}`).click();
  await expect(panel.getByTestId("bootstrap-resume")).toHaveCount(0);
  await expect(panel.getByTestId(`bootstrap-shortlist-item-${shortlistId}`)).toHaveCount(0);
});
