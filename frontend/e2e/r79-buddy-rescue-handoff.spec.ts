import { createHmac } from "node:crypto";
import { expect, test, type APIRequestContext, type Browser, type Page } from "@playwright/test";

const API = `http://127.0.0.1:${Number(process.env.CITYNEXUS_BACKEND_PORT ?? 8000)}`;

type Traveler = { id: string; display_name: string };
type HandoffCandidate = {
  place_id: string;
  name: string;
  latitude: number;
  longitude: number;
  coordinate_system: "WGS84";
  source_label: string;
  evidence_grade: string;
  is_original_shared_stop: boolean;
  distance_from_original_m: number;
  distance_basis: "STRAIGHT_LINE_NOT_ETA";
};

function travelerToken(travelerId: string): string {
  const secret = process.env.CITYNEXUS_TRAVELER_AUTH_SECRET;
  if (!secret || Buffer.byteLength(secret, "utf8") < 32) {
    throw new Error("R79 Playwright requires a per-run CITYNEXUS_TRAVELER_AUTH_SECRET");
  }
  const issuedAt = Math.floor(Date.now() / 1000);
  const body = Buffer.from(JSON.stringify({
    aud: "citynexus-traveler",
    exp: issuedAt + 3600,
    iat: issuedAt,
    sub: travelerId,
    v: 1,
  })).toString("base64url");
  const signature = createHmac("sha256", secret).update(body, "ascii").digest("base64url");
  return `${body}.${signature}`;
}

async function api<T>(request: APIRequestContext, path: string, options: {
  method?: "GET" | "POST";
  data?: unknown;
  token?: string;
  headers?: Record<string, string>;
} = {}): Promise<T> {
  const response = options.method === "POST"
    ? await request.post(`${API}${path}`, {
        data: options.data,
        headers: { ...(options.token ? { Authorization: `Bearer ${options.token}` } : {}), ...options.headers },
      })
    : await request.get(`${API}${path}`, {
        headers: { ...(options.token ? { Authorization: `Bearer ${options.token}` } : {}), ...options.headers },
      });
  const text = await response.text();
  if (!response.ok()) throw new Error(`${options.method ?? "GET"} ${path} -> ${response.status()}: ${text.slice(0, 240)}`);
  return JSON.parse(text) as T;
}

async function openPage(browser: Browser, token: string, journeyId: string): Promise<{ page: Page; close: () => Promise<void> }> {
  const context = await browser.newContext({
    locale: "en-US",
    timezoneId: "Asia/Shanghai",
    storageState: { cookies: [], origins: [] },
  });
  const page = await context.newPage();
  await page.addInitScript(({ id, bearer }) => {
    localStorage.setItem("citynexus.v8.journey_id", id);
    localStorage.setItem("citynexus.locale", "en-US");
    sessionStorage.setItem("citynexus.traveler.bearer", bearer);
  }, { id: journeyId, bearer: token });
  await page.goto("/v8/live", { waitUntil: "domcontentloaded" });
  await expect(page.getByTestId("journey-membership-panel")).toBeVisible();
  return { page, close: () => context.close() };
}

async function acceptInvitation(
  request: APIRequestContext,
  journeyPath: string,
  ownerToken: string,
  inviteeToken: string,
  inviteeId: string,
): Promise<void> {
  const offer = await api<{ invitation_id: string }>(request, journeyPath + "/membership-invitations", {
    method: "POST",
    token: ownerToken,
    headers: { "Idempotency-Key": "r79-member-" + inviteeId },
    data: { target_traveler_id: inviteeId },
  });
  await api(request, "/api/v1/journey-membership-invitations/" + offer.invitation_id + "/respond", {
    method: "POST",
    token: inviteeToken,
    data: { decision: "ACCEPT" },
  });
}

