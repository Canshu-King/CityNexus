import { expect, test } from "@playwright/test";

const JOURNEY_ID = "r57-group-presence";
const TOKEN = "r57-signed-traveler-bearer";

test("shared Journey shows coarse member presence and guides only the viewer to a grounded rendezvous", async ({ page, context }) => {
  await context.grantPermissions(["geolocation"]);
  await context.setGeolocation({ latitude: 35.01, longitude: 135.01, accuracy: 18 });
  await page.addInitScript(({ journeyId, token }) => {
    localStorage.setItem("citynexus.v8.journey_id", journeyId);
    localStorage.setItem("citynexus.locale", "en-US");
    sessionStorage.setItem("citynexus.traveler.bearer", token);
  }, { journeyId: JOURNEY_ID, token: TOKEN });

  let locationAuth = "";
  let routeAuth = "";
  let routeBody: Record<string, unknown> | null = null;
  let locationBody: Record<string, unknown> | null = null;
  await page.route(/\/api\/v1\//, async (route) => {
    const request = route.request();
    const pathname = new URL(request.url()).pathname;
    const send = (json: unknown, status = 200) => route.fulfill({ status, contentType: "application/json", body: JSON.stringify(json) });

    if (pathname.endsWith("/location") && request.method() === "POST") {
      locationAuth = request.headers()["authorization"] ?? "";
      locationBody = request.postDataJSON() as Record<string, unknown>;
      return send({ id: "r57-current-sample", journey_id: JOURNEY_ID, source: "FOREGROUND_WEB", principal_bound: true }, 201);
    }
    if (pathname.endsWith("/group-presence/route") && request.method() === "POST") {
      routeAuth = request.headers()["authorization"] ?? "";
      routeBody = request.postDataJSON() as Record<string, unknown>;
      return send({
        status: "COMPLETED", outcome: "ROUTE_READY",
        target: { activity_id: "next-stop-r57", title: "Shared tea house", place_name: "Shared tea house" },
        route: { duration_min: 11, distance_m: 720, provider: "r57-ui-fixture", provenance: "TEST_FIXTURE_NOT_LIVE" },
        authority: "ADVISORY_FOREGROUND_LOCATION", plan_unchanged: true, guardian_triggered: false,
      });
    }
    if (pathname.endsWith("/operator")) return send({
      journey_id: JOURNEY_ID, state: "WATCHING", headline: "I’m watching your trip.", enabled: true,
      standing_mission_id: "mission-r57", autonomy: "EXECUTE_WITHIN_BOUNDS", incident: null, decision: null, approval: null,
      brain: { state: "READY", headline: "Ready", configured_runtimes: [], preferred_runtime: null, last_failure_reason: null, recovery_resume: { pending: false, safe_to_resume: true } },
      collective: { state: "SINGLE_TRAVELLER", mission_id: null, required_count: 0, response_count: 0, viewer_has_responded: false, members: [], options: [] },
      discovery: { state: "IDLE", attempt_count: 0, max_attempts: 0, raw_candidate_count: 0, materialized_place_count: 0 },
      flow: null, transit: null,
      group_presence: {
        state: "GROUP_SPLIT_ADVISORY", authority: "ADVISORY_FOREGROUND_WEB_NOT_DEVICE_ATTESTED",
        members: [
          { member_id: "member-self", display_name: "Alex", is_viewer: true, location_state: "RECENT", group_state: "SPLIT_FROM_GROUP", age_seconds: 12, authority: "ADVISORY_FOREGROUND_WEB", route_eta_minutes: null, route_eta_provenance: null },
          { member_id: "member-friend", display_name: "Sam", is_viewer: false, location_state: "RECENT", group_state: "SPLIT_FROM_GROUP", age_seconds: 24, authority: "ADVISORY_FOREGROUND_WEB", route_eta_minutes: null, route_eta_provenance: null },
        ],
        rendezvous: { activity_id: "next-stop-r57", title: "Shared tea house", place_name: "Shared tea house", basis: "ACTIVE_PLAN_EXACT_PLACE" },
        rendezvous_state: "RENDEZVOUS_TARGET_READY",
        viewer_route: null,
        can_guide: true,
      },
      progress: null, ahead: null, overnight: null, intents: [], attention: null,
      inbox: { latest: null, pending_count: 0 }, timeline: [], operator: { watching: true, will_continue_after_approval: true },
    });
    if (pathname.endsWith("/experience")) return send({
      journey: { id: JOURNEY_ID, status: "ACTIVE", city_code: "NARA", timezone: "Asia/Tokyo", title: "Shared day", start_at: "2026-10-07T05:00:00+09:00", end_at: "2026-10-07T14:00:00+09:00", traveler_id: "traveler-self", budget: { amount_minor: 5000, currency: "JPY" } },
      trip: { party_size: 2, arrival_anchor: null, departure_anchor: null, stay_budget: { amount_minor: 0, currency: "JPY" } },
      options: [], selected_option_id: null, mobility_facts: [], offers: [], active_plan: null,
      experience_flags: { needs_review: false, recovery_required: false, staleness: false, feasibility_failures: [] },
    });
    if (pathname.endsWith("/plans") || pathname.endsWith("/replans")) return send([]);
    if (pathname.endsWith("/twin")) return send({ id: "twin-r57", current_activity_id: "current-r57", context: { execution: { now_activity_id: "current-r57", next_activity_id: "next-stop-r57", now_state: "IN_PROGRESS", next_state: "NOT_STARTED", cursor_status: "VALID" } } });
    if (pathname.endsWith("/execution-clock")) return send({ now: "2026-10-07T06:10:00+09:00", timezone: "Asia/Tokyo", current_activity_id: "current-r57" });
    if (pathname.endsWith("/guardian/pulse/latest")) return send({ pulse: null });
    if (pathname.endsWith("/guardian/autopilot/status")) return send({ enrollment: { enabled: true }, watch: null, readiness: null });
    if (pathname.endsWith("/web-observations")) return send({ observations: [] });
    if (pathname.endsWith("/offline-snapshot")) return send({ snapshot: null });
    return send({});
  });

  await page.goto("/v8/live", { waitUntil: "domcontentloaded" });
  const card = page.getByTestId("journey-group-presence");
  await expect(card).toContainText("group may be split");
  await expect(card).toContainText("Sam: Recent · may be separated");
  await expect(card).toContainText("Rendezvous: Shared tea house");
  await expect(card).not.toContainText("35.01");
  await page.getByTestId("journey-guide-to-group").click();
  await expect.poll(() => locationAuth).toBe(`Bearer ${TOKEN}`);
  await expect.poll(() => routeAuth).toBe(`Bearer ${TOKEN}`);
  expect(locationBody).toMatchObject({ latitude: 35.01, longitude: 135.01, accuracy_m: 18 });
  expect(routeBody).toEqual({ location_observation_id: "r57-current-sample", requested_mode: "WALK" });
  await expect(page.getByTestId("journey-group-route-result")).toContainText("About 11 min");
  await expect(page.getByTestId("journey-group-route-result")).toContainText("plan unchanged");
});

