import { createHash, createHmac } from "node:crypto";
import { expect, test, type APIRequestContext, type Browser, type Page } from "@playwright/test";

const API = `http://127.0.0.1:${Number(process.env.CITYNEXUS_BACKEND_PORT ?? 8000)}`;

type Traveler = { id: string; display_name: string };
type Presence = { group_presence: { active_plan_version_id: string; current_activity_id: string | null } };

function travelerToken(travelerId: string): string {
  const secret = process.env.CITYNEXUS_TRAVELER_AUTH_SECRET;
  if (!secret || Buffer.byteLength(secret, "utf8") < 32) {
    throw new Error("R80 Playwright requires a per-run CITYNEXUS_TRAVELER_AUTH_SECRET");
  }
  const issuedAt = Math.floor(Date.now() / 1000);
  const body = Buffer.from(JSON.stringify({
    aud: "citynexus-traveler", exp: issuedAt + 3600, iat: issuedAt, sub: travelerId, v: 1,
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
    headers: { "Idempotency-Key": "r80-member-" + inviteeId },
    data: { target_traveler_id: inviteeId },
  });
  await api(request, "/api/v1/journey-membership-invitations/" + offer.invitation_id + "/respond", {
    method: "POST", token: inviteeToken, data: { decision: "ACCEPT" },
  });
}

async function openPage(
  browser: Browser,
  token: string,
  journeyId: string,
  geolocation: { latitude: number; longitude: number; accuracy: number },
): Promise<{ page: Page; close: () => Promise<void> }> {
  const context = await browser.newContext({
    locale: "en-US",
    timezoneId: "Asia/Shanghai",
    permissions: ["geolocation"],
    geolocation,
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

async function consentToRoute(page: Page, handoffId: string): Promise<{ observationId: string; routeState: string }> {
  const locationPromise = page.waitForResponse((response) =>
    response.request().method() === "POST" && response.url().endsWith(`/rendezvous-buddy-handoffs/${handoffId}/route/location`),
  );
  await page.getByTestId("journey-buddy-route-start").click();
  const locationConsent = page.getByTestId("journey-buddy-route-consent");
  await expect(locationConsent).toHaveAttribute("data-consent-step", "LOCATION");
  await expect(locationConsent).toContainText("caller-private");
  await expect(locationConsent).toContainText("does not call a routing provider");
  await page.getByTestId("journey-buddy-route-location-confirm").click();
  const locationResponse = await locationPromise;
  expect(locationResponse.status()).toBe(201);
  const observation = await locationResponse.json() as {
    location_observation_id: string;
    visibility: string;
    external_provider_contacted: boolean;
  };
  expect(observation.visibility).toBe("CALLER_PRIVATE");
  expect(observation.external_provider_contacted).toBe(false);

  const providerConsent = page.getByTestId("journey-buddy-route-consent");
  await expect(providerConsent).toHaveAttribute("data-consent-step", "PROVIDER");
  await expect(providerConsent).toContainText("precise origin once");
  const routePromise = page.waitForResponse((response) =>
    response.request().method() === "POST" && response.url().endsWith(`/rendezvous-buddy-handoffs/${handoffId}/route`),
  );
  await page.getByTestId("journey-buddy-route-provider-confirm").click();
  const routeResponse = await routePromise;
  expect(routeResponse.status()).toBe(200);
  const routeRequest = routeResponse.request().postDataJSON() as {
    location_observation_id: string;
    requested_mode: string;
    external_provider_disclosure_confirmed: boolean;
  };
  expect(routeRequest.location_observation_id).toBe(observation.location_observation_id);
  expect(routeRequest.requested_mode).toBe("WALK");
  expect(routeRequest.external_provider_disclosure_confirmed).toBe(true);
  const route = await routeResponse.json() as { route_state: string; duration_min: number | null };
  await expect(page.getByTestId("journey-buddy-route-result")).toBeVisible();
  if (route.route_state === "UNKNOWN") expect(route.duration_min).toBeNull();
  return { observationId: observation.location_observation_id, routeState: route.route_state };
}

test("R80 routes each signed member privately to the mutually accepted handoff", async ({ browser, request }) => {
  test.setTimeout(180_000);
  const resetToken = process.env.CITYNEXUS_DEMO_RESET_TOKEN;
  if (!resetToken) throw new Error("R80 Playwright requires the isolated-run CITYNEXUS_DEMO_RESET_TOKEN");

  const reset = await api<{ journey_id: string; traveler_id: string }>(request, "/api/v1/demo/reset", {
    method: "POST", headers: { "X-Demo-Reset-Token": resetToken },
  });
  const journeyId = reset.journey_id;
  const journeyPath = "/api/v1/journeys/" + journeyId;
  const helperId = reset.traveler_id;
  const helperToken = travelerToken(helperId);
  const plans = await api<Array<{ id: string }>>(request, journeyPath + "/plans/generate", {
    method: "POST", data: { candidate_count: 1 },
  });
  const planId = plans[0]?.id;
  if (!planId) throw new Error("R80 E2E could not generate the shared Journey plan");
  await api(request, journeyPath + "/plans/" + planId + "/select", { method: "POST", token: helperToken });
  await api(request, journeyPath + "/start", { method: "POST", token: helperToken });

  const bystander = await api<Traveler>(request, "/api/v1/travelers", {
    method: "POST", data: { display_name: "R80 Bystander", locale: "en-US", timezone: "Asia/Shanghai" },
  });
  const bystanderToken = travelerToken(bystander.id);
  await acceptInvitation(request, journeyPath, helperToken, bystanderToken, bystander.id);
  const requester = await api<Traveler>(request, "/api/v1/travelers", {
    method: "POST", data: { display_name: "R80 Requester", locale: "en-US", timezone: "Asia/Shanghai" },
  });
  const requesterToken = travelerToken(requester.id);
  await acceptInvitation(request, journeyPath, helperToken, requesterToken, requester.id);

  const requesterOperator = await api<Record<string, any>>(request, journeyPath + "/operator", { token: requesterToken });
  const presence = requesterOperator.group_presence;
  const target = presence.rendezvous;
  const audience = [...presence.members.map((member: { member_id: string }) => member.member_id)].sort();
  // The server expects the unkeyed SHA-256 of the canonical sorted cohort bytes.
  const expectedAudience = createHash("sha256").update(JSON.stringify(audience)).digest("hex");
  const signal = await api<{ signal_id: string }>(request, journeyPath + "/rendezvous-member-signals", {
    method: "POST",
    token: requesterToken,
    headers: { "Idempotency-Key": "r80-help-" + requester.id },
    data: {
      signal_kind: "NEEDS_COORDINATION",
      expected_active_plan_version_id: presence.active_plan_version_id,
      expected_current_activity_id: presence.current_activity_id,
      expected_rendezvous_activity_id: target.activity_id,
      expected_public_place_id: target.place_id,
      expected_audience_sha256: expectedAudience,
    },
  });
  await api(request, journeyPath + "/rendezvous-member-signals/" + signal.signal_id + "/acknowledge", {
    method: "POST", token: helperToken,
  });
  const candidates = await api<{ items: Array<{ place_id: string; name: string }> }>(request,
    journeyPath + "/rendezvous-buddy-handoffs/candidates?signal_id=" + signal.signal_id,
    { token: helperToken },
  );
  const selected = candidates.items.find((item) => item.place_id !== target.place_id) ?? candidates.items[0];
  if (!selected) throw new Error("R80 E2E found no server-selected public handoff place");
  const offered = await api<{ handoff_id: string }>(request, journeyPath + "/rendezvous-buddy-handoffs", {
    method: "POST",
    token: helperToken,
    headers: { "Idempotency-Key": "r80-offer-" + requester.id },
    data: {
      help_signal_id: signal.signal_id,
      expected_active_plan_version_id: candidates.active_plan_version_id,
      expected_current_activity_id: candidates.current_activity_id,
      expected_rendezvous_activity_id: candidates.rendezvous_activity_id,
      expected_original_public_place_id: candidates.original_public_place_id,
      expected_audience_sha256: candidates.audience_sha256,
      handoff_place_id: selected.place_id,
    },
  });
  await api(request, journeyPath + "/rendezvous-buddy-handoffs/" + offered.handoff_id + "/respond", {
    method: "POST", token: requesterToken, data: { decision: "ACCEPT" },
  });

  const bystanderBefore = await api<{ items: unknown[] }>(request,
    journeyPath + "/rendezvous-buddy-handoffs/current", { token: bystanderToken },
  );
  expect(bystanderBefore.items).toEqual([]);
  const helperBeforeRoute = await api<Record<string, any>>(request,
    journeyPath + "/rendezvous-buddy-handoffs/" + offered.handoff_id + "/route/current", { token: helperToken },
  );
  expect(helperBeforeRoute.status).toBe("NOT_REQUESTED");

  const helper = await openPage(browser, helperToken, journeyId, { latitude: 39.9042, longitude: 116.4074, accuracy: 12 });
  const peer = await openPage(browser, bystanderToken, journeyId, { latitude: 35.6762, longitude: 139.6503, accuracy: 20 });
  const requesterPage = await openPage(browser, requesterToken, journeyId, { latitude: 31.2304, longitude: 121.4737, accuracy: 15 });
  const privateLocationPosts: string[] = [];
  const wrongLocationPosts: string[] = [];
  for (const page of [helper.page, peer.page, requesterPage.page]) {
    page.on("request", (item) => {
      if (item.method() !== "POST") return;
      if (item.url().endsWith("/route/location")) privateLocationPosts.push(item.url());
      if (item.url().endsWith(journeyPath + "/location") || item.url().endsWith("/group-presence/route")) {
        wrongLocationPosts.push(item.url());
      }
    });
  }

  try {
    await helper.page.getByTestId("journey-rendezvous-refresh").click();
    await expect(helper.page.getByTestId("journey-buddy-handoff")).toContainText(selected.name);
    await requesterPage.page.getByTestId("journey-rendezvous-refresh").click();
    await expect(requesterPage.page.getByTestId("journey-buddy-handoff")).toContainText(selected.name);
    await expect(helper.page.getByTestId("journey-buddy-accepted-truth")).toBeVisible();
    await expect(requesterPage.page.getByTestId("journey-buddy-accepted-truth")).toBeVisible();
    await expect(peer.page.getByTestId("journey-buddy-handoff")).toHaveCount(0);
    await expect(peer.page.getByTestId("journey-buddy-route-start")).toHaveCount(0);

    const beforeOperator = await api<Presence>(request, journeyPath + "/operator", { token: helperToken });
    const helperRoute = await consentToRoute(helper.page, offered.handoff_id);
    const requesterRoute = await consentToRoute(requesterPage.page, offered.handoff_id);
    expect(helperRoute.observationId).not.toBe(requesterRoute.observationId);
    expect(privateLocationPosts).toHaveLength(2);
    expect(wrongLocationPosts).toEqual([]);

    const helperRead = await api<Record<string, any>>(request,
      journeyPath + "/rendezvous-buddy-handoffs/" + offered.handoff_id + "/route/current", { token: helperToken },
    );
    const requesterRead = await api<Record<string, any>>(request,
      journeyPath + "/rendezvous-buddy-handoffs/" + offered.handoff_id + "/route/current", { token: requesterToken },
    );
    expect(helperRead.route_state).toBe(helperRoute.routeState);
    expect(requesterRead.route_state).toBe(requesterRoute.routeState);
    expect(JSON.stringify(helperRead)).not.toContain(helperRoute.observationId);
    expect(JSON.stringify(requesterRead)).not.toContain(requesterRoute.observationId);
    expect(JSON.stringify(helperRead)).not.toContain("39.9042");
    expect(JSON.stringify(requesterRead)).not.toContain("31.2304");

    const bystanderOperator = await api<Record<string, any>>(request, journeyPath + "/operator", { token: bystanderToken });
    const bystanderText = JSON.stringify(bystanderOperator);
    expect(bystanderText).not.toContain(offered.handoff_id);
    expect(bystanderText).not.toContain(helperRoute.observationId);
    expect(bystanderText).not.toContain(requesterRoute.observationId);
    expect(bystanderText).not.toContain("39.9042");
    expect(bystanderText).not.toContain("31.2304");
    const bystanderOffline = await api<Record<string, any>>(request, journeyPath + "/offline-snapshot", { token: bystanderToken });
    const bystanderOfflineText = JSON.stringify(bystanderOffline);
    expect(bystanderOfflineText).not.toContain(helperRoute.observationId);
    expect(bystanderOfflineText).not.toContain(requesterRoute.observationId);
    expect(bystanderOfflineText).not.toContain("39.9042");
    expect(bystanderOfflineText).not.toContain("31.2304");

    const afterOperator = await api<Presence>(request, journeyPath + "/operator", { token: helperToken });
    expect(afterOperator.group_presence.active_plan_version_id).toBe(beforeOperator.group_presence.active_plan_version_id);
    expect(afterOperator.group_presence.current_activity_id).toBe(beforeOperator.group_presence.current_activity_id);

    await requesterPage.page.getByTestId("journey-buddy-close").click();
    await expect(requesterPage.page.getByTestId("journey-buddy-handoff")).toHaveCount(0);
    await helper.page.getByTestId("journey-rendezvous-refresh").click();
    await expect(helper.page.getByTestId("journey-buddy-handoff")).toHaveCount(0);
    expect(wrongLocationPosts).toEqual([]);
  } finally {
    await helper.close();
    await peer.close();
    await requesterPage.close();
  }
});
