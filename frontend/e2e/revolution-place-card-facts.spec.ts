import { expect, test, type Route } from "@playwright/test";

test.use({ viewport: { width: 390, height: 844 }, hasTouch: true });

const journey = "00000000-0000-4000-8000-000000000223";
const root = `**/api/v1/journeys/${journey}`;

function json(route: Route, object: object | null) {
  return route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(object) });
}

function candidate(
  candidateId: string,
  osmId: string,
  providerProvenance: "LIVE_PROVIDER" | "TEST_PROVIDER" | "UNVERIFIED",
  facts: {
    openingHours?: Record<string, unknown>;
    costEvidence?: Record<string, unknown>;
  } = {},
) {
  return {
    candidate_id: candidateId,
    provider_key: "overpass",
    name: `地点 ${candidateId}`,
    category: "park",
    external_id: osmId,
    osm_type: "node",
    osm_id: osmId,
    source_url: `https://www.openstreetmap.org/node/${osmId}`,
    latitude: 25.7,
    longitude: 116.75,
    coordinate_system: "WGS84",
    distance_m: 450,
    opening_state: facts.openingHours?.status ?? "UNKNOWN",
    selection_state: facts.openingHours?.status === "NORMALIZED_VALID" ? "READY_FOR_NATIVE_PLAN" : "OPENING_UNVERIFIED",
    selection_action: null,
    availability_confidence: "UNVERIFIED",
    price_state: "UNKNOWN",
    eta_state: "UNKNOWN",
    tags: ["park", "fee=no"],
    ...(facts.openingHours ? { opening_hours: facts.openingHours } : {}),
    ...(facts.costEvidence ? { cost_evidence: facts.costEvidence } : {}),
    opening_observed_at: "2026-10-17T00:00:00Z",
    opening_source: "OpenStreetMap/Overpass",
    opening_claim: facts.openingHours?.status === "NORMALIZED_VALID" ? "OSM_TAG_CLAIM" : "NO_OPENING_TAG",
    opening_verification_state: facts.openingHours?.status === "NORMALIZED_VALID" ? "PROVIDER_GROUNDED" : "EXTERNAL_NOT_ATTESTED",
    opening_verification_action: "OPEN_SOURCE_PAGE",
    source_tags: { opening_hours: "Mo-Fr 09:00-18:00", fee: "no" },
    source_attribution: "© OpenStreetMap contributors",
    source_attribution_url: "https://www.openstreetmap.org/copyright",
    public_access_state: "PUBLIC_ACCESS_UNVERIFIED",
    provider_provenance: providerProvenance,
  };
}

