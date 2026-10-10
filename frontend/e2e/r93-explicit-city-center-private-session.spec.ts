import { expect, test, type APIRequestContext, type Route } from "@playwright/test";

const API = `http://127.0.0.1:${Number(process.env.CITYNEXUS_BACKEND_PORT ?? 8000)}`;

test.use({ viewport: { width: 390, height: 844 } });

async function post<T>(request: APIRequestContext, path: string, data: unknown): Promise<T> {
  const response = await request.post(`${API}${path}`, { data });
  if (!response.ok()) throw new Error(`${path} -> ${response.status()}: ${(await response.text()).slice(0, 240)}`);
  return response.json() as Promise<T>;
}

async function createTraveler(request: APIRequestContext, displayName: string) {
  return post<{ id: string; access_token: string }>(request, "/api/v1/travelers", {
    display_name: displayName,
    locale: "en-GB",
    timezone: "Asia/Shanghai",
  });
}

function savedItem(journeyId: string, shortlistId: string, name: string, externalId: string) {
  return {
    shortlist_id: shortlistId,
    journey_id: journeyId,
    provider_key: "overpass",
    external_id: externalId,
    name,
    category: "gallery",
    latitude: 31.2304,
    longitude: 121.4737,
    coordinate_system: "WGS84",
    source_url: `https://www.openstreetmap.org/node/${shortlistId.slice(-4)}`,
    source_provenance: "LIVE_OPENSTREETMAP_OVERPASS",
    captured_at: "2026-10-10T10:00:00+00:00",
    opening_hours: { status: "UNKNOWN" },
    opening_state: "UNKNOWN",
    price_state: "UNKNOWN",
    eta_state: "UNKNOWN",
    source_tags: {},
    distance_m: 120,
    distance_basis: "MANUAL_PUBLIC_CENTER",
    status: "SAVED",
    created_at: "2026-10-10T10:00:00+00:00",
    updated_at: "2026-10-10T10:00:00+00:00",
  };
}

