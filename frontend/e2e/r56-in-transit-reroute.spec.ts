import { expect, test } from "@playwright/test";

const JOURNEY_ID = "r56-in-transit-reroute";
const TOKEN = "r56-signed-traveler-bearer-test-key";

test("EN_ROUTE traveller can recalculate from one freshly shared advisory location", async ({ page, context }) => {
  await context.grantPermissions(["geolocation"]);
  await context.setGeolocation({ latitude: 35.005, longitude: 139.005, accuracy: 20 });

  await page.addInitScript(({ journeyId, token }) => {
    localStorage.setItem("citynexus.v8.journey_id", journeyId);
    localStorage.setItem("citynexus.locale", "en-US");
    sessionStorage.setItem("citynexus.traveler.bearer", token);
  }, { journeyId: JOURNEY_ID, token: TOKEN });

  let locationAuthorization = "";
  let rerouteAuthorization = "";
  let locationBody: Record<string, unknown> | null = null;
  let rerouteBody: Record<string, unknown> | null = null;

  await page.route(/\/api\/v1\//, async (route) => {
    const request = route.request();
    const pathname = new URL(request.url()).pathname;
    const send = (json: unknown, status = 200) =>
      route.fulfill({ status, contentType: "application/json", body: JSON.stringify(json) });

    if (pathname.endsWith("/location") && request.method() === "POST") {
      locationAuthorization = request.headers()["authorization"] ?? "";
      locationBody = request.postDataJSON() as Record<string, unknown>;
      return send({
        id: "location-r56-current",
        journey_id: JOURNEY_ID,
        latitude: 35.005,
        longitude: 139.005,
        accuracy_m: 20,
        captured_at: "2026-10-07T06:10:00+08:00",
        source: "FOREGROUND_WEB",
        principal_bound: true,
      }, 201);
    }

    if (pathname.endsWith("/in-transit/reroute") && request.method() === "POST") {
      rerouteAuthorization = request.headers()["authorization"] ?? "";
      rerouteBody = request.postDataJSON() as Record<string, unknown>;
      return send({
        operation_id: "route-operation-r56",
        journey_id: JOURNEY_ID,
        fingerprint: "r56-route-fingerprint",
        reused: false,
        status: "COMPLETED",
        phase: "FINALIZING",
        outcome: "ROUTE_READY",
        terminal: true,
        retryable: false,
        origin_key: "location-observation:location-r56-current",
        target_key: "target-place-r56",
        target_activity_id: "activity-r56",
        requested_mode: "WALK",
        provider: "valhalla-http",
        provider_provenance: "LIVE_PROVIDER_CAPTURE",
        result: {
          duration_min: 9,
          distance_m: 680,
          mode: "WALK",
          provider: "valhalla-http",
          provenance: "LIVE_PROVIDER_CAPTURE",
          degraded: false,
        },
        reroute_state: "IN_TRANSIT_REROUTE_ADVISORY_READY",
        reroute_key: "reroute-key-r56",
        origin: {
          key: "location-observation:location-r56-current",
          authority: "ADVISORY_ROUTE",
          source: "FOREGROUND_WEB",
          captured_at: "2026-10-07T06:10:00+08:00",
          accuracy_m: 20,
          coordinates_exposed: false,
        },
        target: {
          activity_id: "activity-r56",
          key: "target-place-r56",
          name: "Nara Craft Museum",
        },
        current_activity_status: "EN_ROUTE",
        active_plan_version_id: "plan-r56",
        active_plan_unchanged: true,
        original_route_comparison: {
          state: "ADVISORY_DEVIATION",
          route_shape_available: true,
          distance_to_route_m: 420,
          authoritative: false,
          material: false,
        },
        commitment_risk: {
          state: "WITHIN_BUFFER",
          authority: "ADVISORY_ROUTE",
          next_commitment: {
            commitment_id: "commitment-r56",
            activity_id: "protected-r56",
            title: "Reserved dinner",
            scheduled_at: "2026-10-07T08:00:00+08:00",
            safety_buffer_min: 10,
          },
          slack_after_buffer_min: 18,
          current_leg_duration_min: 9,
          future_mobility_basis: "FROZEN_PLAN_EVIDENCE_NOT_FUTURE_LIVE_TRAFFIC",
        },
        deviation_event_id: null,
        guardian_handoff: null,
        principal_bound: true,
        provenance_statement: "FOREGROUND_WEB_IS_ADVISORY",
        location_freshness_limit_seconds: 300,
      });
    }

    if (pathname.endsWith("/operator")) {
      return send({
        journey_id: JOURNEY_ID,
        state: "WATCHING",
        headline: "I’m watching your trip.",
        enabled: true,
        standing_mission_id: "standing-r56",
        autonomy: "EXECUTE_WITHIN_BOUNDS",
        incident: null,
        decision: null,
        approval: null,
        brain: {
          state: "READY",
          headline: "Ready",
          configured_runtimes: [],
          preferred_runtime: null,
          last_failure_reason: null,
          recovery_resume: { pending: false, safe_to_resume: true },
        },
        collective: {
          state: "SINGLE_TRAVELLER",
          mission_id: null,
          required_count: 0,
          response_count: 0,
          viewer_has_responded: false,
          members: [],
          options: [],
        },
        discovery: {
          state: "IDLE",
          attempt_count: 0,
          max_attempts: 0,
          raw_candidate_count: 0,
          materialized_place_count: 0,
        },
        flow: {
          state: "EN_ROUTE",
          recommended_action: "CONTINUE",
          can_confirm: false,
          current: { id: "activity-r56", title: "Nara Craft Museum", status: "EN_ROUTE" },
          next: { id: "protected-r56", title: "Reserved dinner", status: "NOT_STARTED" },
        },
        transit: {
          state: "ADVISORY_DEVIATION",
          activity_id: "activity-r56",
          activity_title: "Nara Craft Museum",
          activity_status: "EN_ROUTE",
          location_observation_id: "older-location-r56",
          location_source: "FOREGROUND_WEB",
          location_captured_at: "2026-10-07T06:08:00+08:00",
          location_age_seconds: 120,
          location_accuracy_m: 20,
          location_fresh: true,
          route_shape_available: true,
          route_geometry: {
            basis: "ACTIVE_JOURNEY_LEG",
            provenance: "LIVE_PROVIDER_CAPTURE",
          },
          consecutive_deviation_count: 0,
          distance_to_route_m: 420,
          deviation_threshold_m: 150,
          authoritative: false,
          material: false,
          can_reroute: true,
          route_authority: "ADVISORY_ROUTE",
          reason: "FOREGROUND_LOCATION_OUTSIDE_ROUTE_CORRIDOR",
          active_plan_version_id: "plan-r56",
          read_only: true,
        },
        progress: null,
        ahead: null,
        overnight: null,
        intents: [],
        attention: null,
        inbox: { latest: null, pending_count: 0 },
        timeline: [],
        operator: { watching: true, will_continue_after_approval: true },
      });
    }

    if (pathname.endsWith("/experience")) {
      return send({
        journey: {
          id: JOURNEY_ID,
          status: "ACTIVE",
          city_code: "JP-NARA",
          timezone: "Asia/Tokyo",
          title: "R56 Journey",
          start_at: "2026-10-07T05:00:00+08:00",
          end_at: "2026-10-07T12:00:00+08:00",
          traveler_id: "traveler-r56",
          budget: { amount_minor: 0, currency: "JPY" },
        },
        trip: {
          party_size: 1,
          arrival_anchor: { at: "2026-10-07T05:00:00+08:00", location: "Nara" },
          departure_anchor: { at: "2026-10-07T12:00:00+08:00", location: "Nara" },
          stay_budget: { amount_minor: 0, currency: "JPY" },
        },
        options: [],
        selected_option_id: null,
        mobility_facts: [],
        offers: [],
        active_plan: null,
        experience_flags: {
          needs_review: false,
          recovery_required: false,
          staleness: false,
          feasibility_failures: [],
        },
      });
    }

    if (pathname.endsWith("/plans") || pathname.endsWith("/replans")) return send([]);
    if (pathname.endsWith("/execution-clock")) {
      return send({
        now: "2026-10-07T06:10:00+08:00",
        timezone: "Asia/Tokyo",
        current_activity_id: "activity-r56",
      });
    }
    if (pathname.endsWith("/web-observations")) return send({ observations: [] });
    if (pathname.endsWith("/twin")) {
      return send({
        id: "twin-r56",
        current_activity_id: "activity-r56",
        context: {
          execution: {
            now_activity_id: "activity-r56",
            next_activity_id: "protected-r56",
            now_state: "EN_ROUTE",
            next_state: "NOT_STARTED",
            cursor_status: "VALID",
          },
        },
      });
    }
    if (pathname.endsWith("/guardian/pulse/latest")) return send({ pulse: null });
    if (pathname.endsWith("/guardian/autopilot/status")) {
      return send({ enrollment: { enabled: true }, watch: null, readiness: null });
    }
    if (pathname.endsWith("/offline-snapshot")) return send({ snapshot: null });
    return send({});
  });

  await page.goto("/v8/live", { waitUntil: "domcontentloaded" });

  await expect(page.getByTestId("journey-transit-reroute")).toContainText(
    "Your browser location may be off the planned route.",
  );
  await expect(page.getByTestId("journey-transit-reroute")).toContainText(
    "advisory only",
  );

  await page.getByTestId("journey-transit-reroute-button").click();

  await expect.poll(() => locationAuthorization).toBe(`Bearer ${TOKEN}`);
  await expect.poll(() => rerouteAuthorization).toBe(`Bearer ${TOKEN}`);
  await expect.poll(() => rerouteBody).toEqual({
    location_observation_id: "location-r56-current",
  });

  expect(locationBody).toMatchObject({
    latitude: 35.005,
    longitude: 139.005,
    accuracy_m: 20,
  });

  await expect(page.getByTestId("journey-transit-reroute-result")).toContainText(
    "New route: about 9 min",
  );
  await expect(page.getByTestId("journey-transit-reroute-result")).toContainText(
    "plan unchanged",
  );
  await expect(page.getByTestId("journey-transit-commitment-risk")).toContainText(
    "18 min",
  );
});
