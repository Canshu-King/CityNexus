import { expect, test, type APIRequestContext } from "@playwright/test";

const API = `http://127.0.0.1:${Number(process.env.CITYNEXUS_BACKEND_PORT ?? 8000)}`;

async function post<T>(request: APIRequestContext, path: string, data: unknown): Promise<T> {
  const response = await request.post(`${API}${path}`, { data });
  if (!response.ok()) throw new Error(`${path} -> ${response.status()}: ${(await response.text()).slice(0, 240)}`);
  return response.json() as Promise<T>;
}

async function createEmptyJourney(request: APIRequestContext, suffix: string) {
  const traveler = await post<{ id: string; access_token: string }>(request, "/api/v1/travelers", {
    display_name: `R85 browser ${suffix}`,
    locale: "en-GB",
    timezone: "Asia/Shanghai",
  });
  const journey = await post<{ id: string; city_code: string }>(request, "/api/v1/journeys", {
    traveler_id: traveler.id,
    title: `R85 browser ${suffix}`,
    city_code: `CN-R85-BROWSER-${suffix}`,
    timezone: "Asia/Shanghai",
    start_at: "2026-10-11T10:00:00+08:00",
    end_at: "2026-10-12T18:00:00+08:00",
    budget: { amount_minor: 10000, currency: "CNY" },
  });
  return { ...traveler, ...journey };
}

test("R85 shows a private, consented zero-catalog bootstrap and makes one bounded search", async ({ page, request }) => {
  const first = await createEmptyJourney(request, `${Date.now()}-cancel`);
  await page.addInitScript(({ journeyId, token }) => {
    localStorage.setItem("citynexus.v8.journey_id", journeyId);
    sessionStorage.setItem("citynexus.traveler.bearer", token);
  }, { journeyId: first.id, token: first.access_token });
  await page.goto("/v8/hub", { waitUntil: "domcontentloaded" });
  const panel = page.getByTestId("bootstrap-discovery");
  await expect(panel).toBeVisible();
  await expect(panel.getByTestId("bootstrap-provider-consent")).not.toBeChecked();
  await panel.getByTestId("bootstrap-cancel").click();
  await expect(panel).toBeHidden();

  const second = await createEmptyJourney(request, `${Date.now()}-search`);
  const searchPage = await page.context().newPage();
  await searchPage.addInitScript(({ journeyId, token }) => {
    localStorage.setItem("citynexus.v8.journey_id", journeyId);
    sessionStorage.setItem("citynexus.traveler.bearer", token);
  }, { journeyId: second.id, token: second.access_token });
  let searchCalls = 0;
  let selectCalls = 0;
  const candidateId = "00000000-0000-4000-8000-000000000085";
  await searchPage.route(`**/api/v1/journeys/${second.id}/bootstrap-discovery`, async (route) => {
    searchCalls += 1;
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        journey_id: second.id,
        status: "LIVE_RESULTS",
        receipt_id: "00000000-0000-4000-8000-000000000086",
        expires_at: "2026-10-10T00:00:00+00:00",
        source_kind: "MANUAL_PUBLIC_CENTER",
        provider: "overpass",
        provider_provenance: "LIVE_OPENSTREETMAP_OVERPASS",
        attempts: [{ endpoint: "https://overpass.test/api/interpreter", answered: true, http_status: 200 }],
        candidates: [{
          candidate_id: candidateId,
          name: "R85 Browser Public Cafe",
          category: "cafe",
          external_id: "overpass:node/85001",
          osm_type: "node",
          osm_id: "85001",
          source_url: "https://www.openstreetmap.org/node/85001",
          latitude: 39.12,
          longitude: 117.2,
          coordinate_system: "WGS84",
          distance_m: 120,
          opening_state: "UNKNOWN",
          availability_confidence: "UNVERIFIED",
          price_state: "UNKNOWN",
          eta_state: "UNKNOWN",
          tags: ["cafe", "real_city"],
        }],
      }),
    });
  });
  await searchPage.route(`**/api/v1/journeys/${second.id}/bootstrap-discovery/select`, async (route) => {
    selectCalls += 1;
    const body = route.request().postDataJSON() as { receipt_id: string; candidate_id: string };
    expect(body.candidate_id).toBe(candidateId);
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        journey_id: second.id,
        selected_place_id: "real-place-r85-browser",
        plan_version_id: null,
        journey_status: "DRAFT",
        provider_provenance: "LIVE_OPENSTREETMAP_OVERPASS",
      }),
    });
  });
  await searchPage.goto("/v8/hub", { waitUntil: "domcontentloaded" });
  const secondPanel = searchPage.getByTestId("bootstrap-discovery");
  await expect(secondPanel).toBeVisible();
  await secondPanel.getByTestId("bootstrap-search").click();
  await expect(secondPanel).toContainText("Confirm the OpenStreetMap/Overpass provider disclosure");
  expect(searchCalls).toBe(0);
  await secondPanel.getByTestId("bootstrap-provider-consent").check();
  await secondPanel.getByTestId("bootstrap-search").click();
  await expect(secondPanel.getByTestId("bootstrap-results")).toContainText("R85 Browser Public Cafe");
  expect(searchCalls).toBe(1);
  await secondPanel.getByTestId(`bootstrap-select-${candidateId}`).click();
  expect(selectCalls).toBe(1);
  await searchPage.close();
});