test("R93 requires an explicit center and drops delayed A state after same-tab bearer switch", async ({ page, request }) => {
  const travelerA = await createTraveler(request, `R93 A ${Date.now()}`);
  const travelerB = await createTraveler(request, `R93 B ${Date.now()}`);
  const journey = await post<{ id: string; city_code: string }>(request, "/api/v1/journeys", {
    traveler_id: travelerA.id,
    title: "R93 explicit center isolation",
    city_code: `CN-R93-SH-${Date.now()}`,
    timezone: "Asia/Shanghai",
    start_at: "2026-10-15T10:00:00+08:00",
    end_at: "2026-10-16T18:00:00+08:00",
    budget: { amount_minor: 10000, currency: "CNY" },
  });
  const candidateId = "00000000-0000-4000-8000-000000000931";
  const receiptId = "00000000-0000-4000-8000-000000000932";
  const aShortlistId = "00000000-0000-4000-8000-000000000933";
  const bShortlistId = "00000000-0000-4000-8000-000000000934";
  const aItem = savedItem(journey.id, aShortlistId, "A Secret Shanghai Gallery", "overpass:node/93001");
  const bItem = savedItem(journey.id, bShortlistId, "B Own Shanghai Gallery", "overpass:node/93002");
  const aResume = {
    shortlist_id: aShortlistId,
    journey_id: journey.id,
    name: aItem.name,
    category: aItem.category,
    latitude: aItem.latitude,
    longitude: aItem.longitude,
    coordinate_system: "WGS84",
    source_url: aItem.source_url,
    source_provenance: aItem.source_provenance,
    captured_at: aItem.captured_at,
    selected_at: "2026-10-10T10:05:00+00:00",
    status: "CHOSEN",
  };
  let aHasSaved = false;
  let releaseDelayedSave: (() => void) | undefined;
  let delayedSaveStarted: Promise<void> | undefined;
  let resolveDelayedSaveStarted: (() => void) | undefined;
  delayedSaveStarted = new Promise<void>((resolve) => { resolveDelayedSaveStarted = resolve; });

  await page.route(`**/api/v1/journeys/${journey.id}/bootstrap-shortlist`, async (route: Route) => {
    const authorization = route.request().headers().authorization ?? "";
    if (route.request().method() === "GET") {
      const body = authorization === `Bearer ${travelerA.access_token}`
        ? { journey_id: journey.id, limit: 3, items: aHasSaved ? [aItem] : [], resume: aHasSaved ? aResume : null }
        : { journey_id: journey.id, limit: 3, items: [bItem], resume: null };
      await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(body) });
      return;
    }
    expect(authorization).toBe(`Bearer ${travelerA.access_token}`);
    expect(route.request().postDataJSON()).toEqual({ receipt_id: receiptId, candidate_id: candidateId });
    resolveDelayedSaveStarted?.();
    await new Promise<void>((resolve) => { releaseDelayedSave = resolve; });
    aHasSaved = true;
    await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(aItem) });
  });

  await page.route(`**/api/v1/journeys/${journey.id}/bootstrap-discovery`, async (route: Route) => {
    expect(route.request().method()).toBe("POST");
    const body = route.request().postDataJSON() as Record<string, unknown>;
    expect(body.source_kind).toBe("MANUAL_PUBLIC_CENTER");
    expect(body.provider_consent).toBe(true);
    expect(body.latitude).toBe(31.2304);
    expect(body.longitude).toBe(121.4737);
    expect(body.coordinate_system).toBe("WGS84");
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        journey_id: journey.id,
        status: "LIVE_RESULTS",
        receipt_id: receiptId,
        expires_at: "2026-10-16T00:00:00+00:00",
        source_kind: "MANUAL_PUBLIC_CENTER",
        provider: "TEST_PROVIDER",
        provider_provenance: "TEST_PROVIDER",
        attempts: [{ endpoint: "TEST_PROVIDER", answered: true, http_status: 200 }],
        candidates: [{
          candidate_id: candidateId,
          name: "A Secret Shanghai Gallery",
          category: "gallery",
          external_id: "overpass:node/93001",
          osm_type: "node",
          osm_id: "93001",
          source_url: "https://www.openstreetmap.org/node/93001",
          latitude: 31.2304,
          longitude: 121.4737,
          coordinate_system: "WGS84",
          distance_m: 120,
          opening_state: "UNKNOWN",
          selection_state: "OPENING_UNVERIFIED",
          selection_action: "VERIFY_OPENING_SOURCE_OR_CHOOSE_ANOTHER_CANDIDATE",
          availability_confidence: "UNVERIFIED",
          price_state: "UNKNOWN",
          eta_state: "UNKNOWN",
          tags: ["gallery"],
          opening_hours: { status: "UNKNOWN" },
          opening_observed_at: "2026-10-10T10:00:00+00:00",
          opening_source: "TEST_PROVIDER",
          opening_claim: "NO_OPENING_TAG",
          opening_verification_state: "EXTERNAL_NOT_ATTESTED",
          opening_verification_action: "OPEN_SOURCE_PAGE",
          source_tags: {},
        }],
      }),
    });
  });

  await page.addInitScript(({ journeyId, token }) => {
    localStorage.setItem("citynexus.v8.journey_id", journeyId);
    sessionStorage.setItem("citynexus.traveler.bearer", token);
  }, { journeyId: journey.id, token: travelerA.access_token });
  await page.goto("/v8/hub", { waitUntil: "domcontentloaded" });
  const panel = page.getByTestId("bootstrap-discovery");
  await expect(panel.getByTestId("bootstrap-center-required")).toContainText("No provider request will be made yet");
  await expect(panel.getByTestId("bootstrap-search")).toBeDisabled();
  await expect(panel.getByTestId("bootstrap-latitude")).toHaveValue("");
  await expect(panel.getByTestId("bootstrap-longitude")).toHaveValue("");

  await panel.getByTestId("bootstrap-latitude").fill("31.2304");
  await panel.getByTestId("bootstrap-longitude").fill("121.4737");
  await expect(panel.getByTestId("bootstrap-selected-center")).toContainText("31.230400, 121.473700");
  await panel.getByTestId("bootstrap-provider-consent").check();
  await panel.getByTestId("bootstrap-search").click();
  await expect(panel.getByTestId(`bootstrap-candidate-${candidateId}`)).toContainText("A Secret Shanghai Gallery");

  await panel.getByTestId(`bootstrap-save-${candidateId}`).click();
  await delayedSaveStarted;

  // Direct same-tab sessionStorage writes do not emit the browser storage event.
  // R93's polling/signal boundary must still clear A synchronously for the new bearer.
  await page.evaluate((token) => {
    sessionStorage.setItem("citynexus.traveler.bearer", token);
  }, travelerB.access_token);
  await expect(panel.getByTestId("bootstrap-center-required")).toBeVisible();
  await expect(panel.getByTestId("bootstrap-provider-consent")).not.toBeChecked();
  await expect(panel.getByTestId("bootstrap-results")).toHaveCount(0);
  await expect(panel).not.toContainText("A Secret Shanghai Gallery");
  await expect(panel.getByTestId("bootstrap-shortlist")).toContainText("B Own Shanghai Gallery");

  // The old A POST resolves after the switch. Its response must be ignored.
  releaseDelayedSave?.();
  await expect(panel).not.toContainText("A Secret Shanghai Gallery");

  // A can return later and recover only A's own signed board.
  await page.evaluate((token) => {
    sessionStorage.setItem("citynexus.traveler.bearer", token);
  }, travelerA.access_token);
  await expect(panel.getByTestId("bootstrap-resume")).toContainText("A Secret Shanghai Gallery");
  await expect(panel.getByTestId("bootstrap-shortlist")).toContainText("A Secret Shanghai Gallery");
});
