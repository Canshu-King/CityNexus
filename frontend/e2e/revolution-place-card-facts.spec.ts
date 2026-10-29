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

test("named place search waits for explicit submission and keeps the public area", async ({ page }) => {
  const searches: Record<string, unknown>[] = [];
  await page.addInitScript((id) => {
    window.sessionStorage.setItem("citynexus.traveler.bearer", "signed-only-fixture-token");
    window.localStorage.setItem("citynexus.revolution.firstlook.journey", JSON.stringify({
      id, cityCode: "CN-RV-TEST", cityName: "连城", status: "DRAFT",
    }));
  }, journey);
  await page.route("**/api/v1/**", (route) => route.fulfill({ status: 404,
    contentType: "application/json", body: JSON.stringify({ detail: "TEST_FIXTURE_ENDPOINT_NOT_SEEDED" }),
  }));
  await page.route("**/api/v1/travelers/session", (route) => json(route, { traveler_id: "fixture-named-owner" }));
  await page.route("**/api/v1/agent/runtime-status", (route) => json(route, {
    runtime_identity: "UNCONFIGURED", hermes_compat_configured: false,
  }));
  await page.route(`${root}/bootstrap-discovery/readiness`, (route) => json(route, {
    status: "READY", reason_code: "READY", provider: "photon", provider_name: "Photon TEST_FIXTURE",
    supports_place_name_search: true,
    expected_recipient: "Photon TEST_FIXTURE", capability_state: "TEST_CAPABLE", provider_grade: "TEST_PROVIDER",
    external_request_allowed: true, test_only: true,
  }));
  // The restore leg proves membership with the operator read (2026-10-25). Without this mock the
  // pointer restore treats the 404 as a refusal and the exploration screen never renders.
  await page.route(`${root}/operator`, (route) => json(route, { journey_id: journey, state: "OFF" }));
  await page.route(`${root}/bootstrap-shortlist`, (route) => json(route, {
    journey_id: journey, limit: 3, items: [], resume: null, pocket_walk: null,
  }));
  await page.route(`${root}/bootstrap-discovery/current`, (route) => json(route, null));
  await page.route(`${root}/bootstrap-city-search`, (route) => json(route, {
    journey_id: journey, status: "CITY_RESULTS", query: "连城", provider_attempts: [], results: [{
      result_id: "named-city-fixture", name: "连城县", display_name: "连城县（测试地名结果）",
      provider: "test", provider_provenance: "TEST_PROVIDER", latitude: 25.7, longitude: 116.75,
      coordinate_system: "WGS84", confidence: "CITY_CENTROID_UNCERTAIN", selection_state: "CAMERA_ONLY_TAP_REQUIRED",
    }],
  }));
  await page.route(`${root}/bootstrap-discovery`, (route) => {
    expect(route.request().headers().authorization).toBe("Bearer signed-only-fixture-token");
    searches.push(route.request().postDataJSON());
    return json(route, {
      journey_id: journey, status: "LIVE_RESULTS", source_kind: "MANUAL_PUBLIC_CENTER",
      provider: "photon", provider_provenance: "TEST_PROVIDER", receipt_id: "named-place-fixture-receipt",
      attempts: [], candidates: [{ ...candidate("named-museum", "991223", "TEST_PROVIDER"),
        name: "TEST_FIXTURE 想去的博物馆", provider_key: "photon" }],
    });
  });
  await page.goto("/revolution");
  await page.getByTestId("rev-quick-area-secondary").locator("summary").first().click();
  await page.getByTestId("rev-quick-find-city").click();
  await page.getByRole("button", { name: /连城县.*2.5公里/ }).click();
  await page.getByTestId("rev-quick-use-approx-center").click();
  await expect(page.getByRole("region", { name: "按关键词查找公开地点" })).toBeVisible();
  const input = page.getByRole("searchbox", { name: "地点名称或关键词" });
  const submit = page.getByRole("button", { name: "搜索真实地点 →", exact: true });
  await input.fill(" ");
  await expect(submit).toBeDisabled();
  await input.fill("  想去的博物馆  ");
  await expect(page.getByText("把地点名和所选公开区域发送至 Photon TEST_FIXTURE", { exact: true })).toBeVisible();
  expect(searches).toHaveLength(0);
  expect(await submit.evaluate((element) => element.getBoundingClientRect().height)).toBeGreaterThanOrEqual(44);
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
  await input.press("Enter");
  await expect(page.getByTestId("rev-quick-place-card")).toContainText("TEST_FIXTURE 想去的博物馆");
  expect(searches).toEqual([{
    query: "想去的博物馆", query_mode: "name", radius_m: 2500, limit: 8,
    source_kind: "MANUAL_PUBLIC_CENTER", provider_consent: true, consented_provider: "photon",
    latitude: 25.7, longitude: 116.75, coordinate_system: "WGS84", mode: "live",
  }]);
});

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
  // Same membership proof as above: the operator read must answer 200 or the restore is refused.
  await page.route(`${root}/operator`, (route) => json(route, { journey_id: journey, state: "OFF" }));
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
  await page.getByTestId("rev-quick-area-secondary").locator("summary").first().click();
  await page.getByTestId("rev-quick-find-city").click();
  await expect(page.getByTestId("rev-quick-city-results")).toBeVisible();
  await page.getByRole("button", { name: /连城县.*2.5公里/ }).click();
  await page.getByTestId("rev-quick-use-approx-center").click();
  await expect(page.getByText("已经有想去的地方？", { exact: true })).toHaveCount(0);
  await page.locator(".rev-quick-legacy-categories > summary").click();
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