test("place cards show grounded hours and costs while preserving provenance and OSM links", async ({ page }) => {
  let detailRequests = 0;
  let discoveryRequests = 0;
  let enriched: (ReturnType<typeof candidate> & { facts_status: string }) | null = null;
  await page.addInitScript((id) => {
    window.sessionStorage.setItem("citynexus.traveler.bearer", "signed-only-fixture-token");
    window.localStorage.setItem("citynexus.revolution.firstlook.journey", JSON.stringify({
      id, cityCode: "CN-RV-TEST", cityName: "连城", status: "DRAFT",
    }));
  }, journey);

  await page.route("**/api/v1/**", (route) => route.fulfill({
    status: 404,
    contentType: "application/json",
    body: JSON.stringify({ detail: "TEST_FIXTURE_ENDPOINT_NOT_SEEDED" }),
  }));
  await page.route("**/api/v1/travelers/session", (route) => json(route, {
    traveler_id: "fixture-traveler-223",
  }));
  await page.route("**/api/v1/agent/runtime-status", (route) => json(route, {
    runtime_identity: "UNCONFIGURED", hermes_compat_configured: false,
  }));
  await page.route(`${root}/bootstrap-discovery/readiness`, (route) => json(route, {
    status: "READY", reason_code: "READY", provider: "overpass", provider_name: "Playwright fixture",
    expected_recipient: "TEST_PROVIDER", capability_state: "TEST_CAPABLE", provider_grade: "TEST_PROVIDER",
    external_request_allowed: true, test_only: true,
  }));
  await page.route(`${root}/bootstrap-shortlist`, (route) => json(route, {
    journey_id: journey, limit: 3, items: [], resume: null, pocket_walk: null,
  }));
  await page.route(`${root}/bootstrap-city-search`, (route) => json(route, {
    journey_id: journey, status: "CITY_RESULTS", query: "连城", provider_attempts: [],
    results: [{
      result_id: "city-facts-fixture", name: "连城县", display_name: "连城县（测试地名结果）",
      provider: "test", provider_provenance: "TEST_PROVIDER", latitude: 25.7, longitude: 116.75,
      coordinate_system: "WGS84", confidence: "CITY_CENTROID_UNCERTAIN", selection_state: "CAMERA_ONLY_TAP_REQUIRED",
    }],
  }));
  await page.route(`${root}/bootstrap-discovery`, (route) => {
    discoveryRequests += 1;
    return json(route, {
    journey_id: journey, status: "LIVE_RESULTS", source_kind: "MANUAL_PUBLIC_CENTER",
    provider: "overpass", provider_provenance: "LIVE_PROVIDER", receipt_id: "receipt-place-facts",
    expires_at: "2026-10-17T01:00:00Z", attempts: [{ http_status: 200 }],
    candidates: [
      candidate("live-free", "123", "LIVE_PROVIDER", {
        openingHours: {
          status: "NORMALIZED_VALID",
          raw: "Mo-Fr 09:00-18:00",
          open: "09:00",
          close: "18:00",
          intervals: [{ days: ["Mo", "Tu", "We", "Th", "Fr"], open: "09:00", close: "18:00" }],
          weekday_intervals: [{ days: ["Mo", "Tu", "We", "Th", "Fr"], intervals: [{ open: "09:00", close: "18:00" }] }],
        },
        costEvidence: { status: "KNOWN", amount_minor: 0, currency: null, evidence_basis: "OSM_FEE_NO" },
      }),
      candidate("test-priced", "124", "TEST_PROVIDER", {
        costEvidence: { status: "VERIFIED_PROVIDER", amount_minor: 1200, currency: "CNY" },
      }),
      {
        ...candidate("unknown-facts", "125", "UNVERIFIED", {
          costEvidence: { status: "UNKNOWN", amount_minor: 0, currency: "CNY" },
        }),
        distance_m: null,
      },
      candidate("live-needs-details", "126", "LIVE_PROVIDER"),
    ],
    });
  });
  await page.route(`${root}/bootstrap-discovery/current`, (route) => json(route, enriched ? {
    journey_id: journey, status: "LIVE_RESULTS", receipt_id: "receipt-place-facts",
    source_kind: "MANUAL_PUBLIC_CENTER", provider: "overpass", provider_provenance: "LIVE_PROVIDER",
    attempts: [], candidates: [enriched],
  } : null));
  await page.route(`${root}/bootstrap-discovery/facts`, (route) => {
    detailRequests += 1;
    expect(route.request().headers().authorization).toBe("Bearer signed-only-fixture-token");
    expect(route.request().postDataJSON()).toEqual({
      receipt_id: "receipt-place-facts", candidate_id: "live-needs-details", provider_consent: true,
    });
    enriched = {
      ...candidate("live-needs-details", "126", "LIVE_PROVIDER", {
        openingHours: { status: "NORMALIZED_VALID", open: "00:00", close: "24:00" },
        costEvidence: { status: "KNOWN", amount_minor: 0, evidence_basis: "OSM_FEE_NO" },
      }), facts_status: "SUCCESS", opening_source: "OpenStreetMap element API",
    };
    return json(route, { journey_id: journey, cached: false, candidate: enriched });
  });

  await page.goto("/revolution");
  await page.getByTestId("rev-quick-find-city").click();
  await expect(page.getByTestId("rev-quick-city-results")).toBeVisible();
  await page.getByRole("button", { name: /连城县.*2.5公里/ }).click();
  await page.getByTestId("rev-quick-use-approx-center").click();
  await page.getByTestId("rev-quick-find-places").click();

  const cards = page.getByTestId("rev-quick-place-card");
  await expect(cards).toHaveCount(4);
  await expect(cards.nth(0)).toContainText("营业时间：周一至周五 09:00–18:00 · 免费");
  await expect(cards.nth(0)).toContainText("公开地图来源");
  await expect(cards.nth(1)).toContainText("营业时间未知 · 费用：¥12.00");
  await expect(cards.nth(1)).toContainText("测试地点");
  await expect(cards.nth(2)).toContainText("营业时间未知 · 费用未知");
  await expect(cards.nth(2)).toContainText("来源待确认");
  await expect(cards.nth(2).getByText("park · 距离未知", { exact: true })).toBeVisible();

  for (let index = 0; index < 3; index += 1) {
    await expect(cards.nth(index).getByRole("link", { name: "查看 OpenStreetMap 来源 ↗" })).toHaveAttribute(
      "href",
      `https://www.openstreetmap.org/node/${123 + index}`,
    );
    await expect(cards.nth(index).getByRole("link", { name: "© OpenStreetMap contributors" })).toHaveAttribute(
      "href",
      "https://www.openstreetmap.org/copyright",
    );
    await expect(cards.nth(index)).not.toContainText("fee=no");
    await expect(cards.nth(index)).not.toContainText("opening_hours");
  }
  const incomplete = cards.nth(3);
  await expect(incomplete.getByTestId("rev-quick-formal-live-needs-details")).toHaveCount(0);
  expect(detailRequests).toBe(0);
  await incomplete.getByText("补齐营业和费用资料", { exact: true }).click();
  await expect(incomplete).toContainText("向 OpenStreetMap 查询这处地点的营业时间和费用。");
  expect(detailRequests).toBe(0);
  await incomplete.getByTestId("rev-quick-facts-live-needs-details").click();
  await expect(incomplete).toContainText("营业时间：全天 · 免费");
  await expect(incomplete.getByTestId("rev-quick-formal-live-needs-details")).toBeVisible();
  await expect(incomplete.getByTestId("rev-quick-facts-live-needs-details")).toHaveCount(0);
  expect(detailRequests).toBe(1);
  await page.reload();
  await expect(page.getByText("已恢复上次找到的地点，可以继续挑选。", { exact: true })).toBeVisible();
  await expect(page.getByTestId("rev-quick-place-card")).toHaveCount(1);
  await expect(page.getByTestId("rev-quick-place-card")).toContainText("营业时间：全天 · 免费");
  expect(discoveryRequests).toBe(1);
  expect(detailRequests).toBe(1);
});
