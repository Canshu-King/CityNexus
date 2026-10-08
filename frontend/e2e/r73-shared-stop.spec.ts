import { createHmac } from "node:crypto";
import { expect, test, type APIRequestContext, type Browser, type Page } from "@playwright/test";

const API = `http://127.0.0.1:${Number(process.env.CITYNEXUS_BACKEND_PORT ?? 8000)}`;

type Traveler = { id: string; display_name: string };
type Place = {
  id: string;
  name: string;
  category: string;
  location: { latitude: number; longitude: number };
};
type Promotion = {
  promotion_id: string;
  state: string;
  state_detail: { feasibility?: string; code?: string };
  place: { place_id: string; name: string };
  dwell_minutes: number;
  clarification_id: string;
  responses: Array<{ member_id: string; display_name: string; decision: string }>;
  tradeoff: { added_count: number; route_provider: string; route_fact_qualities: string[] } | null;
  viewer_can_decide: boolean;
  viewer_can_apply: boolean;
};

function travelerToken(travelerId: string): string {
  const secret = process.env.CITYNEXUS_TRAVELER_AUTH_SECRET;
  if (!secret || Buffer.byteLength(secret, "utf8") < 32) {
    throw new Error("R73 Playwright requires a per-run CITYNEXUS_TRAVELER_AUTH_SECRET");
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
  const body = await response.text();
  if (!response.ok()) throw new Error(`${options.method ?? "GET"} ${path} -> ${response.status()}: ${body.slice(0, 300)}`);
  return JSON.parse(body) as T;
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

function catalogInterest(category: string): "COFFEE_FOOD" | "CULTURE" | "NATURE" | null {
  const normalized = category.toLowerCase();
  if (["bakery", "cafe", "coffee", "food", "market", "restaurant"].some((word) => normalized.includes(word))) {
    return "COFFEE_FOOD";
  }
  if (["culture", "gallery", "heritage", "landmark", "library", "museum"].some((word) => normalized.includes(word))) {
    return "CULTURE";
  }
  if (["garden", "nature", "park", "river", "trail", "waterfront"].some((word) => normalized.includes(word))) {
    return "NATURE";
  }
  return null;
}

test("R73 promotes one discovered Place through signed collective consent to the shared itinerary", async ({ browser, request }) => {
  test.setTimeout(180_000);
  const resetToken = process.env.CITYNEXUS_DEMO_RESET_TOKEN;
  const fixtureToken = process.env.CITYNEXUS_R73_TEST_FIXTURE_TOKEN;
  if (!resetToken || !fixtureToken) throw new Error("R73 isolated run requires demo-reset and test-fixture tokens");

  const reset = await api<{ journey_id: string; traveler_id: string; city_code: string }>(request, "/api/v1/demo/reset", {
    method: "POST",
    headers: { "X-Demo-Reset-Token": resetToken },
  });
  const journeyId = reset.journey_id;
  const journeyPath = `/api/v1/journeys/${journeyId}`;
  const ownerId = reset.traveler_id;
  const ownerToken = travelerToken(ownerId);
  const plans = await api<Array<{ id: string }>>(request, `${journeyPath}/plans/generate`, {
    method: "POST",
    data: { candidate_count: 1 },
  });
  const planId = plans[0]?.id;
  if (!planId) throw new Error("R73 E2E could not generate a demo PlanVersion");
  await api(request, `${journeyPath}/plans/${planId}/select`, { method: "POST", token: ownerToken });
  await api(request, `${journeyPath}/start`, { method: "POST" });

  const companion = await api<Traveler>(request, "/api/v1/travelers", {
    method: "POST",
    data: { display_name: "R73 Signed Companion B", locale: "en-US", timezone: "Asia/Tokyo" },
  });
  const companionToken = travelerToken(companion.id);
  await api(request, `${journeyPath}/members`, {
    method: "POST",
    token: ownerToken,
    data: { traveler_id: companion.id, role: "COLLABORATOR", invited_by: ownerId },
  });
  await api(request, `${journeyPath}/operator/start`, {
    method: "POST",
    token: ownerToken,
    data: { interval_seconds: 3600 },
  });

  const experience = await api<{
    journey: { city_code: string };
    active_plan: { id: string; activities: Array<{ place_id: string | null }> };
  }>(request, `${journeyPath}/experience`);
  const places = await api<Place[]>(request, `/api/v1/places?city_code=${encodeURIComponent(experience.journey.city_code)}`);
  const plannedPlaceIds = new Set(experience.active_plan.activities.map((activity) => activity.place_id).filter(Boolean));
  const discoveryTarget = places.find((place) =>
    !plannedPlaceIds.has(place.id)
      && Number.isFinite(place.location?.latitude)
      && Number.isFinite(place.location?.longitude)
      && catalogInterest(place.category) !== null,
  );
  if (!discoveryTarget) throw new Error("The demo catalog needs a routable public Place outside the active plan");
  const interest = catalogInterest(discoveryTarget.category);
  if (!interest) throw new Error(`No catalog discovery interest maps to ${discoveryTarget.category}`);

  // The discovery is an authenticated foreground sample against the local City
  // Place catalog. It is test data, not device GPS or a live external search.
  const observation = await api<{ id: string }>(request, `${journeyPath}/location`, {
    method: "POST",
    token: ownerToken,
    data: {
      latitude: discoveryTarget.location.latitude,
      longitude: discoveryTarget.location.longitude,
      accuracy_m: 8,
      captured_at: new Date().toISOString(),
    },
  });
  const scout = await api<{
    scout_state: string;
    scout_context: string;
    candidates: Array<{ place_id: string; place_provenance: string }>;
    evidence_boundary: string;
  }>(request, `${journeyPath}/moment-scout`, {
    method: "POST",
    token: ownerToken,
    data: { location_observation_id: observation.id, budget_minutes: 30, interest },
  });
  expect(scout.scout_state).toBe("OPTIONS_AVAILABLE");
  expect(scout.candidates.some((candidate) => candidate.place_id === discoveryTarget.id)).toBeTruthy();
  expect(JSON.stringify(scout)).not.toContain("latitude");
  expect(JSON.stringify(scout)).not.toContain("longitude");
  expect(scout.evidence_boundary).toContain("ROUTE");
  const discovered = scout.candidates.find((candidate) => candidate.place_id === discoveryTarget.id);
  if (!discovered) throw new Error("Moment Scout did not return the selected catalog Place");

  const selected = await api<{ member_side_quest: { id: string; state: string } }>(
    request,
    `${journeyPath}/moment-scout/select`,
    {
      method: "POST",
      token: ownerToken,
      data: {
        location_observation_id: observation.id,
        budget_minutes: 30,
        interest,
        place_id: discoveryTarget.id,
        scout_context: scout.scout_context,
      },
    },
  );
  const ownerQuestId = selected.member_side_quest.id;
  expect(selected.member_side_quest.state).toBe("READY");

  // Ground the controlled time window before the invitation captures its exact
  // rendezvous snapshot; later schedule edits would correctly stale that invite.
  const fixture = await api<{
    fixture_class: string;
    route_source: string;
    active_plan_version_id: string;
    rendezvous_commitment_ref: string;
    active_member_count: number;
  }>(request, `/__test/r73/prepare/${journeyId}`, {
    method: "POST",
    data: { side_quest_id: ownerQuestId },
    headers: { "X-R73-Test-Fixture-Token": fixtureToken },
  });
  expect(fixture.fixture_class).toBe("TEST_REPLAY");
  expect(fixture.route_source).toBe("R73-TEST-REPLAY-EXPLICIT-FIXTURE");
  expect(fixture.active_member_count).toBe(2);

  const invitePreview = await api<{ audience_snapshot: string }>(
    request,
    `${journeyPath}/member-side-quests/${ownerQuestId}/place-invitation-preview`,
    { token: ownerToken },
  );
  const sent = await api<{ member_place_invitations: { sent: Array<{ invitation_id: string }> } }>(
    request,
    `${journeyPath}/member-side-quests/${ownerQuestId}/place-invitations`,
    {
      method: "POST",
      token: ownerToken,
      data: { confirm_public_place_sharing: true, audience_snapshot: invitePreview.audience_snapshot },
    },
  );
  const invitationId = sent.member_place_invitations.sent[0]?.invitation_id;
  if (!invitationId) throw new Error("R73 E2E did not create the R70 invitation");
  const invitationPath = `${journeyPath}/member-place-invitations/${invitationId}`;
  const feasibility = await api<{ state: string; feasibility_token: string }>(
    request,
    `${invitationPath}/feasibility-preview`,
    {
      method: "POST",
      token: companionToken,
      data: { consent_route_provider: true, location_observation_id: null, dwell_minutes: 30, requested_mode: "WALK" },
    },
  );
  expect(feasibility.state).toBe("UNKNOWN");
  const accepted = await api<{ member_side_quest: { id: string } }>(request, `${invitationPath}/respond`, {
    method: "POST",
    token: companionToken,
    data: {
      decision: "ACCEPT",
      confirm_exact_public_place: true,
      feasibility_token: feasibility.feasibility_token,
      acknowledge_feasibility_unknown: true,
    },
  });
  const companionQuestId = accepted.member_side_quest.id;

  const uninvolved = await api<Traveler>(request, "/api/v1/travelers", {
    method: "POST",
    data: { display_name: "R73 Signed Journey Member C", locale: "en-US", timezone: "Asia/Shanghai" },
  });
  const uninvolvedToken = travelerToken(uninvolved.id);
  await api(request, `${journeyPath}/members`, {
    method: "POST",
    token: ownerToken,
    data: { traveler_id: uninvolved.id, role: "COLLABORATOR", invited_by: ownerId },
  });
  const uninvolvedProjection = await api<{
    member_place_invitations?: { incoming?: unknown[]; joined?: unknown[] } | null;
  }>(request, `${journeyPath}/operator`, { token: uninvolvedToken });
  expect(uninvolvedProjection.member_place_invitations?.incoming ?? []).toEqual([]);
  expect(uninvolvedProjection.member_place_invitations?.joined ?? []).toEqual([]);
  expect(JSON.stringify(uninvolvedProjection)).not.toContain(discoveryTarget.name);

  const currentMembers = await api<Array<{ traveler_id: string; role: string }>>(
    request,
    `${journeyPath}/members`,
    { token: ownerToken },
  );
  expect(currentMembers.filter((member) => member.role === "OWNER")).toHaveLength(1);
  expect(currentMembers.filter((member) => member.role === "COLLABORATOR")).toHaveLength(2);

  const baseline = await api<{
    agent_run_count: number;
    provider_call_count: number;
    route_acquisition_operation_count: number;
  }>(request, `/__test/r73/evidence/${journeyId}`, {
    headers: { "X-R73-Test-Fixture-Token": fixtureToken },
  });

  const owner = await openJourneyPage(browser, journeyId, ownerToken);
  const joined = await openJourneyPage(browser, journeyId, companionToken);
  const uninvolvedPage = await openJourneyPage(browser, journeyId, uninvolvedToken);
  try {
    const ownerBoard = owner.page.getByTestId("member-place-progress-sent-invitation");
    const joinedBoard = joined.page.getByTestId("member-place-invitation-joined");
    await expect(ownerBoard).toBeVisible();
    await expect(joinedBoard).toBeVisible();
    await expect(joinedBoard).toContainText(discoveryTarget.name);
    await expect(uninvolvedPage.page.getByTestId("member-place-progress-board")).toHaveCount(0);

    const beforePromotion = await api<{ active_plan: { id: string } }>(request, `${journeyPath}/experience`);
    expect(beforePromotion.active_plan.id).toBe(fixture.active_plan_version_id);

    const offer = owner.page.getByTestId("member-place-promotion-offer");
    await expect(offer).toBeVisible();

    // A offers the exact place-scoped grant. B and C independently accept
    // with their own signed sessions; no test fixture upgrades either role.
    await offer.getByTestId("member-place-coplanning-member").selectOption({ label: companion.display_name });
    await offer.getByTestId("member-place-coplanning-offer").click();
    await joined.page.reload({ waitUntil: "domcontentloaded" });
    const bGrant = joined.page.getByTestId("member-place-coplanning-grant");
    await expect(bGrant).toContainText(discoveryTarget.name);
    await bGrant.getByTestId("member-place-coplanning-accept").click();

    await owner.page.reload({ waitUntil: "domcontentloaded" });
    const refreshedOffer = owner.page.getByTestId("member-place-promotion-offer");
    await refreshedOffer.getByTestId("member-place-coplanning-member").selectOption({ label: uninvolved.display_name });
    await refreshedOffer.getByTestId("member-place-coplanning-offer").click();
    await uninvolvedPage.page.reload({ waitUntil: "domcontentloaded" });
    const cGrant = uninvolvedPage.page.getByTestId("member-place-coplanning-grant");
    await expect(cGrant).toContainText(discoveryTarget.name);
    await cGrant.getByTestId("member-place-coplanning-accept").click();

    await owner.page.reload({ waitUntil: "domcontentloaded" });
    const readyOffer = owner.page.getByTestId("member-place-promotion-offer");
    await expect(readyOffer.getByTestId("member-place-coplanning-pending")).toHaveCount(0);
    await readyOffer.getByTestId("member-place-promotion-dwell").selectOption("30");
    const createResponsePromise = owner.page.waitForResponse((response) =>
      response.request().method() === "POST"
        && response.url().endsWith(`/member-place-invitations/${invitationId}/promotions`),
    );
    await readyOffer.getByTestId("member-place-promotion-create").click();
    const createResponse = await createResponsePromise;
    expect(createResponse.ok()).toBeTruthy();
    expect(createResponse.request().postDataJSON()).toEqual({ dwell_minutes: 30 });
    expect(createResponse.request().headers()["idempotency-key"]).toMatch(/^r73-create-/);

    const created = await createResponse.json() as {
      member_place_invitations: { promotions: Promotion[] };
    };
    expect(created.member_place_invitations.promotions).toHaveLength(1);
    const promotion = created.member_place_invitations.promotions[0];
    expect(promotion.state).toBe("WAITING_FOR_MEMBERS");
    expect(promotion.state_detail.feasibility).toBe("GROUNDED_FEASIBLE");
    expect(promotion.place.place_id).toBe(discoveryTarget.id);
    expect(promotion.dwell_minutes).toBe(30);
    expect(promotion.responses.map((item) => item.decision)).toEqual(["WAITING", "WAITING", "WAITING"]);

    await Promise.all([
      owner.page.reload({ waitUntil: "domcontentloaded" }),
      joined.page.reload({ waitUntil: "domcontentloaded" }),
      uninvolvedPage.page.reload({ waitUntil: "domcontentloaded" }),
    ]);
    await expect(owner.page.getByTestId("member-place-promotion")).toHaveAttribute("data-state", "WAITING_FOR_MEMBERS");
    await expect(joined.page.getByTestId("member-place-promotion")).toHaveAttribute("data-state", "WAITING_FOR_MEMBERS");
    await expect(uninvolvedPage.page.getByTestId("member-place-promotion")).toHaveAttribute("data-state", "WAITING_FOR_MEMBERS");

    const respond = async (page: Page) => {
      const responsePromise = page.waitForResponse((response) =>
        response.request().method() === "POST"
          && response.url().endsWith(`/member-place-promotions/${promotion.promotion_id}/respond`),
      );
      await page.getByTestId("member-place-promotion-approve").click();
      const response = await responsePromise;
      expect(response.ok()).toBeTruthy();
    };
    await respond(owner.page);
    await respond(joined.page);

    const afterAB = await api<{ active_plan: { id: string } }>(request, `${journeyPath}/experience`);
    expect(afterAB.active_plan.id).toBe(beforePromotion.active_plan.id);
    await uninvolvedPage.page.reload({ waitUntil: "domcontentloaded" });
    const blockedByC = uninvolvedPage.page.getByTestId("member-place-promotion");
    await expect(blockedByC).toHaveAttribute("data-state", "WAITING_FOR_MEMBERS");
    await expect(blockedByC.getByTestId("member-place-promotion-approve")).toBeVisible();
    const cProjection = await api<{
      member_place_invitations: { promotions: Promotion[]; incoming: unknown[] };
    }>(request, `${journeyPath}/operator`, { token: uninvolvedToken });
    const cPromotion = cProjection.member_place_invitations.promotions.find((item) => item.promotion_id === promotion.promotion_id);
    expect(cProjection.member_place_invitations.incoming).toEqual([]);
    expect(cPromotion?.responses.filter((item) => item.decision === "APPROVE")).toHaveLength(2);
    expect(cPromotion?.viewer_can_decide).toBeTruthy();

    await respond(uninvolvedPage.page);
    await owner.page.reload({ waitUntil: "domcontentloaded" });
    const authorized = owner.page.getByTestId("member-place-promotion");
    await expect(authorized).toHaveAttribute("data-state", "AUTHORIZED");
    const applyResponsePromise = owner.page.waitForResponse((response) =>
      response.request().method() === "POST"
        && response.url().endsWith(`/member-place-promotions/${promotion.promotion_id}/apply`),
    );
    await authorized.getByTestId("member-place-promotion-apply").click();
    const applyResponse = await applyResponsePromise;
    expect(applyResponse.ok()).toBeTruthy();
    expect(applyResponse.request().headers()["idempotency-key"]).toMatch(/^r73-apply-/);

    const afterApply = await api<{
      active_plan: { id: string; activities: Array<{ place_id: string | null; activity_type: string }> };
    }>(request, `${journeyPath}/experience`);
    expect(afterApply.active_plan.id).not.toBe(beforePromotion.active_plan.id);
    expect(afterApply.active_plan.activities.filter((item) => item.place_id === discoveryTarget.id)).toHaveLength(1);

    const evidence = await api<{
      fixture_class: string;
      active_plan_version_id: string;
      active_plan_status: string;
      active_plan_count: number;
      plan_ids_and_statuses: Array<{ id: string; status: string }>;
      activities: Array<{ place_id: string | null; activity_type: string }>;
      rendezvous_commitment_activity_plan_id: string | null;
      mobility_source_provider: string | null;
      mobility_fact_qualities: string[];
      agent_run_count: number;
      provider_call_count: number;
      route_acquisition_operation_count: number;
      promotions: Array<{ id: string; state: string; applied_plan_version_id: string | null }>;
    }>(request, `/__test/r73/evidence/${journeyId}`, {
      headers: { "X-R73-Test-Fixture-Token": fixtureToken },
    });
    expect(evidence.fixture_class).toBe("TEST_REPLAY");
    expect(evidence.active_plan_version_id).toBe(afterApply.active_plan.id);
    expect(evidence.active_plan_status).toBe("ACTIVE");
    expect(evidence.active_plan_count).toBe(1);
    expect(evidence.plan_ids_and_statuses.find((item) => item.id === beforePromotion.active_plan.id)?.status).toBe("SUPERSEDED");
    expect(evidence.rendezvous_commitment_activity_plan_id).toBe(afterApply.active_plan.id);
    expect(evidence.mobility_source_provider).toBe("R73-TEST-REPLAY-EXPLICIT-FIXTURE");
    expect(evidence.mobility_fact_qualities).toEqual(["EXPLICIT_FROZEN_FIXTURE"]);
    expect(evidence.agent_run_count).toBe(baseline.agent_run_count);
    expect(evidence.provider_call_count).toBe(baseline.provider_call_count);
    expect(evidence.route_acquisition_operation_count).toBe(baseline.route_acquisition_operation_count);
    expect(evidence.promotions).toHaveLength(1);
    expect(evidence.promotions[0].state).toBe("APPLIED");
    expect(evidence.promotions[0].applied_plan_version_id).toBe(afterApply.active_plan.id);

    for (const page of [owner.page, joined.page]) {
      await page.goto("/v8/trips", { waitUntil: "domcontentloaded" });
      const itinerary = page.getByTestId("trip-itinerary");
      await expect(itinerary).toBeVisible();
      await expect(itinerary.getByTestId("trip-stop").filter({ hasText: discoveryTarget.name })).toHaveCount(1);
    }
  } finally {
    await Promise.allSettled([owner.close(), joined.close(), uninvolvedPage.close()]);
  }
});
