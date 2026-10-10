import { createHmac } from "node:crypto";
import { expect, test, type APIRequestContext, type Browser, type Page } from "@playwright/test";

const API = `http://127.0.0.1:${Number(process.env.CITYNEXUS_BACKEND_PORT ?? 8000)}`;

type Traveler = { id: string; display_name: string };

function travelerToken(travelerId: string): string {
  const secret = process.env.CITYNEXUS_TRAVELER_AUTH_SECRET;
  if (!secret || Buffer.byteLength(secret, "utf8") < 32) {
    throw new Error("R76 Playwright requires a per-run CITYNEXUS_TRAVELER_AUTH_SECRET");
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

async function openPage(
  browser: Browser,
  token: string,
  journeyId?: string,
  options: { geolocation?: { latitude: number; longitude: number; accuracy: number } } = {},
): Promise<{ page: Page; close: () => Promise<void> }> {
  const context = await browser.newContext({
    locale: "en-US",
    timezoneId: "Asia/Shanghai",
    storageState: { cookies: [], origins: [] },
    ...(options.geolocation
      ? { permissions: ["geolocation"], geolocation: options.geolocation }
      : {}),
  });
  const page = await context.newPage();
  await page.addInitScript(({ id, bearer }) => {
    if (id) localStorage.setItem("citynexus.v8.journey_id", id);
    localStorage.setItem("citynexus.locale", "en-US");
    sessionStorage.setItem("citynexus.traveler.bearer", bearer);
  }, { id: journeyId ?? null, bearer: token });
  await page.goto(journeyId ? "/v8/live" : "/v8/today", { waitUntil: "domcontentloaded" });
  await expect(page.getByTestId("journey-membership-panel")).toBeVisible();
  return { page, close: () => context.close() };
}

test("R76 lets a signed nonmember accept an active-Journey invite and see honest catch-up", async ({ browser, request }) => {
  test.setTimeout(120_000);
  const resetToken = process.env.CITYNEXUS_DEMO_RESET_TOKEN;
  if (!resetToken) throw new Error("R76 Playwright requires the isolated-run CITYNEXUS_DEMO_RESET_TOKEN");

  const reset = await api<{ journey_id: string; traveler_id: string }>(request, "/api/v1/demo/reset", {
    method: "POST",
    headers: { "X-Demo-Reset-Token": resetToken },
  });
  const journeyId = reset.journey_id;
  const ownerId = reset.traveler_id;
  const ownerToken = travelerToken(ownerId);
  const journeyPath = `/api/v1/journeys/${journeyId}`;
  const plans = await api<Array<{ id: string }>>(request, `${journeyPath}/plans/generate`, {
    method: "POST",
    data: { candidate_count: 1 },
  });
  const planId = plans[0]?.id;
  if (!planId) throw new Error("R76 E2E could not generate an active Journey plan");
  await api(request, `${journeyPath}/plans/${planId}/select`, { method: "POST", token: ownerToken });
  await api(request, `${journeyPath}/start`, { method: "POST", token: ownerToken });

  const target = await api<Traveler>(request, "/api/v1/travelers", {
    method: "POST",
    data: { display_name: "R76 Signed New Companion", locale: "en-US", timezone: "Asia/Shanghai" },
  });
  const targetToken = travelerToken(target.id);

  const directAdd = await request.post(`${API}${journeyPath}/members`, {
    data: { traveler_id: target.id, role: "COLLABORATOR", invited_by: ownerId },
    headers: { Authorization: `Bearer ${ownerToken}` },
  });
  expect(directAdd.status()).toBe(409);
  expect(await directAdd.text()).toContain("RECIPIENT_ACCEPTANCE_REQUIRED");
  const beforeMembers = await api<Array<{ traveler_id: string }>>(request, `${journeyPath}/members`, { token: ownerToken });
  expect(beforeMembers.some((member) => member.traveler_id === target.id)).toBe(false);
  const beforeOperator = await request.get(`${API}${journeyPath}/operator`, {
    headers: { Authorization: `Bearer ${targetToken}` },
  });
  expect(beforeOperator.status()).toBe(403);

  const owner = await openPage(browser, ownerToken, journeyId);
  const companion = await openPage(browser, targetToken);
  try {
    const inviteTarget = owner.page.getByTestId("journey-membership-target-id");
    await inviteTarget.fill(target.id);
    const inviteResponsePromise = owner.page.waitForResponse((response) =>
      response.request().method() === "POST" && response.url().endsWith(`${journeyPath}/membership-invitations`),
    );
    await owner.page.getByTestId("journey-membership-send").click();
    const inviteResponse = await inviteResponsePromise;
    expect(inviteResponse.status()).toBe(201);
    const invitation = await inviteResponse.json() as { invitation_id: string; proposed_role: string; state: string };
    expect(invitation.proposed_role).toBe("COLLABORATOR");
    expect(invitation.state).toBe("OFFERED");

    const inbox = await api<Array<Record<string, unknown>>>(request, "/api/v1/travelers/me/journey-membership-invitations", {
      token: targetToken,
    });
    expect(inbox).toHaveLength(1);
    expect(Object.keys(inbox[0] ?? {}).sort()).toEqual([
      "approximate_start_date",
      "city_code",
      "expires_at",
      "invitation_id",
      "inviter_display_name",
      "journey_title",
      "proposed_role",
      "state",
    ].sort());
    const serializedInbox = JSON.stringify(inbox);
    expect(serializedInbox).not.toContain(journeyId);
    expect(serializedInbox).not.toContain(planId);

    await companion.page.getByTestId("journey-membership-refresh").click();
    const preview = companion.page.getByTestId("journey-membership-invitation");
    await expect(preview).toBeVisible();
    await expect(preview).toContainText(String(inbox[0]?.inviter_display_name));
    await expect(preview).toContainText(String(inbox[0]?.journey_title));
    await expect(preview).toContainText(String(inbox[0]?.city_code));
    await expect(preview).toContainText("COLLABORATOR");
    await expect(preview).not.toContainText(planId);
    await expect(preview).not.toContainText(journeyId);

    const acceptPromise = companion.page.waitForResponse((response) =>
      response.request().method() === "POST" && response.url().endsWith(`/journey-membership-invitations/${invitation.invitation_id}/respond`),
    );
    await preview.getByTestId("journey-membership-accept").click();
    const acceptedResponse = await acceptPromise;
    expect(acceptedResponse.ok()).toBeTruthy();
    await expect(companion.page.getByTestId("journey-group-presence")).toBeVisible();
    await expect(companion.page.getByTestId("journey-membership-catchup")).toBeVisible();
    await expect(companion.page.getByTestId("journey-membership-catchup")).toContainText("UNKNOWN / ROUTE_UNAVAILABLE");

    // Catch-up is a persistent current-Journey action, not a one-render
    // success toast. A newcomer can come back after a browser reload.
    await companion.page.reload({ waitUntil: "domcontentloaded" });
    await expect(companion.page.getByTestId("journey-membership-catchup")).toBeVisible();
    await expect(companion.page.getByTestId("journey-membership-catchup")).toContainText("UNKNOWN / ROUTE_UNAVAILABLE");

    const afterMembers = await api<Array<{ traveler_id: string; role: string; joined_at?: string | null }>>(
      request,
      `${journeyPath}/members`,
      { token: ownerToken },
    );
    const joined = afterMembers.filter((member) => member.traveler_id === target.id);
    expect(joined).toHaveLength(1);
    expect(joined[0].role).toBe("COLLABORATOR");
    expect(joined[0].joined_at).toBeTruthy();

    const duplicateAccept = await request.post(`${API}/api/v1/journey-membership-invitations/${invitation.invitation_id}/respond`, {
      data: { decision: "ACCEPT" },
      headers: { Authorization: `Bearer ${targetToken}` },
    });
    expect(duplicateAccept.status()).toBe(409);
    const finalMembers = await api<Array<{ traveler_id: string }>>(request, `${journeyPath}/members`, { token: ownerToken });
    expect(finalMembers.filter((member) => member.traveler_id === target.id)).toHaveLength(1);
  } finally {
    await owner.close();
    await companion.close();
  }
});

test("R77 lets a joined companion request a fresh private route with grounded evidence or UNKNOWN", async ({ browser, request }) => {
  test.setTimeout(180_000);
  const resetToken = process.env.CITYNEXUS_DEMO_RESET_TOKEN;
  if (!resetToken) throw new Error("R77 Playwright requires the isolated-run CITYNEXUS_DEMO_RESET_TOKEN");

  const reset = await api<{ journey_id: string; traveler_id: string }>(request, "/api/v1/demo/reset", {
    method: "POST",
    headers: { "X-Demo-Reset-Token": resetToken },
  });
  const journeyId = reset.journey_id;
  const journeyPath = "/api/v1/journeys/" + journeyId;
  const ownerToken = travelerToken(reset.traveler_id);
  const plans = await api<Array<{ id: string }>>(request, journeyPath + "/plans/generate", {
    method: "POST",
    data: { candidate_count: 1 },
  });
  const planId = plans[0]?.id;
  if (!planId) throw new Error("R77 E2E could not generate the initial Journey plan");
  await api(request, journeyPath + "/plans/" + planId + "/select", { method: "POST", token: ownerToken });
  await api(request, journeyPath + "/start", { method: "POST", token: ownerToken });

  const peer = await api<Traveler>(request, "/api/v1/travelers", {
    method: "POST",
    data: { display_name: "R77 Existing Companion", locale: "en-US", timezone: "Asia/Shanghai" },
  });
  const peerToken = travelerToken(peer.id);
  const peerOffer = await api<{ invitation_id: string }>(request, journeyPath + "/membership-invitations", {
    method: "POST",
    token: ownerToken,
    headers: { "Idempotency-Key": "r77-peer-" + journeyId },
    data: { target_traveler_id: peer.id },
  });
  await api(request, "/api/v1/journey-membership-invitations/" + peerOffer.invitation_id + "/respond", {
    method: "POST",
    token: peerToken,
    data: { decision: "ACCEPT" },
  });

  const companion = await api<Traveler>(request, "/api/v1/travelers", {
    method: "POST",
    data: { display_name: "R77 New Companion", locale: "en-US", timezone: "Asia/Shanghai" },
  });
  const companionToken = travelerToken(companion.id);
  const owner = await openPage(browser, ownerToken, journeyId);
  const existingPeer = await openPage(browser, peerToken, journeyId);
  const newcomer = await openPage(browser, companionToken, undefined, {
    geolocation: { latitude: 12.345678, longitude: 23.456789, accuracy: 6 },
  });

  const locationRequests: string[] = [];
  const routeRequests: Array<{ location_observation_id: string }> = [];
  newcomer.page.on("request", (pageRequest) => {
    if (pageRequest.method() !== "POST") return;
    if (pageRequest.url().endsWith(journeyPath + "/location")) locationRequests.push(pageRequest.url());
    if (pageRequest.url().endsWith(journeyPath + "/group-presence/route")) {
      routeRequests.push(pageRequest.postDataJSON() as { location_observation_id: string });
    }
  });

  try {
    const inviteResponsePromise = owner.page.waitForResponse((response) =>
      response.request().method() === "POST" && response.url().endsWith(journeyPath + "/membership-invitations"),
    );
    await owner.page.getByTestId("journey-membership-target-id").fill(companion.id);
    await owner.page.getByTestId("journey-membership-send").click();
    const inviteResponse = await inviteResponsePromise;
    expect(inviteResponse.status()).toBe(201);
    const invitation = await inviteResponse.json() as { invitation_id: string };

    await newcomer.page.getByTestId("journey-membership-refresh").click();
    const invitationCard = newcomer.page.getByTestId("journey-membership-invitation");
    await expect(invitationCard).toBeVisible();
    await invitationCard.getByTestId("journey-membership-accept").click();
    await expect(newcomer.page.getByTestId("journey-group-presence")).toBeVisible();
    const catchup = newcomer.page.getByTestId("journey-membership-catchup");
    await expect(catchup).toBeVisible();
    await expect(catchup.getByTestId("journey-membership-route-check")).toBeVisible();
    expect(locationRequests).toHaveLength(0);
    expect(routeRequests).toHaveLength(0);

    await newcomer.page.getByTestId("journey-membership-route-check").click();
    const consent = newcomer.page.getByTestId("journey-membership-route-consent");
    await expect(consent).toBeVisible();
    await expect(consent).toContainText("foreground location observation");
    await expect(consent).toContainText("companions can see");
    await expect(consent).toContainText("configured routing provider");
    await expect(consent).toContainText("There is no background sampling or tracking");
    await consent.getByTestId("journey-membership-route-cancel").click();
    await expect(consent).toHaveCount(0);
    expect(locationRequests).toHaveLength(0);
    expect(routeRequests).toHaveLength(0);
    await expect(catchup.getByRole("button", { name: /Open exact meeting-place pin/ })).toBeVisible();

    const currentOperator = await api<{
      group_presence: {
        can_guide: boolean;
        active_plan_version_id: string;
        current_activity_id: string | null;
        rendezvous: {
          activity_id: string;
          title: string;
          place_id: string;
          place_name: string;
          latitude: number;
          longitude: number;
          coordinate_system: string;
        };
      };
    }>(request, journeyPath + "/operator", { token: companionToken });
    const presence = currentOperator.group_presence;
    expect(presence.can_guide).toBe(true);
    expect(presence.rendezvous.coordinate_system).toBe("WGS84");
    const routeResponseBodies = [
      {
        provenance: "CAPTURED_REPLAY",
        duration_min: 19,
        provider: "r77-frozen-route-capture",
      },
      {
        provenance: "SYNTHETIC_FIXTURE",
        duration_min: 999,
        provider: "r77-untrusted-route-fixture",
      },
      {
        // Adversarial provenance: a test provider must not masquerade as a
        // LIVE_PROVIDER_CAPTURE, even when the timestamp and ETA look valid.
        provenance: "LIVE_PROVIDER_CAPTURE",
        duration_min: 8,
        provider: "mock-routing-adapter",
      },
    ];
    let routeReplyCount = 0;
    await newcomer.page.route("**/api/v1/journeys/**/group-presence/route", async (route) => {
      const callNumber = ++routeReplyCount;
      const reply = routeResponseBodies[callNumber - 1];
      if (!reply) {
        await route.abort();
        return;
      }
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          plan_version_id: presence.active_plan_version_id,
          current_activity_id: presence.current_activity_id,
          status: "COMPLETED",
          outcome: "ROUTE_READY",
          target: {
            activity_id: presence.rendezvous.activity_id,
            title: presence.rendezvous.title,
            place_id: presence.rendezvous.place_id,
            place_name: presence.rendezvous.place_name,
            latitude: presence.rendezvous.latitude,
            longitude: presence.rendezvous.longitude,
            coordinate_system: "WGS84",
          },
          route: {
            duration_min: reply.duration_min,
            distance_m: 1400,
            provider: reply.provider,
            provenance: reply.provenance,
            captured_at: new Date().toISOString(),
          },
          authority: "ADVISORY_FOREGROUND_LOCATION",
          shared_commitment_risk: {
            state: "UNKNOWN",
            authority: "ADVISORY_FOREGROUND_LOCATION",
            next_commitment: null,
            predicted_arrival_at: null,
            slack_after_buffer_min: null,
          },
          member_risk_event_id: null,
          guardian_triggered: false,
          guardian: { status: "NOT_ENROLLED" },
          plan_unchanged: true,
          target_unchanged: true,
        }),
      });
    });

    await newcomer.page.getByTestId("journey-membership-route-check").click();
    const firstLocationResponsePromise = newcomer.page.waitForResponse((response) =>
      response.request().method() === "POST" && response.url().endsWith(journeyPath + "/location"),
    );
    const firstRouteResponsePromise = newcomer.page.waitForResponse((response) =>
      response.request().method() === "POST" && response.url().endsWith(journeyPath + "/group-presence/route"),
    );
    await newcomer.page.getByTestId("journey-membership-route-confirm").click();
    const firstLocationResponse = await firstLocationResponsePromise;
    const firstRouteResponse = await firstRouteResponsePromise;
    expect(firstLocationResponse.status()).toBe(201);
    expect(firstRouteResponse.status()).toBe(200);
    const firstObservation = await firstLocationResponse.json() as { id: string };
    expect(routeRequests).toHaveLength(1);
    expect(routeRequests[0].location_observation_id).toBe(firstObservation.id);
    expect(JSON.stringify(routeRequests[0])).not.toContain("12.345678");
    expect(JSON.stringify(routeRequests[0])).not.toContain("23.456789");
    const replayResult = newcomer.page.getByTestId("journey-membership-route-result");
    await expect(replayResult).toHaveAttribute("data-evidence", "REPLAY");
    await expect(replayResult).toHaveAttribute("data-provenance", "CAPTURED_REPLAY");
    await expect(replayResult).toContainText("Captured historical route (not current traffic)");
    await expect(replayResult).toContainText("Walking estimate: about 19 minutes");
    await expect(replayResult).toContainText("Location authority: ADVISORY_FOREGROUND_LOCATION");
    await expect(replayResult).toContainText("not where the group is physically located");
    await expect(newcomer.page.getByTestId("journey-membership-location-truth"))
      .toContainText("explicit location consent");

    for (const viewerToken of [ownerToken, peerToken]) {
      const viewer = await api<{ group_presence: Record<string, unknown> }>(
        request,
        journeyPath + "/operator",
        { token: viewerToken },
      );
      const projected = JSON.stringify(viewer.group_presence);
      expect(projected).not.toContain(firstObservation.id);
      expect(projected).not.toContain("12.345678");
      expect(projected).not.toContain("23.456789");
    }
    await expect(owner.page.getByTestId("journey-group-presence")).not.toContainText("R77 New Companion has arrived");
    await expect(existingPeer.page.getByTestId("journey-group-presence")).not.toContainText("R77 New Companion has arrived");

    await newcomer.page.getByTestId("journey-membership-route-check").click();
    const secondLocationResponsePromise = newcomer.page.waitForResponse((response) =>
      response.request().method() === "POST" && response.url().endsWith(journeyPath + "/location"),
    );
    const secondRouteResponsePromise = newcomer.page.waitForResponse((response) =>
      response.request().method() === "POST" && response.url().endsWith(journeyPath + "/group-presence/route"),
    );
    await newcomer.page.getByTestId("journey-membership-route-confirm").click();
    const secondLocationResponse = await secondLocationResponsePromise;
    const secondRouteResponse = await secondRouteResponsePromise;
    expect(secondLocationResponse.status()).toBe(201);
    expect(secondRouteResponse.status()).toBe(200);
    const secondObservation = await secondLocationResponse.json() as { id: string };
    expect(routeRequests).toHaveLength(2);
    expect(routeRequests[1].location_observation_id).toBe(secondObservation.id);
    const unknownResult = newcomer.page.getByTestId("journey-membership-route-result");
    await expect(unknownResult).toHaveAttribute("data-evidence", "UNKNOWN");
    await expect(unknownResult).toContainText("UNKNOWN / ROUTE_UNAVAILABLE");
    await expect(unknownResult).not.toContainText("999");
    await expect(unknownResult).not.toContainText("minutes");
    await expect(newcomer.page.getByTestId("journey-membership-location-truth"))
      .toContainText("observation may already be stored");
    expect(locationRequests).toHaveLength(2);
    for (const viewerToken of [ownerToken, peerToken]) {
      const viewer = await api<{ group_presence: Record<string, unknown> }>(
        request,
        journeyPath + "/operator",
        { token: viewerToken },
      );
      const projected = JSON.stringify(viewer.group_presence);
      expect(projected).not.toContain(secondObservation.id);
      expect(projected).not.toContain("12.345678");
      expect(projected).not.toContain("23.456789");
    }

    // Even a forged LIVE provenance is UNKNOWN when the named provider is a
    // mock adapter. Never present a fresh-looking 8-minute fake as live routing.
    await newcomer.page.getByTestId("journey-membership-route-check").click();
    const thirdLocationResponsePromise = newcomer.page.waitForResponse((response) =>
      response.request().method() === "POST" && response.url().endsWith(journeyPath + "/location"),
    );
    const thirdRouteResponsePromise = newcomer.page.waitForResponse((response) =>
      response.request().method() === "POST" && response.url().endsWith(journeyPath + "/group-presence/route"),
    );
    await newcomer.page.getByTestId("journey-membership-route-confirm").click();
    const thirdLocationResponse = await thirdLocationResponsePromise;
    const thirdRouteResponse = await thirdRouteResponsePromise;
    expect(thirdLocationResponse.status()).toBe(201);
    expect(thirdRouteResponse.status()).toBe(200);
    const thirdObservation = await thirdLocationResponse.json() as { id: string };
    expect(routeRequests).toHaveLength(3);
    expect(routeRequests[2].location_observation_id).toBe(thirdObservation.id);
    const forgedLive = newcomer.page.getByTestId("journey-membership-route-result");
    await expect(forgedLive).toHaveAttribute("data-provenance", "LIVE_PROVIDER_CAPTURE");
    await expect(forgedLive).toHaveAttribute("data-evidence", "UNKNOWN");
    await expect(forgedLive).toContainText("UNKNOWN / ROUTE_UNAVAILABLE");
    await expect(forgedLive).not.toContainText("8 minutes");
    expect(locationRequests).toHaveLength(3);

    // Simulate another authorized actor advancing the server projection while
    // the consent sheet is open. Active shared-plan changes go through
    // collective mediation, so this UI freshness test changes only the
    // projection response; it does not bypass that governance path.
    let changedProjectionCount = 0;
    await newcomer.page.getByTestId("journey-membership-route-check").click();
    await newcomer.page.route("**/api/v1/journeys/" + journeyId + "/operator", async (route) => {
      const response = await route.fetch();
      const body = await response.json() as {
        group_presence?: {
          active_plan_version_id?: string | null;
          current_activity_id?: string | null;
        } | null;
      };
      if (body.group_presence) {
        changedProjectionCount += 1;
        body.group_presence.active_plan_version_id = "r77-replacement-plan-" + changedProjectionCount;
        body.group_presence.current_activity_id = "r77-replacement-cursor-" + changedProjectionCount;
      }
      await route.fulfill({ response, body: JSON.stringify(body) });
    });
    await newcomer.page.getByTestId("journey-membership-route-confirm").click();
    await expect(newcomer.page.getByTestId("journey-membership-message")).toContainText(
      /plan or meeting stop changed; no location was read/i,
    );
    expect(changedProjectionCount).toBeGreaterThan(0);
    expect(locationRequests).toHaveLength(3);
    expect(routeRequests).toHaveLength(3);
    await expect(newcomer.page.getByTestId("journey-membership-route-result")).toHaveCount(0);

    await newcomer.page.getByRole("button", { name: /Open exact meeting-place pin/ }).click();
    await expect(newcomer.page.getByTestId("journey-membership-map-consent")).toBeVisible();
    const staleMapPopupPromise = newcomer.page.waitForEvent("popup");
    await newcomer.page.getByTestId("journey-membership-map-confirm").click();
    const staleMapPopup = await staleMapPopupPromise;
    await expect.poll(() => staleMapPopup.isClosed()).toBe(true);
    await expect(newcomer.page.getByTestId("journey-membership-message")).toContainText(
      "The plan or meeting stop changed",
    );
    expect(locationRequests).toHaveLength(3);
    expect(routeRequests).toHaveLength(3);
  } finally {
    await owner.close();
    await existingPeer.close();
    await newcomer.close();
  }
});