test("R79 gives the signed helper and requester a private, mutually accepted public handoff", async ({ browser, request }) => {
  test.setTimeout(180_000);
  const resetToken = process.env.CITYNEXUS_DEMO_RESET_TOKEN;
  if (!resetToken) throw new Error("R79 Playwright requires the isolated-run CITYNEXUS_DEMO_RESET_TOKEN");

  const reset = await api<{ journey_id: string; traveler_id: string }>(request, "/api/v1/demo/reset", {
    method: "POST",
    headers: { "X-Demo-Reset-Token": resetToken },
  });
  const journeyId = reset.journey_id;
  const journeyPath = "/api/v1/journeys/" + journeyId;
  const helperId = reset.traveler_id;
  const helperToken = travelerToken(helperId);
  const plans = await api<Array<{ id: string }>>(request, journeyPath + "/plans/generate", {
    method: "POST",
    data: { candidate_count: 1 },
  });
  const planId = plans[0]?.id;
  if (!planId) throw new Error("R79 E2E could not generate a current Journey plan");
  await api(request, journeyPath + "/plans/" + planId + "/select", { method: "POST", token: helperToken });
  await api(request, journeyPath + "/start", { method: "POST", token: helperToken });

  const bystander = await api<Traveler>(request, "/api/v1/travelers", {
    method: "POST", data: { display_name: "R79 Bystander", locale: "en-US", timezone: "Asia/Shanghai" },
  });
  const bystanderToken = travelerToken(bystander.id);
  await acceptInvitation(request, journeyPath, helperToken, bystanderToken, bystander.id);
  const requester = await api<Traveler>(request, "/api/v1/travelers", {
    method: "POST", data: { display_name: "R79 Requester", locale: "en-US", timezone: "Asia/Shanghai" },
  });
  const requesterToken = travelerToken(requester.id);
  await acceptInvitation(request, journeyPath, helperToken, requesterToken, requester.id);

  const helperBefore = await api<{ group_presence: { active_plan_version_id: string; current_activity_id: string | null } }>(
    request, journeyPath + "/operator", { token: helperToken },
  );
  const beforePlanId = helperBefore.group_presence.active_plan_version_id;
  const beforeCursor = helperBefore.group_presence.current_activity_id;
  const helper = await openPage(browser, helperToken, journeyId);
  const peer = await openPage(browser, bystanderToken, journeyId);
  const requesterPage = await openPage(browser, requesterToken, journeyId);
  const forbiddenPosts: string[] = [];
  const privateLocationPosts: string[] = [];
  const privateRoutePosts: string[] = [];
  for (const page of [helper.page, peer.page, requesterPage.page]) {
    page.on("request", (pageRequest) => {
      if (pageRequest.method() !== "POST") return;
      if (pageRequest.url().endsWith(journeyPath + "/location")
        || pageRequest.url().endsWith(journeyPath + "/group-presence/route")) {
        forbiddenPosts.push(pageRequest.url());
      }
      if (pageRequest.url().includes("/rendezvous-buddy-handoffs/") && pageRequest.url().endsWith("/route/location")) {
        privateLocationPosts.push(pageRequest.url());
      }
      if (pageRequest.url().includes("/rendezvous-buddy-handoffs/") && pageRequest.url().endsWith("/route")) {
        privateRoutePosts.push(pageRequest.url());
      }
    });
  }

  const osmUrls: string[] = [];
  const googleDirectionsUrls: string[] = [];
  for (const context of [helper.page.context(), requesterPage.page.context()]) {
    context.on("request", (item) => {
      if (item.url().startsWith("https://www.openstreetmap.org/")) osmUrls.push(item.url());
      if (item.url().startsWith("https://www.google.com/maps/dir/")) googleDirectionsUrls.push(item.url());
    });
    await context.route("**/*", async (route) => {
      if (route.request().url().startsWith("https://www.openstreetmap.org/")
        || route.request().url().startsWith("https://www.google.com/maps/dir/")) {
        await route.abort();
        return;
      }
      await route.continue();
    });
  }

  try {
    await requesterPage.page.getByTestId("journey-rendezvous-help-share").click();
    const consent = requesterPage.page.getByTestId("journey-rendezvous-consent");
    await expect(consent).toBeVisible();
    await expect(consent).toContainText("Current companions who can see this");
    const helpPromise = requesterPage.page.waitForResponse((response) =>
      response.request().method() === "POST" && response.url().endsWith("/rendezvous-member-signals"),
    );
    await requesterPage.page.getByTestId("journey-rendezvous-consent-confirm").click();
    const helpResponse = await helpPromise;
    expect(helpResponse.status()).toBe(201);
    const help = await helpResponse.json() as { signal_id: string; signal_kind: string };
    expect(help.signal_kind).toBe("NEEDS_COORDINATION");

    await helper.page.getByTestId("journey-rendezvous-refresh").click();
    const helpCard = helper.page.getByTestId("journey-rendezvous-status");
    await expect(helpCard).toContainText("R79 Requester self-reports needing coordination help");
    const ackPromise = helper.page.waitForResponse((response) =>
      response.request().method() === "POST" && response.url().endsWith("/acknowledge"),
    );
    await helper.page.getByTestId("journey-rendezvous-help-acknowledge").click();
    expect((await ackPromise).ok()).toBeTruthy();
    await helper.page.getByTestId("journey-rendezvous-refresh").click();
    await expect(helper.page.getByTestId("journey-buddy-load-candidates")).toBeVisible();

    const bystanderCandidates = await request.get(
      `${API}${journeyPath}/rendezvous-buddy-handoffs/candidates?signal_id=${help.signal_id}`,
      { headers: { Authorization: `Bearer ${bystanderToken}` } },
    );
    expect(bystanderCandidates.status()).toBe(403);
    const bystanderCurrent = await api<{ items: unknown[] }>(request, journeyPath + "/rendezvous-buddy-handoffs/current", {
      token: bystanderToken,
    });
    expect(bystanderCurrent.items).toEqual([]);

    const candidatesPromise = helper.page.waitForResponse((response) =>
      response.request().method() === "GET" && response.url().includes("/rendezvous-buddy-handoffs/candidates?signal_id="),
    );
    await helper.page.getByTestId("journey-buddy-load-candidates").click();
    const candidatesResponse = await candidatesPromise;
    expect(candidatesResponse.status()).toBe(200);
    const candidateList = await candidatesResponse.json() as { items: HandoffCandidate[] };
    expect(candidateList.items.length).toBeGreaterThanOrEqual(1);
    expect(candidateList.items.length).toBeLessThanOrEqual(3);
    const selected = candidateList.items.find((item) => !item.is_original_shared_stop) ?? candidateList.items[0];
    expect(selected.evidence_grade).toBe("DEMO_FIXTURE_NOT_LIVE_VERIFIED");
    expect(selected.distance_basis).toBe("STRAIGHT_LINE_NOT_ETA");
    expect(selected.distance_from_original_m).toBeLessThanOrEqual(1500);
    await expect(helper.page.getByTestId("journey-buddy-candidate-chooser"))
      .toContainText("feasibility is unverified");
    await helper.page.getByTestId("journey-buddy-candidate-select").selectOption(selected.place_id);
    const offerPromise = helper.page.waitForResponse((response) =>
      response.request().method() === "POST" && response.url().endsWith("/rendezvous-buddy-handoffs"),
    );
    await helper.page.getByTestId("journey-buddy-offer").click();
    const offerResponse = await offerPromise;
    expect(offerResponse.status()).toBe(201);
    const offered = await offerResponse.json() as { handoff_id: string; status: string };
    expect(offered.status).toBe("OFFERED");
    await expect(helper.page.getByTestId("journey-buddy-handoff")).toContainText(selected.name);

    await requesterPage.page.getByTestId("journey-rendezvous-refresh").click();
    const requesterOffer = requesterPage.page.getByTestId("journey-buddy-handoff");
    await expect(requesterOffer).toBeVisible();
    await expect(requesterOffer).toContainText(selected.name);
    await expect(requesterOffer).toContainText("not a route or ETA");
    await expect(requesterOffer).toContainText("UNKNOWN");

    const bystanderOperator = await api<Record<string, unknown>>(request, journeyPath + "/operator", { token: bystanderToken });
    expect(JSON.stringify(bystanderOperator)).not.toContain(offered.handoff_id);
    const bystanderAfterOffer = await api<{ items: unknown[] }>(
      request, journeyPath + "/rendezvous-buddy-handoffs/current", { token: bystanderToken },
    );
    expect(bystanderAfterOffer.items).toEqual([]);
    expect(forbiddenPosts).toEqual([]);
    expect(osmUrls).toEqual([]);

    const acceptPromise = requesterPage.page.waitForResponse((response) =>
      response.request().method() === "POST" && response.url().endsWith("/rendezvous-buddy-handoffs/" + offered.handoff_id + "/respond"),
    );
    await requesterPage.page.getByTestId("journey-buddy-accept").click();
    expect((await acceptPromise).status()).toBe(200);
    await helper.page.getByTestId("journey-rendezvous-refresh").click();
    await requesterPage.page.getByTestId("journey-rendezvous-refresh").click();
    await expect(helper.page.getByTestId("journey-buddy-accepted-truth")).toContainText("not GPS proof");
    await expect(requesterPage.page.getByTestId("journey-buddy-accepted-truth")).toContainText("not GPS proof");

    // Current handoffs are fetched from the pair-private endpoint on page reload.
    await helper.page.reload({ waitUntil: "domcontentloaded" });
    await requesterPage.page.reload({ waitUntil: "domcontentloaded" });
    await expect(helper.page.getByTestId("journey-buddy-handoff")).toContainText(selected.name);
    await expect(requesterPage.page.getByTestId("journey-buddy-handoff")).toContainText(selected.name);

    // A declined map consent produces no OSM request. Each participant then
    // separately consents to opening the same exact public WGS84 pin.
    await requesterPage.page.getByTestId("journey-buddy-map-open").click();
    await expect(requesterPage.page.getByTestId("journey-buddy-map-consent")).toContainText(selected.name);
    await requesterPage.page.getByTestId("journey-buddy-map-cancel").click();
    expect(osmUrls).toEqual([]);

    const openRequesterMap = async () => {
      const requestPromise = requesterPage.page.context().waitForEvent("request", {
        timeout: 15_000,
        predicate: (item) => item.url().startsWith("https://www.openstreetmap.org/"),
      });
      const popupPromise = requesterPage.page.waitForEvent("popup");
      await requesterPage.page.getByTestId("journey-buddy-map-open").click();
      await requesterPage.page.getByTestId("journey-buddy-map-confirm").click();
      const [mapRequest, popup] = await Promise.all([requestPromise, popupPromise]);
      const url = new URL(mapRequest.url());
      expect(url.searchParams.get("mlat")).toBe(String(selected.latitude));
      expect(url.searchParams.get("mlon")).toBe(String(selected.longitude));
      expect(url.searchParams.has("origin")).toBe(false);
      await popup.close().catch(() => undefined);
    };
    await openRequesterMap();

    const openHelperMap = async () => {
      const requestPromise = helper.page.context().waitForEvent("request", {
        timeout: 15_000,
        predicate: (item) => item.url().startsWith("https://www.openstreetmap.org/"),
      });
      const popupPromise = helper.page.waitForEvent("popup");
      await helper.page.getByTestId("journey-buddy-map-open").click();
      await helper.page.getByTestId("journey-buddy-map-confirm").click();
      const [mapRequest, popup] = await Promise.all([requestPromise, popupPromise]);
      const url = new URL(mapRequest.url());
      expect(url.searchParams.get("mlat")).toBe(String(selected.latitude));
      expect(url.searchParams.get("mlon")).toBe(String(selected.longitude));
      expect(url.searchParams.has("origin")).toBe(false);
      await popup.close().catch(() => undefined);
    };
    await openHelperMap();
    expect(osmUrls).toHaveLength(2);
    expect(forbiddenPosts).toEqual([]);

    // External walking directions are a separate per-participant consent from the
    // static OSM pin. Their URL carries only the accepted destination and WALK mode.
    const cancelDirections = async (page: Page) => {
      await page.getByTestId("journey-buddy-directions-open").click();
      await expect(page.getByTestId("journey-buddy-directions-consent")).toContainText("no stored origin");
      await expect(page.getByTestId("journey-buddy-directions-consent")).toContainText("does not provide a server-calculated route or ETA");
      await page.getByTestId("journey-buddy-directions-cancel").click();
    };
    await cancelDirections(requesterPage.page);
    expect(googleDirectionsUrls).toEqual([]);

    const openDirections = async (page: Page) => {
      const requestPromise = page.context().waitForEvent("request", {
        timeout: 15_000,
        predicate: (item) => item.url().startsWith("https://www.google.com/maps/dir/"),
      });
      const popupPromise = page.waitForEvent("popup");
      await page.getByTestId("journey-buddy-directions-open").click();
      await expect(page.getByTestId("journey-buddy-directions-consent")).toBeVisible();
      await page.getByTestId("journey-buddy-directions-confirm").click();
      const [mapRequest, popup] = await Promise.all([requestPromise, popupPromise]);
      const url = new URL(mapRequest.url());
      expect(url.searchParams.get("destination")).toBe(`${selected.latitude},${selected.longitude}`);
      expect(url.searchParams.get("travelmode")).toBe("walking");
      expect(url.searchParams.get("dir_action")).toBe("navigate");
      expect(url.searchParams.has("origin")).toBe(false);
      expect(url.searchParams.has("destination_label")).toBe(false);
      expect([...url.searchParams.keys()].sort()).toEqual(["api", "destination", "dir_action", "travelmode"]);
      await expect(page.getByTestId("journey-buddy-message")).toContainText("not a server-verified route or proof of arrival");
      await popup.close().catch(() => undefined);
    };
    await openDirections(requesterPage.page);
    await openDirections(helper.page);
    expect(googleDirectionsUrls).toHaveLength(2);

    // The card shows both evidence legs independently and refuses to present a
    // safe commitment when the return leg is unknown, even if a payload's
    // aggregate risk field is optimistic.
    await requesterPage.page.route(`**${journeyPath}/rendezvous-buddy-handoffs/${offered.handoff_id}/route/current`, async (route) => {
      await route.fulfill({ json: {
        handoff_id: offered.handoff_id,
        route_state: "UNKNOWN",
        status: "UNAVAILABLE",
        reason: "return leg unavailable",
        duration_min: null,
        provider: null,
        provenance: "NO_LIVE_PROVIDER_CONFIGURED",
        captured_at: null,
        route_age_seconds: null,
        origin_age_seconds: null,
        outbound_leg: {
          route_state: "REPLAY",
          status: "COMPLETED",
          reason: "historical receipt only",
          duration_min: 12,
          provider: "valhalla-http",
          provenance: "CAPTURED_REPLAY",
        },
        return_leg: {
          route_state: "UNKNOWN",
          status: "UNAVAILABLE",
          reason: "no current return-route receipt",
          duration_min: null,
          provider: null,
          provenance: "NO_LIVE_PROVIDER_CONFIGURED",
        },
        authority: "CALLER_PRIVATE",
        target_place_name: selected.name,
        target_source_label: selected.source_label,
        target_evidence_grade: selected.evidence_grade,
        original_shared_stop_name: "Original shared stop",
        shared_commitment_risk: {
          state: "ON_TRACK",
          authority: "TEST_FIXTURE",
          next_commitment: null,
          slack_after_buffer_min: 999,
          basis: "TEST_PROVIDER_EMULATOR",
        },
        shared_plan_changed: false,
        physical_arrival_verified: false,
        guardian_triggered: false,
      } });
    });
    await requesterPage.page.getByTestId("journey-rendezvous-refresh").click();
    const twoLegResult = requesterPage.page.getByTestId("journey-buddy-route-result");
    await expect(twoLegResult).toHaveAttribute("data-route-state", "UNKNOWN");
    await expect(twoLegResult.locator('[data-leg="outbound"]')).toContainText("REPLAY");
    await expect(twoLegResult.locator('[data-leg="outbound"]')).toContainText("CAPTURED_REPLAY");
    await expect(twoLegResult.locator('[data-leg="return"]')).toContainText("UNKNOWN");
    await expect(twoLegResult.locator('[data-leg="return"]')).toContainText("NO_LIVE_PROVIDER_CONFIGURED");
    await expect(twoLegResult).toContainText("Protected-commitment risk: UNKNOWN");
    await expect(twoLegResult).not.toContainText("Both legs total about");
    await requesterPage.page.unroute(`**${journeyPath}/rendezvous-buddy-handoffs/${offered.handoff_id}/route/current`);

    // One verified leg can prove the commitment is already at risk even while
    // the onward leg remains unknown. The UI must preserve that lower bound.
    await requesterPage.page.route(`**${journeyPath}/rendezvous-buddy-handoffs/${offered.handoff_id}/route/current`, async (route) => {
      await route.fulfill({ json: {
        handoff_id: offered.handoff_id,
        route_state: "UNKNOWN",
        status: "PARTIAL",
        reason: "return leg unavailable",
        duration_min: null,
        provider: null,
        provenance: "TWO_LEG_ROUTE_EVIDENCE_INCOMPLETE",
        captured_at: null,
        route_age_seconds: null,
        origin_age_seconds: 10,
        outbound_leg: {
          route_state: "LIVE",
          status: "COMPLETED",
          reason: "",
          duration_min: 20,
          provider: "valhalla-http",
          provenance: "LIVE_PROVIDER_CAPTURE",
        },
        return_leg: {
          route_state: "UNKNOWN",
          status: "UNAVAILABLE",
          reason: "no current return-route receipt",
          duration_min: null,
          provider: null,
          provenance: "NO_LIVE_PROVIDER_CONFIGURED",
        },
        authority: "CALLER_PRIVATE",
        target_place_name: selected.name,
        target_source_label: selected.source_label,
        target_evidence_grade: selected.evidence_grade,
        original_shared_stop_name: "Original shared stop",
        shared_commitment_risk: {
          state: "COMMITMENT_AT_RISK",
          authority: "ADVISORY_FOREGROUND_LOCATION",
          next_commitment: { title: "Protected stop", scheduled_at: "2026-10-09T12:00:00Z", safety_buffer_min: 5 },
          slack_after_buffer_min: -10,
          basis: "ONE_VERIFIED_ROUTE_LEG_ALONE_EXCEEDS_PROTECTED_COMMITMENT",
          legs_used: ["TO_HANDOFF"],
          evidence_scope: "CURRENT_PROVIDER_CAPTURE",
        },
        shared_plan_changed: false,
        physical_arrival_verified: false,
        guardian_triggered: false,
      } });
    });
    await requesterPage.page.getByTestId("journey-rendezvous-refresh").click();
    const lowerBoundResult = requesterPage.page.getByTestId("journey-buddy-route-result");
    await expect(lowerBoundResult).toHaveAttribute("data-route-state", "UNKNOWN");
    await expect(lowerBoundResult).toContainText("Protected-commitment risk: COMMITMENT_AT_RISK");
    await expect(requesterPage.page.getByTestId("journey-buddy-route-commitment-warning"))
      .toContainText("One verified route leg alone");
    await expect(lowerBoundResult).not.toContainText("Both legs total about");
    await requesterPage.page.unroute(`**${journeyPath}/rendezvous-buddy-handoffs/${offered.handoff_id}/route/current`);

    await requesterPage.page.route(`**${journeyPath}/rendezvous-buddy-handoffs/${offered.handoff_id}/route/current`, async (route) => {
      await route.fulfill({ json: {
        handoff_id: offered.handoff_id,
        route_state: "UNKNOWN",
        status: "STALE",
        reason: "R81_PRIVATE_LOCATION_BINDING_STALE",
        duration_min: null,
        provider: null,
        provenance: "UNKNOWN",
        captured_at: null,
        route_age_seconds: null,
        origin_age_seconds: null,
        outbound_leg: { route_state: "UNKNOWN", status: "STALE", reason: "stale", duration_min: null, provider: null, provenance: "UNKNOWN" },
        return_leg: { route_state: "UNKNOWN", status: "STALE", reason: "stale", duration_min: null, provider: null, provenance: "UNKNOWN" },
        authority: "UNKNOWN",
        target_place_name: selected.name,
        target_source_label: selected.source_label,
        target_evidence_grade: selected.evidence_grade,
        original_shared_stop_name: "Original shared stop",
        shared_commitment_risk: { state: "UNKNOWN", authority: "UNKNOWN", next_commitment: null, slack_after_buffer_min: null },
        shared_plan_changed: false,
        physical_arrival_verified: false,
        guardian_triggered: false,
      } });
    });
    await requesterPage.page.getByTestId("journey-rendezvous-refresh").click();
    await expect(requesterPage.page.getByTestId("journey-buddy-route-result")).toHaveAttribute("data-route-state", "STALE");
    await expect(requesterPage.page.getByTestId("journey-buddy-route-result")).toContainText("Route context is stale");
    await requesterPage.page.unroute(`**${journeyPath}/rendezvous-buddy-handoffs/${offered.handoff_id}/route/current`);

    // A stalled browser location prompt has a finite timeout and an enabled
    // cancel action. Late geolocation callbacks cannot save an origin or start
    // the separately consented route request.
    await requesterPage.page.evaluate(() => {
      Object.defineProperty(navigator, "geolocation", {
        configurable: true,
        value: {
          getCurrentPosition: (_success: PositionCallback, _error: PositionErrorCallback, options?: PositionOptions) => {
            (window as Window & { __r81GeoTimeout?: number }).__r81GeoTimeout = options?.timeout ?? 0;
          },
        },
      });
    });
    await requesterPage.page.getByTestId("journey-buddy-route-start").click();
    await requesterPage.page.getByTestId("journey-buddy-route-location-confirm").click();
    await expect(requesterPage.page.getByTestId("journey-buddy-route-cancel")).toBeEnabled();
    const geolocationTimeout = await requesterPage.page.evaluate(
      () => (window as Window & { __r81GeoTimeout?: number }).__r81GeoTimeout,
    );
    expect(geolocationTimeout).toBe(15_000);
    await requesterPage.page.getByTestId("journey-buddy-route-cancel").click();
    await expect(requesterPage.page.getByTestId("journey-buddy-route-message")).toContainText("no route request will follow");
    expect(privateLocationPosts).toEqual([]);
    expect(privateRoutePosts).toEqual([]);

    // A denied/failed prompt exits busy and leaves the action available for a
    // deliberate retry; it does not advance to provider disclosure.
    await requesterPage.page.evaluate(() => {
      Object.defineProperty(navigator, "geolocation", {
        configurable: true,
        value: {
          getCurrentPosition: (_success: PositionCallback, error: PositionErrorCallback) => {
            error({ code: 1, message: "denied", PERMISSION_DENIED: 1, POSITION_UNAVAILABLE: 2, TIMEOUT: 3 });
          },
        },
      });
    });
    await requesterPage.page.getByTestId("journey-buddy-route-start").click();
    await requesterPage.page.getByTestId("journey-buddy-route-location-confirm").click();
    await expect(requesterPage.page.getByTestId("journey-buddy-route-message")).toContainText("No location observation was saved; no handoff route was requested");
    await expect(requesterPage.page.getByTestId("journey-buddy-route-start")).toBeEnabled();
    await expect(requesterPage.page.getByTestId("journey-buddy-route-consent")).toHaveCount(0);
    expect(privateLocationPosts).toEqual([]);
    expect(privateRoutePosts).toEqual([]);

    // The exact shared cursor is re-read on confirmation. A stale cursor closes
    // the blank popup and releases no destination to the external provider.
    await requesterPage.page.getByTestId("journey-buddy-directions-open").click();
    await expect(requesterPage.page.getByTestId("journey-buddy-directions-consent")).toBeVisible();
    await requesterPage.page.route("**/api/v1/journeys/*/operator", async (route) => {
      const response = await route.fetch();
      const body = await response.json() as { group_presence?: { current_activity_id?: string | null } };
      if (body.group_presence) body.group_presence.current_activity_id = "r81-stale-cursor";
      await route.fulfill({ response, body: JSON.stringify(body) });
    });
    const stalePopupPromise = requesterPage.page.waitForEvent("popup");
    await requesterPage.page.getByTestId("journey-buddy-directions-confirm").click();
    const stalePopup = await stalePopupPromise;
    await expect.poll(() => stalePopup.isClosed()).toBe(true);
    await requesterPage.page.unroute("**/api/v1/journeys/*/operator");
    await expect(requesterPage.page.getByTestId("journey-buddy-message")).toContainText("No destination was sent to an external map");
    expect(googleDirectionsUrls).toHaveLength(2);
    expect(osmUrls).toHaveLength(2);

    const after = await api<{ group_presence: { active_plan_version_id: string; current_activity_id: string | null } }>(
      request, journeyPath + "/operator", { token: helperToken },
    );
    expect(after.group_presence.active_plan_version_id).toBe(beforePlanId);
    expect(after.group_presence.current_activity_id).toBe(beforeCursor);

    const revokePromise = requesterPage.page.waitForResponse((response) =>
      response.request().method() === "POST" && response.url().endsWith("/rendezvous-buddy-handoffs/" + offered.handoff_id + "/revoke"),
    );
    await requesterPage.page.getByTestId("journey-buddy-close").click();
    expect((await revokePromise).status()).toBe(200);
    await expect(requesterPage.page.getByTestId("journey-buddy-handoff")).toHaveCount(0);
    const helperCurrent = await api<{ items: unknown[] }>(
      request, journeyPath + "/rendezvous-buddy-handoffs/current", { token: helperToken },
    );
    expect(helperCurrent.items).toEqual([]);
    expect(osmUrls).toHaveLength(2);
    expect(forbiddenPosts).toEqual([]);
  } finally {
    await helper.close();
    await peer.close();
    await requesterPage.close();
  }
});
