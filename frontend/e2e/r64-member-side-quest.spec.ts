import { createHmac } from "node:crypto";
import { expect, test, type APIRequestContext, type Browser, type Page } from "@playwright/test";
import type { MemberSideQuestNavigationTarget } from "../src/api/citynexus";
import {
  buildGoogleWalkingDirectionsUrl,
  buildOpenStreetMapPinUrl,
} from "../src/features/execution/memberSideQuestNavigationLinks";

const API = `http://127.0.0.1:${Number(process.env.CITYNEXUS_BACKEND_PORT ?? 8000)}`;

type Traveler = { id: string; display_name: string };
type Place = {
  id: string;
  name: string;
  city_code: string;
  location: { latitude: number; longitude: number };
};

function travelerToken(travelerId: string): string {
  const secret = process.env.CITYNEXUS_TRAVELER_AUTH_SECRET;
  if (!secret || Buffer.byteLength(secret, "utf8") < 32) {
    throw new Error("R64 E2E requires a test-only CITYNEXUS_TRAVELER_AUTH_SECRET of at least 32 bytes");
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
  geolocation?: { latitude: number; longitude: number; accuracy: number },
): Promise<{ page: Page; close: () => Promise<void> }> {
  const context = await browser.newContext(geolocation
    ? { permissions: ["geolocation"], geolocation }
    : {});
  const page = await context.newPage();
  await page.addInitScript(({ id, bearer }) => {
    localStorage.setItem("citynexus.v8.journey_id", id);
    localStorage.setItem("citynexus.locale", "en-US");
    sessionStorage.setItem("citynexus.traveler.bearer", bearer);
  }, { id: journeyId, bearer: token });
  if (geolocation) {
    await page.addInitScript((point) => {
      Object.defineProperty(navigator, "geolocation", {
        configurable: true,
        value: {
          getCurrentPosition(success: (position: GeolocationPosition) => void) {
            queueMicrotask(() => success({
              coords: {
                latitude: point.latitude,
                longitude: point.longitude,
                accuracy: point.accuracy,
                altitude: null,
                altitudeAccuracy: null,
                heading: null,
                speed: null,
                toJSON: () => ({}),
              },
              timestamp: Date.now(),
              toJSON: () => ({}),
            } as GeolocationPosition));
          },
        },
      });
    }, geolocation);
  }
  await page.goto("/v8/live", { waitUntil: "domcontentloaded" });
  await expect(page.getByTestId("journey-group-presence")).toBeVisible();
  return { page, close: () => context.close() };
}

test("R66 scouts, explicitly selects, then completes the existing private detour and return flow", async ({ browser, request }) => {
  const resetToken = process.env.CITYNEXUS_DEMO_RESET_TOKEN;
  if (!resetToken) throw new Error("R64 E2E requires CITYNEXUS_DEMO_RESET_TOKEN for its isolated demo database");
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
  expect(candidates.length).toBeGreaterThan(0);
  const planId = candidates[0].id;
  await api(request, `/api/v1/journeys/${journeyId}/plans/${planId}/select`, { method: "POST" });
  await api(request, `/api/v1/journeys/${journeyId}/start`, { method: "POST" });

  const collaborator = await api<Traveler>(request, "/api/v1/travelers", {
    method: "POST",
    data: { display_name: "R64 Collaborator", locale: "en-US", timezone: "Asia/Tokyo" },
  });
  await api(request, `/api/v1/journeys/${journeyId}/members`, {
    method: "POST",
    data: { traveler_id: collaborator.id, role: "COLLABORATOR", invited_by: ownerId },
  });
  const collaboratorToken = travelerToken(collaborator.id);
  await api(request, `/api/v1/journeys/${journeyId}/operator/start`, {
    method: "POST",
    token: ownerToken,
    data: { interval_seconds: 3600 },
  });

  const experience = await api<{
    journey: { city_code: string };
    active_plan: { id: string; activities: Array<{ place_id: string | null }> };
  }>(request, `/api/v1/journeys/${journeyId}/experience`);
  const places = await api<Place[]>(request, `/api/v1/places?city_code=${encodeURIComponent(experience.journey.city_code)}`);
  const usedPlaceIds = new Set(experience.active_plan.activities.map((activity) => activity.place_id).filter(Boolean));
  const privatePlace = places.find((place) => !usedPlaceIds.has(place.id));
  if (!privatePlace) throw new Error("the demo city needs a known Place outside the active shared plan");

  const planRowsBefore = await api<Array<{ id: string }>>(request, `/api/v1/journeys/${journeyId}/plans`);
  const activePlanIdBefore = experience.active_plan.id;

  const owner = await openJourneyPage(browser, journeyId, ownerToken, {
    latitude: privatePlace.location.latitude,
    longitude: privatePlace.location.longitude,
    accuracy: 10,
  });
  const collaboratorSession = await openJourneyPage(browser, journeyId, collaboratorToken);
  try {
    const ownerCard = owner.page.getByTestId("member-side-quest-card");
    const scoutCard = owner.page.getByTestId("moment-scout");
    await expect(scoutCard).toBeVisible();
    await expect(ownerCard).toHaveCount(0);
    const scoutResponsePromise = owner.page.waitForResponse((response) =>
      response.request().method() === "POST"
        && response.url().includes(`/journeys/${journeyId}/moment-scout`)
        && !response.url().endsWith("/select"),
    );
    await scoutCard.getByTestId("moment-scout-submit").click();
    const scoutResponse = await scoutResponsePromise;
    expect(scoutResponse.ok()).toBeTruthy();
    const scoutResult = await scoutResponse.json() as {
      scout_state: string;
      candidates: Array<{ place_id: string; name: string; straight_line_distance_m: number; place_provenance: string }>;
      rendezvous: {
        place_name: string;
        scheduled_at: string | null;
        time_state: "AVAILABLE" | "UNKNOWN" | "PAST";
        minutes_until: number | null;
      };
    };
    expect(scoutResult.scout_state).toBe("OPTIONS_AVAILABLE");
    expect(scoutResult.candidates.length).toBeGreaterThan(0);
    expect(scoutResult.candidates.length).toBeLessThanOrEqual(3);
    expect(JSON.stringify(scoutResult)).not.toContain("latitude");
    expect(JSON.stringify(scoutResult)).not.toContain("longitude");
    expect(scoutResult.rendezvous.time_state).not.toBe("PAST");
    await expect(scoutCard.getByTestId("moment-scout-results")).toContainText(scoutResult.rendezvous.place_name);
    // Live discovery is an explicit alternative even if the local catalogue
    // has a few entries (including demo/fixture entries). No external request
    // occurs merely because this opt-in is visible.
    await expect(scoutCard.getByTestId("moment-scout-live-opt-in")).toBeVisible();
    if (scoutResult.rendezvous.time_state === "UNKNOWN") {
      await expect(scoutCard.getByTestId("moment-scout-rendezvous-time-warning")).toContainText("time is unknown");
    } else if ((scoutResult.rendezvous.minutes_until ?? 0) < 30) {
      await expect(scoutCard.getByTestId("moment-scout-rendezvous-time-warning")).toContainText("less than your 30-minute preference");
    }
    const selectedCandidate = scoutResult.candidates[0];
    const privateStopName = selectedCandidate.name;
    const selectedPrivatePlace = places.find((place) => place.id === selectedCandidate.place_id);
    expect(selectedPrivatePlace).toBeTruthy();
    await scoutCard.getByTestId("moment-scout-choose").first().click();
    await expect(scoutCard.getByTestId("moment-scout-confirmation")).toContainText(
      `Go to ${privateStopName}, then rejoin at`,
    );
    await scoutCard.getByTestId("moment-scout-confirm").click();
    await expect(ownerCard).toBeVisible();
    await expect(ownerCard).toHaveAttribute("data-state", "READY");
    await expect(ownerCard.getByTestId("member-side-quest-owner-state")).toContainText(privateStopName);
    await expect(ownerCard).toContainText("shared Journey");

    await ownerCard.getByTestId("member-side-quest-fit-preview").click();
    const fitResult = ownerCard.getByTestId("member-side-quest-fit-result");
    await expect(fitResult).toBeVisible();
    await expect(fitResult).toHaveAttribute("data-state", "UNKNOWN");
    await expect(fitResult).toContainText("We can't confirm whether this private stop fits");

    // Changing the dwell time makes an earlier leave-by estimate stale.
    await ownerCard.getByTestId("member-side-quest-dwell").selectOption("30");
    await expect(fitResult).toHaveCount(0);
    await ownerCard.getByTestId("member-side-quest-fit-preview").click();
    await expect(fitResult).toHaveAttribute("data-state", "UNKNOWN");

    await ownerCard.getByTestId("member-side-quest-navigate").click();
    const privateRoute = ownerCard.getByTestId("member-side-quest-private-route");
    await expect(privateRoute).toBeVisible();
    await expect(privateRoute).toHaveAttribute("data-state", "UNKNOWN");
    await expect(privateRoute).toContainText("No reliable route is available");

    await ownerCard.getByTestId("member-side-quest-open-walking-maps").click();
    const outboundConsent = ownerCard.getByTestId("member-side-quest-navigation-consent");
    await expect(outboundConsent).toBeVisible();
    await expect(outboundConsent).toContainText(privateStopName);
    await expect(outboundConsent).toContainText("exact coordinates will be sent");
    const cancelledPopup = owner.page.waitForEvent("popup", { timeout: 1000 })
      .then(() => true)
      .catch(() => false);
    await outboundConsent.getByTestId("member-side-quest-consent-cancel").click();
    expect(await cancelledPopup).toBe(false);

    await owner.page.context().route("https://www.google.com/maps/**", (route) => route.fulfill({
      status: 200,
      contentType: "text/html",
      body: "<!doctype html><title>Maps fixture</title>",
    }));
    const outboundTargetResponse = owner.page.waitForResponse((response) =>
      response.request().method() === "GET"
        && response.url().includes(`/journeys/${journeyId}/member-side-quests/`)
        && response.url().endsWith("/navigation-targets"),
    );
    await ownerCard.getByTestId("member-side-quest-open-walking-maps").click();
    const outboundTarget = await (await outboundTargetResponse).json() as {
      target: { kind: string; place_id: string; name: string; latitude: number; longitude: number; coordinate_system: string };
    };
    expect(outboundTarget.target.kind).toBe("PRIVATE_STOP");
    expect(outboundTarget.target.place_id).toBe(selectedPrivatePlace!.id);
    expect(outboundTarget.target.coordinate_system).toBe("WGS84");
    await expect(outboundConsent).toBeVisible();
    const googlePopupPromise = owner.page.waitForEvent("popup");
    await outboundConsent.getByTestId("member-side-quest-consent-google").click();
    const googlePopup = await googlePopupPromise;
    await expect.poll(() => new URL(googlePopup.url()).hostname).toBe("www.google.com");
    const googleUrl = new URL(googlePopup.url());
    expect(googleUrl.pathname).toBe("/maps/dir/");
    expect(googleUrl.searchParams.get("api")).toBe("1");
    expect(googleUrl.searchParams.get("travelmode")).toBe("walking");
    expect(googleUrl.searchParams.get("destination")).toBe(
      `${outboundTarget.target.latitude},${outboundTarget.target.longitude}`,
    );
    expect(googleUrl.searchParams.get("dir_action")).toBe("navigate");
    expect(googleUrl.searchParams.has("destination_label")).toBe(false);
    expect(googleUrl.searchParams.has("origin")).toBe(false);
    await googlePopup.close();
    await owner.page.context().unroute("https://www.google.com/maps/**");

    await collaboratorSession.page.reload();
    const safeAway = collaboratorSession.page.getByTestId("journey-member-personal-stop");
    await expect(safeAway).toHaveAttribute("data-state", "PLANNED");
    await expect(safeAway).toContainText("destination visible only to them");
    await expect(collaboratorSession.page.locator("body")).not.toContainText(privateStopName);
    await expect(collaboratorSession.page.getByTestId("member-side-quest-card")).toHaveCount(0);

    await ownerCard.getByTestId("member-side-quest-start").click();
    await expect(ownerCard).toHaveAttribute("data-state", "EN_ROUTE");
    // Neither a preview nor a private route from READY may masquerade as
    // guidance for the new execution state, even after an async completion.
    await expect(fitResult).toHaveCount(0);
    await expect(privateRoute).toHaveCount(0);
    await ownerCard.getByTestId("member-side-quest-arrive").click();
    await expect(ownerCard).toHaveAttribute("data-state", "ARRIVED");
    await expect(ownerCard.getByTestId("member-side-quest-arrival-boundary")).toContainText("not device-verified physical presence");
    await ownerCard.getByTestId("member-side-quest-complete").click();
    await expect(ownerCard).toHaveAttribute("data-state", "COMPLETED");
    await expect(ownerCard.getByTestId("member-side-quest-return-emphasis")).toContainText("return to");
    await expect(ownerCard.getByTestId("member-side-quest-return-state")).toContainText("Return status unknown");
    await expect(ownerCard).toContainText("shared Journey is unchanged");
    await expect(owner.page.getByTestId("moment-scout")).toHaveCount(0);

    await owner.page.context().route("https://www.openstreetmap.org/**", (route) => route.fulfill({
      status: 200,
      contentType: "text/html",
      body: "<!doctype html><title>OpenStreetMap fixture</title>",
    }));
    const rendezvousTargetResponse = owner.page.waitForResponse((response) =>
      response.request().method() === "GET"
        && response.url().includes(`/journeys/${journeyId}/member-side-quests/`)
        && response.url().endsWith("/navigation-targets"),
    );
    await ownerCard.getByTestId("member-side-quest-map-back").click();
    const rendezvousTarget = await (await rendezvousTargetResponse).json() as {
      target: { kind: string; name: string; latitude: number; longitude: number; coordinate_system: string };
    };
    expect(rendezvousTarget.target.kind).toBe("SHARED_RENDEZVOUS");
    expect(rendezvousTarget.target.coordinate_system).toBe("WGS84");
    const returnConsent = ownerCard.getByTestId("member-side-quest-navigation-consent");
    await expect(returnConsent).toBeVisible();
    await expect(returnConsent).toContainText(rendezvousTarget.target.name);
    const osmPopupPromise = owner.page.waitForEvent("popup");
    await returnConsent.getByTestId("member-side-quest-consent-osm").click();
    const osmPopup = await osmPopupPromise;
    await expect.poll(() => new URL(osmPopup.url()).hostname).toBe("www.openstreetmap.org");
    const osmUrl = new URL(osmPopup.url());
    expect(osmUrl.searchParams.get("mlat")).toBe(String(rendezvousTarget.target.latitude));
    expect(osmUrl.searchParams.get("mlon")).toBe(String(rendezvousTarget.target.longitude));
    expect(osmUrl.hash).toBe(`#map=18/${rendezvousTarget.target.latitude}/${rendezvousTarget.target.longitude}`);
    await osmPopup.close();
    await owner.page.context().unroute("https://www.openstreetmap.org/**");
    await expect(ownerCard.getByTestId("member-side-quest-return-state")).toContainText("Return status unknown");

    await collaboratorSession.page.reload();
    const safeReturning = collaboratorSession.page.getByTestId("journey-member-personal-stop");
    await expect(safeReturning).toHaveAttribute("data-state", "FINISHED_RETURN_UNCONFIRMED");
    await expect(safeReturning).toContainText("return has not been confirmed");
    await expect(collaboratorSession.page.locator("body")).not.toContainText(privateStopName);
    await expect(collaboratorSession.page.getByTestId("member-side-quest-card")).toHaveCount(0);
    await expect(collaboratorSession.page.locator("body")).not.toContainText("You are physically rejoined");

    await ownerCard.getByTestId("member-side-quest-head-back").click();
    await expect(ownerCard.getByTestId("member-side-quest-return-state")).toContainText(
      "You reported heading back; this does not verify your location or reunion.",
    );
    await expect(ownerCard.getByTestId("member-side-quest-message")).toContainText("Your return report is saved");
    await collaboratorSession.page.reload();
    const safeHeadedBack = collaboratorSession.page.getByTestId("journey-member-personal-stop");
    await expect(safeHeadedBack).toHaveAttribute("data-state", "RETURN_STARTED_REPORTED");
    await expect(safeHeadedBack).toContainText("has reported heading back (location and reunion are unverified)");
    await expect(collaboratorSession.page.locator("body")).not.toContainText(privateStopName);
    await expect(collaboratorSession.page.getByTestId("member-side-quest-card")).toHaveCount(0);

    const finalExperience = await api<{ active_plan: { id: string } }>(request, `/api/v1/journeys/${journeyId}/experience`);
    const planRowsAfter = await api<Array<{ id: string }>>(request, `/api/v1/journeys/${journeyId}/plans`);
    expect(finalExperience.active_plan.id).toBe(activePlanIdBefore);
    expect(planRowsAfter.map((row) => row.id).sort()).toEqual(planRowsBefore.map((row) => row.id).sort());

    // A modal is only a consent prompt, never a cached authorization. If the
    // split ends after it opens, the final owner-bound target read must refuse
    // the stale return destination and no external URL may be assigned.
    await ownerCard.getByTestId("member-side-quest-map-back").click();
    const staleConsent = ownerCard.getByTestId("member-side-quest-navigation-consent");
    await expect(staleConsent).toBeVisible();
    const endedSplit = await api<{
      planned_separation_result: { physical_reunion_claimed: boolean };
    }>(request, `/api/v1/journeys/${journeyId}/agent/commands`, {
      method: "POST",
      token: ownerToken,
      data: { command: "I'm back with the group.", requested_autonomy: "PLAN_ONLY" },
    });
    expect(endedSplit.planned_separation_result.physical_reunion_claimed).toBe(false);
    const staleNavigationResponse = owner.page.waitForResponse((response) =>
      response.request().method() === "GET"
        && response.url().endsWith("/navigation-targets"),
    );
    const stalePopupPromise = owner.page.waitForEvent("popup");
    await staleConsent.getByTestId("member-side-quest-consent-google").click();
    const stalePopup = await stalePopupPromise;
    expect((await staleNavigationResponse).status()).toBe(409);
    await expect.poll(() => stalePopup.isClosed()).toBe(true);
    await expect(owner.page.getByTestId("member-side-quest-navigation-consent")).toHaveCount(0);
  } finally {
    await Promise.all([owner.close(), collaboratorSession.close()]);
  }
});


test("R67 explicit nearby search and selection use a controlled local Overpass fixture simulation", async ({ browser, request }) => {
  test.skip(
    process.env.CITYNEXUS_R67_TEST_PROVIDER !== "fixture",
    "R67 live E2E uses a local controlled Overpass fixture; it never calls a public provider.",
  );
  const fixtureBase = process.env.CITYNEXUS_R67_OVERPASS_FIXTURE_URL ?? "http://127.0.0.1:8367";
  const fixtureStats = async () => {
    const response = await request.get(`${fixtureBase}/stats`);
    expect(response.ok()).toBeTruthy();
    return await response.json() as { request_count: number; mode: string };
  };
  const startingFixtureRequestCount = (await fixtureStats()).request_count;

  const reset = await api<{ journey_id: string; traveler_id: string }>(request, "/api/v1/demo/reset", {
    method: "POST",
    headers: { "X-Demo-Reset-Token": process.env.CITYNEXUS_DEMO_RESET_TOKEN ?? "" },
  });
  const journeyId = reset.journey_id;
  const ownerId = reset.traveler_id;
  const ownerToken = travelerToken(ownerId);
  const candidates = await api<Array<{ id: string }>>(request, `/api/v1/journeys/${journeyId}/plans/generate`, {
    method: "POST",
    data: { candidate_count: 1 },
  });
  const planId = candidates[0]?.id;
  if (!planId) throw new Error("the demo Journey needs one selectable plan");
  await api(request, `/api/v1/journeys/${journeyId}/plans/${planId}/select`, { method: "POST" });
  await api(request, `/api/v1/journeys/${journeyId}/start`, { method: "POST" });

  const collaborator = await api<Traveler>(request, "/api/v1/travelers", {
    method: "POST",
    data: { display_name: "R67 Collaborator", locale: "en-US", timezone: "Asia/Tokyo" },
  });
  await api(request, `/api/v1/journeys/${journeyId}/members`, {
    method: "POST",
    data: { traveler_id: collaborator.id, role: "COLLABORATOR", invited_by: ownerId },
  });
  const collaboratorToken = travelerToken(collaborator.id);
  await api(request, `/api/v1/journeys/${journeyId}/operator/start`, {
    method: "POST",
    token: ownerToken,
    data: { interval_seconds: 3600 },
  });
  const experienceBefore = await api<{
    journey: { city_code: string };
    active_plan: { id: string };
  }>(request, `/api/v1/journeys/${journeyId}/experience`);
  const planRowsBefore = await api<Array<{ id: string }>>(request, `/api/v1/journeys/${journeyId}/plans`);
  const location = { latitude: 5.123456, longitude: 10.654321, accuracy: 8 };
  const owner = await openJourneyPage(browser, journeyId, ownerToken, location);
  const collaboratorSession = await openJourneyPage(browser, journeyId, collaboratorToken);
  try {
    const scoutCard = owner.page.getByTestId("moment-scout");
    await expect(scoutCard).toBeVisible();
    await scoutCard.getByTestId("moment-scout-interest").selectOption("CULTURE");
    const localPromise = owner.page.waitForResponse((response) =>
      response.request().method() === "POST"
        && response.url().endsWith(`/journeys/${journeyId}/moment-scout`),
    );
    await scoutCard.getByTestId("moment-scout-submit").click();
    const local = await localPromise;
    expect(local.ok()).toBeTruthy();
    expect((await local.json()).scout_state).toBe("NO_GROUNDED_OPTIONS");
    await expect(scoutCard.getByTestId("moment-scout-live-opt-in")).toBeVisible();
    expect((await fixtureStats()).request_count).toBe(startingFixtureRequestCount);

    await scoutCard.getByTestId("moment-scout-live-opt-in").click();
    const consent = scoutCard.getByTestId("moment-scout-live-consent");
    await expect(consent).toContainText("external OpenStreetMap");
    await consent.getByTestId("moment-scout-live-consent-cancel").click();
    expect((await fixtureStats()).request_count).toBe(startingFixtureRequestCount);

    await scoutCard.getByTestId("moment-scout-live-opt-in").click();
    const livePromise = owner.page.waitForResponse((response) =>
      response.request().method() === "POST"
        && response.url().endsWith(`/journeys/${journeyId}/moment-scout/live`),
    );
    await scoutCard.getByTestId("moment-scout-live-consent-confirm").click();
    const liveResponse = await livePromise;
    expect(liveResponse.ok()).toBeTruthy();
    const liveResult = await liveResponse.json() as {
      scout_state: string;
      receipt_id: string;
      candidates: Array<{ candidate_id: string; name: string }>;
    };
    expect(liveResult.scout_state).toBe("LIVE_RESULTS");
    expect(liveResult.candidates).toHaveLength(1);
    expect(liveResult.candidates[0].name).toBe("R67 Fixture OSM Museum");
    expect(JSON.stringify(liveResult)).not.toContain("5.123456");
    expect(JSON.stringify(liveResult)).not.toContain("10.654321");
    expect((await fixtureStats()).request_count).toBe(startingFixtureRequestCount + 1);

    const liveResults = scoutCard.getByTestId("moment-scout-live-results");
    await expect(liveResults).toHaveAttribute("data-state", "LIVE_RESULTS");
    await expect(liveResults).toContainText("R67 Fixture OSM Museum");
    await collaboratorSession.page.reload();
    await expect(collaboratorSession.page.locator("body")).not.toContainText("R67 Fixture OSM Museum");
    await expect(collaboratorSession.page.locator("body")).not.toContainText(liveResult.receipt_id);

    await liveResults.getByTestId("moment-scout-live-choose").click();
    await expect(scoutCard.getByTestId("moment-scout-live-confirmation")).toContainText(
      "return to the current shared rendezvous",
    );
    const selectionPromise = owner.page.waitForResponse((response) =>
      response.request().method() === "POST"
        && response.url().endsWith(`/journeys/${journeyId}/moment-scout/live/select`),
    );
    await scoutCard.getByTestId("moment-scout-live-confirm").click();
    const selection = await selectionPromise;
    expect(selection.status()).toBe(201);
    await expect(owner.page.getByTestId("member-side-quest-card")).toBeVisible();
    await expect(owner.page.getByTestId("member-side-quest-card")).toContainText("R67 Fixture OSM Museum");

    await collaboratorSession.page.reload();
    const coarseStatus = collaboratorSession.page.getByTestId("journey-member-personal-stop");
    await expect(coarseStatus).toHaveAttribute("data-state", "PLANNED");
    await expect(collaboratorSession.page.locator("body")).not.toContainText("R67 Fixture OSM Museum");

    const places = await api<Place[]>(
      request,
      `/api/v1/places?city_code=${encodeURIComponent(experienceBefore.journey.city_code)}`,
    );
    expect(places.filter((place) => place.name === "R67 Fixture OSM Museum")).toHaveLength(1);
    const experienceAfter = await api<{ active_plan: { id: string } }>(
      request,
      `/api/v1/journeys/${journeyId}/experience`,
    );
    const planRowsAfter = await api<Array<{ id: string }>>(request, `/api/v1/journeys/${journeyId}/plans`);
    expect(experienceAfter.active_plan.id).toBe(experienceBefore.active_plan.id);
    expect(planRowsAfter.map((row) => row.id).sort()).toEqual(planRowsBefore.map((row) => row.id).sort());
  } finally {
    await Promise.all([owner.close(), collaboratorSession.close()]);
  }
});


test("R68 map URL builders encode exact WGS84 targets and reject unsupported coordinates", () => {
  const target: MemberSideQuestNavigationTarget = {
    kind: "PRIVATE_STOP",
    place_id: "place-r68-encoded",
    name: "Café & Tea 雨",
    latitude: 39.105,
    longitude: 117.19,
    coordinate_system: "WGS84",
    provenance: {
      provider_key: "fixture",
      external_id: "r68-encoded",
      source_coordinate_system: null,
    },
    navigation_available: true,
    unavailable_reason: null,
  };
  const google = new URL(buildGoogleWalkingDirectionsUrl(target));
  expect(google.searchParams.get("travelmode")).toBe("walking");
  expect(google.searchParams.get("destination")).toBe("39.105,117.19");
  expect(google.searchParams.get("dir_action")).toBe("navigate");
  // Preserve exact coordinates rather than depending on unsupported label
  // parameters or ambiguous name-based geocoding.
  expect(google.searchParams.has("destination_label")).toBe(false);
  expect(google.searchParams.has("origin")).toBe(false);
  expect(google.href).not.toContain("Caf%C3%A9");

  const osm = new URL(buildOpenStreetMapPinUrl(target));
  expect(osm.searchParams.get("mlat")).toBe("39.105");
  expect(osm.searchParams.get("mlon")).toBe("117.19");
  expect(osm.hash).toBe("#map=18/39.105/117.19");

  expect(() => buildGoogleWalkingDirectionsUrl({ ...target, coordinate_system: "GCJ-02" })).toThrow();
  expect(() => buildOpenStreetMapPinUrl({ ...target, latitude: 91 })).toThrow();
});
