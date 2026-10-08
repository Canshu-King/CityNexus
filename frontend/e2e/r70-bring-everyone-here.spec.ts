import { createHmac } from "node:crypto";
import { expect, test, type APIRequestContext, type Browser, type Page } from "@playwright/test";

const API = `http://127.0.0.1:${Number(process.env.CITYNEXUS_BACKEND_PORT ?? 8000)}`;

type Traveler = { id: string; display_name: string };
type Place = {
  id: string;
  name: string;
  city_code: string;
  location: { latitude: number; longitude: number };
};
type NavigationTarget = {
  kind: string;
  place_id: string;
  name: string;
  latitude: number;
  longitude: number;
  coordinate_system: string;
};

function travelerToken(travelerId: string): string {
  const secret = process.env.CITYNEXUS_TRAVELER_AUTH_SECRET;
  if (!secret || Buffer.byteLength(secret, "utf8") < 32) {
    throw new Error("R70 E2E requires a test-only CITYNEXUS_TRAVELER_AUTH_SECRET of at least 32 bytes");
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

async function openJourneyPage(
  browser: Browser,
  journeyId: string,
  token: string,
): Promise<{ page: Page; close: () => Promise<void> }> {
  const context = await browser.newContext({ locale: "en-US", timezoneId: "Asia/Shanghai" });
  const page = await context.newPage();
  await page.addInitScript(({ id, bearer }) => {
    localStorage.setItem("citynexus.v8.journey_id", id);
    localStorage.setItem("citynexus.locale", "en-US");
    sessionStorage.setItem("citynexus.traveler.bearer", bearer);
  }, { id: journeyId, bearer: token });
  await page.goto("/v8/live", { waitUntil: "domcontentloaded" });
  await expect(page.getByTestId("journey-group-presence")).toBeVisible();
  return { page, close: () => context.close() };
}

test("R70 invites one companion into an independent, navigable visit", async ({ browser, request }) => {
  const resetToken = process.env.CITYNEXUS_DEMO_RESET_TOKEN;
  if (!resetToken) throw new Error("R70 E2E requires CITYNEXUS_DEMO_RESET_TOKEN for its fresh SQLite database");
  const reset = await api<{ journey_id: string; traveler_id: string; city_code: string }>(request, "/api/v1/demo/reset", {
    method: "POST",
    headers: { "X-Demo-Reset-Token": resetToken },
  });
  const journeyId = reset.journey_id;
  const ownerId = reset.traveler_id;
  const ownerToken = travelerToken(ownerId);
  const candidates = await api<Array<{ id: string }>>(request, `/api/v1/journeys/${journeyId}/plans/generate`, {
    method: "POST",
    data: { candidate_count: 1 },
  });
  const planId = candidates[0]?.id;
  if (!planId) throw new Error("R70 E2E could not generate a demo PlanVersion");
  await api(request, `/api/v1/journeys/${journeyId}/plans/${planId}/select`, { method: "POST" });
  await api(request, `/api/v1/journeys/${journeyId}/start`, { method: "POST" });

  const companion = await api<Traveler>(request, "/api/v1/travelers", {
    method: "POST",
    data: { display_name: "R70 Invited Companion", locale: "en-US", timezone: "Asia/Tokyo" },
  });
  const companionToken = travelerToken(companion.id);
  await api(request, `/api/v1/journeys/${journeyId}/members`, {
    method: "POST",
    data: { traveler_id: companion.id, role: "COLLABORATOR", invited_by: ownerId },
  });
  await api(request, `/api/v1/journeys/${journeyId}/operator/start`, {
    method: "POST",
    token: ownerToken,
    data: { interval_seconds: 3600 },
  });

  const experience = await api<{
    journey: { city_code: string; current_activity_id: string | null };
    active_plan: { id: string; activities: Array<{ place_id: string | null }> };
  }>(request, `/api/v1/journeys/${journeyId}/experience`);
  const places = await api<Place[]>(request, `/api/v1/places?city_code=${encodeURIComponent(experience.journey.city_code)}`);
  const plannedPlaceIds = new Set(experience.active_plan.activities.map((activity) => activity.place_id).filter(Boolean));
  const privatePlace = places.find((place) => !plannedPlaceIds.has(place.id));
  if (!privatePlace) throw new Error("the demo city needs a known Place outside the active shared plan");

  await api(request, `/api/v1/journeys/${journeyId}/agent/commands`, {
    method: "POST",
    token: ownerToken,
    data: {
      command: "I want to go alone for a while and meet at the next shared stop.",
      requested_autonomy: "PLAN_ONLY",
    },
  });
  const created = await api<{ member_side_quest: { id: string; state: string } }>(
    request,
    `/api/v1/journeys/${journeyId}/member-side-quests`,
    { method: "POST", token: ownerToken, data: { place_id: privatePlace.id } },
  );
  const ownerQuestId = created.member_side_quest.id;
  expect(created.member_side_quest.state).toBe("READY");
  const preview = await api<{
    place: { place_id: string; name: string; source: string; latitude: number; longitude: number };
    rendezvous: { title: string; place_name: string; scheduled_at: string | null };
    recipient_count: number;
  }>(request, `/api/v1/journeys/${journeyId}/member-side-quests/${ownerQuestId}/place-invitation-preview`, {
    token: ownerToken,
  });
  expect(preview.recipient_count).toBe(1);
  expect(preview.place.place_id).toBe(privatePlace.id);

  const before = await api<{
    member_side_quest: unknown;
    member_place_invitations: { incoming: unknown[] };
  }>(request, `/api/v1/journeys/${journeyId}/operator`, { token: companionToken });
  expect(before.member_side_quest).toBeNull();
  expect(before.member_place_invitations.incoming).toEqual([]);
  expect(JSON.stringify(before)).not.toContain(privatePlace.name);

  // Every browser identity gets its own context and signed principal. Neither
  // context grants geolocation permission.
  const owner = await openJourneyPage(browser, journeyId, ownerToken);
  const invited = await openJourneyPage(browser, journeyId, companionToken);
  try {
    const ownerCard = owner.page.getByTestId("member-side-quest-card");
    await expect(ownerCard).toHaveAttribute("data-state", "READY");
    await expect(ownerCard.getByTestId("member-place-invitation-sent")).toHaveCount(0);

    await ownerCard.getByTestId("member-place-invitation-review").click();
    const previewDialog = owner.page.getByTestId("member-place-invitation-preview");
    await expect(previewDialog).toBeVisible();
    await expect(previewDialog).toContainText(privatePlace.name);
    await expect(previewDialog).toContainText(preview.place.source);
    await expect(previewDialog).toContainText(preview.rendezvous.title);
    await expect(previewDialog).toContainText(preview.rendezvous.place_name);
    await expect(previewDialog).toContainText("exact public pin");
    await expect(previewDialog).toContainText("device location, original search coordinates, private note, route");
    await expect(previewDialog).toContainText("15 minutes");
    if (preview.rendezvous.scheduled_at) {
      await expect(previewDialog).toContainText(new Date(preview.rendezvous.scheduled_at).toLocaleString("en-US", {
        timeZone: "Asia/Shanghai",
      }));
    }
    const createResponsePromise = owner.page.waitForResponse((response) =>
      response.request().method() === "POST"
        && response.url().endsWith(`/member-side-quests/${ownerQuestId}/place-invitations`),
    );
    await previewDialog.getByTestId("member-place-invitation-confirm").click();
    const createResponse = await createResponsePromise;
    expect(createResponse.ok()).toBeTruthy();
    const createdProjection = await createResponse.json() as {
      member_place_invitations: { sent: Array<{
        invitation_id: string;
        created_at: string;
        expires_at: string;
      }> };
    };
    const createdInvitation = createdProjection.member_place_invitations.sent[0];
    const ttlMilliseconds = Date.parse(createdInvitation.expires_at) - Date.parse(createdInvitation.created_at);
    expect(ttlMilliseconds).toBeGreaterThanOrEqual(14 * 60_000);
    expect(ttlMilliseconds).toBeLessThanOrEqual(16 * 60_000);
    const sent = ownerCard.getByTestId("member-place-invitation-sent");
    await expect(sent).toHaveAttribute("data-state", "OPEN");
    await expect(sent).toContainText(companion.display_name);
    await expect(sent).toContainText("INVITED");

    await invited.page.reload({ waitUntil: "domcontentloaded" });
    const incoming = invited.page.getByTestId("member-place-invitation");
    await expect(incoming).toHaveAttribute("data-state", "INVITED");
    await expect(incoming).toContainText(privatePlace.name);
    await expect(incoming).toContainText(preview.place.source);
    await expect(incoming).toContainText(`${preview.place.latitude.toFixed(5)}, ${preview.place.longitude.toFixed(5)}`);
    await expect(incoming).toContainText("WGS84");
    await expect(incoming).toContainText(preview.rendezvous.title);
    await expect(incoming).toContainText(preview.rendezvous.place_name);
    await expect(incoming).toContainText("not a promise that the visit fits");
    if (preview.rendezvous.scheduled_at) {
      await expect(incoming).toContainText(new Date(preview.rendezvous.scheduled_at).toLocaleString("en-US", {
        timeZone: "Asia/Shanghai",
      }));
    }
    const incomingProjection = await api<{
      member_place_invitations: { incoming: Array<Record<string, unknown>> };
    }>(request, `/api/v1/journeys/${journeyId}/operator`, { token: companionToken });
    expect(JSON.stringify(incomingProjection.member_place_invitations.incoming[0])).not.toContain(ownerQuestId);

    let popupCount = 0;
    const unexpectedPosts: string[] = [];
    invited.page.on("popup", () => { popupCount += 1; });
    invited.page.on("request", (browserRequest) => {
      if (browserRequest.method() === "POST"
        && browserRequest.url().startsWith(API)
        && !browserRequest.url().endsWith(`/member-place-invitations/${createdInvitation.invitation_id}/respond`)) {
        unexpectedPosts.push(browserRequest.url());
      }
    });
    await incoming.getByTestId("member-place-invitation-view-pin").click();
    const pinConsent = invited.page.getByTestId("member-place-invitation-pin-consent");
    await expect(pinConsent).toBeVisible();
    expect(popupCount).toBe(0);
    await invited.page.context().route("https://www.openstreetmap.org/**", (route) => route.fulfill({
      status: 200,
      contentType: "text/html",
      body: "<!doctype html><title>OSM pin fixture</title>",
    }));
    const pinPopupPromise = invited.page.waitForEvent("popup");
    await pinConsent.getByTestId("member-place-invitation-pin-confirm").click();
    const pinPopup = await pinPopupPromise;
    const pinUrl = new URL(pinPopup.url());
    expect(pinUrl.hostname).toBe("www.openstreetmap.org");
    expect(pinUrl.searchParams.get("mlat")).toBe(String(preview.place.latitude));
    expect(pinUrl.searchParams.get("mlon")).toBe(String(preview.place.longitude));
    expect(pinUrl.searchParams.has("origin")).toBe(false);
    await pinPopup.close();
    await invited.page.context().unroute("https://www.openstreetmap.org/**");
    await expect(incoming).toBeVisible(); // Viewing the pin did not accept the invitation.

    popupCount = 0;
    await incoming.getByTestId("member-place-invitation-accept").click();
    const ownCard = invited.page.getByTestId("member-side-quest-card");
    await expect(ownCard).toHaveAttribute("data-state", "READY");
    await expect(ownCard).toContainText(privatePlace.name);
    expect(popupCount).toBe(0);
    expect(unexpectedPosts).toEqual([]);
    await expect(invited.page.getByTestId("member-place-invitation")).toHaveCount(0);

    await invited.page.reload({ waitUntil: "domcontentloaded" });
    const refreshedOwnCard = invited.page.getByTestId("member-side-quest-card");
    await expect(refreshedOwnCard).toHaveAttribute("data-state", "READY");
    await expect(refreshedOwnCard).toContainText(privatePlace.name);
    const ownProjection = await api<{ member_side_quest: { id: string } }>(
      request,
      `/api/v1/journeys/${journeyId}/operator`,
      { token: companionToken },
    );
    const ownQuestId = ownProjection.member_side_quest.id;
    expect(ownQuestId).not.toBe(ownerQuestId);
    const navigationPath = `/api/v1/journeys/${journeyId}/member-side-quests/${ownQuestId}/navigation-targets`;
    const navigation = await api<{ target: NavigationTarget }>(request, navigationPath, { token: companionToken });
    expect(navigation.target.kind).toBe("PRIVATE_STOP");
    expect(navigation.target.place_id).toBe(privatePlace.id);
    expect(navigation.target.coordinate_system).toBe("WGS84");

    await invited.page.context().route("https://www.google.com/maps/**", (route) => route.fulfill({
      status: 200,
      contentType: "text/html",
      body: "<!doctype html><title>Maps fixture</title>",
    }));
    const navigationResponse = invited.page.waitForResponse((response) =>
      response.request().method() === "GET"
        && response.url().includes(`/journeys/${journeyId}/member-side-quests/`)
        && response.url().endsWith("/navigation-targets"),
    );
    await ownCard.getByTestId("member-side-quest-open-walking-maps").click();
    const navigationConsent = invited.page.getByTestId("member-side-quest-navigation-consent");
    await expect(navigationConsent).toBeVisible();
    const navigationBody = await (await navigationResponse).json() as { target: NavigationTarget };
    expect(navigationBody.target.place_id).toBe(privatePlace.id);
    const walkingPopupPromise = invited.page.waitForEvent("popup");
    await navigationConsent.getByTestId("member-side-quest-consent-google").click();
    const walkingPopup = await walkingPopupPromise;
    await expect.poll(() => new URL(walkingPopup.url()).hostname).toBe("www.google.com");
    const walkingUrl = new URL(walkingPopup.url());
    expect(walkingUrl.searchParams.get("destination")).toBe(
      `${navigationBody.target.latitude},${navigationBody.target.longitude}`,
    );
    expect(walkingUrl.searchParams.get("travelmode")).toBe("walking");
    expect(walkingUrl.searchParams.has("origin")).toBe(false);
    await walkingPopup.close();

    await owner.page.reload({ waitUntil: "domcontentloaded" });
    const refreshedOwnerCard = owner.page.getByTestId("member-side-quest-card");
    await expect(refreshedOwnerCard).toHaveAttribute("data-state", "READY");
    const ownerSent = refreshedOwnerCard.getByTestId("member-place-invitation-sent");
    await expect(ownerSent).toBeVisible();
    await expect(ownerSent).toContainText(`${companion.display_name}: ACCEPTED_OWN_STOP_READY`);
    const after = await api<{ active_plan: { id: string } }>(request, `/api/v1/journeys/${journeyId}/experience`);
    expect(after.active_plan.id).toBe(experience.active_plan.id);
  } finally {
    await Promise.all([owner.close(), invited.close()]);
  }
});