test("two signed member contexts share independently and see themselves as You", async ({ browser }) => {
  const ownerToken = "r57-owner-signed-bearer";
  const adminToken = "r57-admin-signed-bearer";
  const sharedSamples: Record<string, { id: string; latitude: number; longitude: number } | undefined> = {
    owner: undefined,
    admin: undefined,
  };
  const routeCalls: Record<string, Array<{ authorization: string; body: Record<string, unknown> }>> = {
    owner: [],
    admin: [],
  };

  const makeMember = (key: "owner" | "admin", viewer: "owner" | "admin") => {
    const sample = sharedSamples[key];
    const other = sharedSamples[key === "owner" ? "admin" : "owner"];
    const split = Boolean(sample && other && Math.abs(sample.latitude - other.latitude) > 0.003);
    return {
      member_id: "member-" + key,
      display_name: key === "owner" ? "Alex" : "Sam",
      is_viewer: key === viewer,
      location_state: sample ? "RECENT" : "MISSING",
      group_state: sample && other ? (split ? "SPLIT_FROM_GROUP" : "WITH_GROUP") : "UNKNOWN",
      age_seconds: sample ? 12 : null,
      authority: sample ? "ADVISORY_FOREGROUND_WEB" : "NO_BOUND_LOCATION",
      route_eta_minutes: null,
      route_eta_provenance: null,
    };
  };

  const openMember = async (token: string, latitude: number) => {
    const context = await browser.newContext({
      permissions: ["geolocation"],
      geolocation: { latitude, longitude: 135.01, accuracy: 18 },
    });
    await context.addInitScript(({ journeyId, bearer }) => {
      localStorage.setItem("citynexus.v8.journey_id", journeyId);
      localStorage.setItem("citynexus.locale", "en-US");
      sessionStorage.setItem("citynexus.traveler.bearer", bearer);
    }, { journeyId: JOURNEY_ID, bearer: token });
    await context.route(/\/api\/v1\//, async (route) => {
      const request = route.request();
      const pathname = new URL(request.url()).pathname;
      const authorization = request.headers()["authorization"] ?? "";
      const viewer = authorization === "Bearer " + ownerToken ? "owner" : "admin";
      const send = (json: unknown, status = 200) => route.fulfill({
        status, contentType: "application/json", body: JSON.stringify(json),
      });
      if (pathname.endsWith("/location") && request.method() === "POST") {
        const body = request.postDataJSON() as { latitude: number; longitude: number };
        sharedSamples[viewer] = {
          id: "sample-" + viewer,
          latitude: body.latitude,
          longitude: body.longitude,
        };
        return send({ id: sharedSamples[viewer]?.id, journey_id: JOURNEY_ID, source: "FOREGROUND_WEB", principal_bound: true }, 201);
      }
      if (pathname.endsWith("/group-presence/route") && request.method() === "POST") {
        routeCalls[viewer].push({ authorization, body: request.postDataJSON() as Record<string, unknown> });
        return send({
          status: "COMPLETED", outcome: "ROUTE_READY",
          target: { activity_id: "next-stop-r57", title: "Shared tea house", place_name: "Shared tea house" },
          route: { duration_min: viewer === "owner" ? 11 : 16, distance_m: 720, provider: "r57-ui-fixture", provenance: "TEST_FIXTURE_NOT_LIVE" },
          authority: "ADVISORY_FOREGROUND_LOCATION", plan_unchanged: true, guardian_triggered: false,
        });
      }
      if (pathname.endsWith("/operator")) return send({
        journey_id: JOURNEY_ID, state: "WATCHING", headline: "Watching", enabled: true,
        standing_mission_id: "mission-r57", autonomy: "EXECUTE_WITHIN_BOUNDS", incident: null, decision: null, approval: null,
        brain: { state: "READY", headline: "Ready", configured_runtimes: [], preferred_runtime: null, last_failure_reason: null, recovery_resume: { pending: false, safe_to_resume: true } },
        collective: { state: "GROUP", mission_id: null, required_count: 0, response_count: 0, viewer_has_responded: false, members: [], options: [] },
        discovery: { state: "IDLE", attempt_count: 0, max_attempts: 0, raw_candidate_count: 0, materialized_place_count: 0 },
        flow: null, transit: null,
        group_presence: {
          state: !sharedSamples.owner || !sharedSamples.admin
            ? "MEMBER_LOCATION_MISSING"
            : Math.abs(sharedSamples.owner.latitude - sharedSamples.admin.latitude) > 0.003
              ? "GROUP_SPLIT_ADVISORY"
              : "TOGETHER",
          authority: "ADVISORY_FOREGROUND_WEB_NOT_DEVICE_ATTESTED",
          members: [makeMember("owner", viewer), makeMember("admin", viewer)],
          rendezvous: { activity_id: "next-stop-r57", title: "Shared tea house", place_name: "Shared tea house", basis: "ACTIVE_PLAN_EXACT_PLACE" },
          rendezvous_state: "RENDEZVOUS_TARGET_READY",
          viewer_route: null,
          can_guide: true,
        },
        progress: null, ahead: null, overnight: null, intents: [], attention: null,
        inbox: { latest: null, pending_count: 0 }, timeline: [], operator: { watching: true, will_continue_after_approval: true },
      });
      if (pathname.endsWith("/experience")) return send({
        journey: { id: JOURNEY_ID, status: "ACTIVE", city_code: "NARA", timezone: "Asia/Tokyo", title: "Shared day", start_at: "2026-10-07T05:00:00+09:00", end_at: "2026-10-07T14:00:00+09:00", traveler_id: "traveler-owner", budget: { amount_minor: 5000, currency: "JPY" } },
        trip: { party_size: 2, arrival_anchor: null, departure_anchor: null, stay_budget: { amount_minor: 0, currency: "JPY" } },
        options: [], selected_option_id: null, mobility_facts: [], offers: [], active_plan: null,
        experience_flags: { needs_review: false, recovery_required: false, staleness: false, feasibility_failures: [] },
      });
      if (pathname.endsWith("/plans") || pathname.endsWith("/replans")) return send([]);
      if (pathname.endsWith("/twin")) return send({ id: "twin-r57", current_activity_id: "current-r57", context: { execution: { now_activity_id: "current-r57", next_activity_id: "next-stop-r57", now_state: "IN_PROGRESS", next_state: "NOT_STARTED", cursor_status: "VALID" } } });
      if (pathname.endsWith("/execution-clock")) return send({ now: "2026-10-07T06:10:00+09:00", timezone: "Asia/Tokyo", current_activity_id: "current-r57" });
      if (pathname.endsWith("/guardian/pulse/latest")) return send({ pulse: null });
      if (pathname.endsWith("/guardian/autopilot/status")) return send({ enrollment: { enabled: true }, watch: null, readiness: null });
      if (pathname.endsWith("/web-observations")) return send({ observations: [] });
      if (pathname.endsWith("/offline-snapshot")) return send({ snapshot: null });
      return send({});
    });
    const page = await context.newPage();
    await page.goto("/v8/live", { waitUntil: "domcontentloaded" });
    return { context, page };
  };

  const owner = await openMember(ownerToken, 35.01);
  const admin = await openMember(adminToken, 35.08);
  const ownerCard = owner.page.getByTestId("journey-group-presence");
  const adminCard = admin.page.getByTestId("journey-group-presence");
  await expect(ownerCard).toContainText("You: No shared location");
  await expect(ownerCard).toContainText("Sam: No shared location");
  await expect(adminCard).toContainText("Alex: No shared location");
  await expect(adminCard).toContainText("You: No shared location");

  await owner.page.getByTestId("journey-guide-to-group").click();
  await expect.poll(() => routeCalls.owner.length).toBe(1);
  expect(routeCalls.owner[0]).toEqual({
    authorization: "Bearer " + ownerToken,
    body: { location_observation_id: "sample-owner", requested_mode: "WALK" },
  });
  await expect(ownerCard).toContainText("You: Recent · group proximity unknown");
  await expect(ownerCard).toContainText("Sam: No shared location");

  await admin.page.reload({ waitUntil: "domcontentloaded" });
  await expect(adminCard).toContainText("Alex: Recent · group proximity unknown");
  await expect(adminCard).toContainText("You: No shared location");
  await admin.page.getByTestId("journey-guide-to-group").click();
  await expect.poll(() => routeCalls.admin.length).toBe(1);
  expect(routeCalls.admin[0]).toEqual({
    authorization: "Bearer " + adminToken,
    body: { location_observation_id: "sample-admin", requested_mode: "WALK" },
  });
  await expect(adminCard).toContainText("You: Recent · may be separated");
  await expect(adminCard).toContainText("Alex: Recent · may be separated");

  await owner.page.reload({ waitUntil: "domcontentloaded" });
  await expect(owner.page.getByTestId("journey-group-presence")).toContainText("You: Recent · may be separated");
  expect(routeCalls.owner).toHaveLength(1);
  expect(routeCalls.admin).toHaveLength(1);
  await owner.context.close();
  await admin.context.close();
});