test("trip place facts refresh requires one-time consent and never repeats a recorded attempt", async ({ page }) => {
  let factsRequests = 0;
  let planningIntentReads = 0;
  const receiptId = "trip-place-facts-receipt";
  const incomplete = {
    ...candidate("trip-museum", "8126", "LIVE_PROVIDER"),
    provider_key: "photon",
    selection_blockers: ["OPENING_UNVERIFIED", "COST_UNKNOWN"],
    receipt_id: receiptId,
  };
  const priorFailure = {
    ...candidate("trip-park-prior-failure", "8127", "LIVE_PROVIDER"),
    facts_status: "UNAVAILABLE",
    selection_blockers: ["OPENING_UNVERIFIED", "COST_UNKNOWN"],
    receipt_id: receiptId,
  };
  let planningCandidates: Record<string, unknown>[] = [incomplete, priorFailure];
  const planningIntent = () => ({
    journey_id: journey,
    intent: null,
    trip: { dates: ["2026-11-01", "2026-11-02"], party_size: 2,
      budget: { amount_minor: 100000, currency: "CNY" }, planning_mode: "balanced" },
    candidates: planningCandidates,
    preview_kind: "UNVERIFIED_SUGGESTION_DRAFT",
    transport_status: "UNKNOWN",
    plan_version_id: null,
  });

  await page.addInitScript((id) => {
    window.sessionStorage.setItem("citynexus.traveler.bearer", "signed-only-fixture-token");
    window.sessionStorage.setItem("citynexus.traveler.session-id", "fixture-trip-owner");
    window.localStorage.setItem("citynexus.revolution.firstlook.journey", JSON.stringify({
      id, cityCode: "CN-RV-TEST", cityName: "连城", status: "DRAFT", ownerTravelerId: "fixture-trip-owner",
    }));
  }, journey);
  await page.route("**/api/v1/**", (route) => route.fulfill({ status: 404,
    contentType: "application/json", body: JSON.stringify({ detail: "TEST_FIXTURE_ENDPOINT_NOT_SEEDED" }),
  }));
  await page.route("**/api/v1/travelers/session", (route) => json(route, { traveler_id: "fixture-trip-owner" }));
  await page.route("**/api/v1/agent/runtime-status", (route) => json(route, {
    runtime_identity: "UNCONFIGURED", hermes_compat_configured: false,
  }));
  await page.route(`${root}`, (route) => json(route, {
    id: journey, traveler_id: "fixture-trip-owner", title: "TEST_FIXTURE 连城", city_code: "CN-RV-TEST",
    timezone: "Asia/Shanghai", status: "DRAFT", start_at: "2026-11-01T00:00:00Z",
    end_at: "2026-11-02T00:00:00Z", budget: { amount_minor: 100000, currency: "CNY" },
  }));
  await page.route(`${root}/plans`, (route) => json(route, []));
  await page.route(`${root}/planning-intent`, (route) => {
    planningIntentReads += 1;
    return json(route, planningIntent());
  });
  await page.route(`${root}/bootstrap-discovery/facts`, (route) => {
    factsRequests += 1;
    expect(route.request().headers().authorization).toBe("Bearer signed-only-fixture-token");
    expect(route.request().postDataJSON()).toEqual({
      receipt_id: receiptId, candidate_id: "trip-museum", provider_consent: true,
    });
    const refreshed = {
      ...candidate("trip-museum", "8126", "LIVE_PROVIDER", {
        openingHours: { status: "NORMALIZED_VALID", open: "00:00", close: "24:00" },
      }),
      selection_state: "OPENING_UNVERIFIED",
      selection_blockers: ["COST_UNKNOWN"],
      facts_status: "SUCCESS",
    };
    planningCandidates = [{ ...refreshed, receipt_id: receiptId }, priorFailure];
    return json(route, { journey_id: journey, candidate: refreshed, cached: false });
  });

  await page.goto("/revolution");
  await page.getByTestId("rev-mobile-tab-trips").click();
  await expect(page.getByTestId("rev-plan-workbench")).toBeVisible();
  const museum = page.getByTestId("rev-travel-place-trip-museum");
  const detail = museum.getByTestId("rev-plan-facts-detail-trip-museum");
  await detail.locator("summary").click();
  await expect(detail).toContainText("node/8126");
  await expect(detail).toContainText("发送给 OpenStreetMap");
  const consent = detail.getByTestId("rev-plan-facts-consent-trip-museum");
  const submit = detail.getByTestId("rev-plan-facts-refresh-trip-museum");
  await expect(consent).not.toBeChecked();
  await expect(submit).toBeDisabled();
  expect(factsRequests).toBe(0);

  await consent.check();
  await detail.locator("summary").click();
  await expect(consent).not.toBeChecked();
  expect(factsRequests).toBe(0);
  await detail.locator("summary").click();
  await expect(submit).toBeDisabled();
  await consent.check();
  await submit.click();

  await expect(museum).toContainText("营业时间：全天 · 费用未知");
  await expect(museum).toContainText("待补：费用");
  await expect(museum.getByTestId("rev-plan-facts-detail-trip-museum")).toHaveCount(0);
  const failed = page.getByTestId("rev-travel-place-trip-park-prior-failure");
  await expect(failed).toContainText("待补：营业时间、费用");
  await expect(failed).toContainText("此前查询未能补齐以上资料");
  await expect(failed.locator("details")).toHaveCount(0);
  expect(factsRequests).toBe(1);
  expect(planningIntentReads).toBeGreaterThanOrEqual(2);
});
