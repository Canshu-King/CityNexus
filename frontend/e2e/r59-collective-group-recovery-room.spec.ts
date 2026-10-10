import { expect, test, type BrowserContext, type Page } from "@playwright/test";

const JOURNEY_ID = "99999999-9999-4999-8999-999999999959";
const MISSION_ID = "r59-collective-room";
const CLARIFICATION_ID = "r59-clarification";
const GARDEN = "proposal-garden";
const MUSEUM = "proposal-museum";

function operatorFor(viewer: "owner" | "admin", authorized: boolean) {
  const ownerResponded = true;
  const adminResponded = authorized;
  const collectiveState = authorized ? "COLLECTIVE_AUTHORIZED" : "WAITING_FOR_MEMBERS";
  const collectiveRoom = {
    mission_id: MISSION_ID,
    state: collectiveState,
    required_count: 2,
    response_count: authorized ? 2 : 1,
    waiting_for_member_count: authorized ? 0 : 1,
    viewer_has_responded: viewer === "owner" || authorized,
    authority_receipt_id: authorized ? "receipt-r59-current" : null,
  };
  return {
    journey_id: JOURNEY_ID,
    state: "INVESTIGATING",
    headline: "A shared trip decision is needed.",
    enabled: true,
    standing_mission_id: "standing-r59",
    autonomy: "PLAN_ONLY",
    incident: null,
    decision: null,
    approval: null,
    brain: {
      state: "READY",
      headline: "Planning is available.",
      configured_runtimes: ["hermes"],
      preferred_runtime: "hermes",
      last_failure_reason: null,
      recovery_resume: { pending: false, safe_to_resume: true },
    },
    attention: null,
    collective: {
      state: collectiveState,
      mission_id: MISSION_ID,
      clarification_id: CLARIFICATION_ID,
      status: authorized ? "RESOLVED" : "WAITING_FOR_MEMBERS",
      required_count: 2,
      response_count: authorized ? 2 : 1,
      waiting_for_member_count: authorized ? 0 : 1,
      viewer_member_id: viewer === "owner" ? "member-owner" : "member-admin",
      viewer_has_responded: viewer === "owner" || authorized,
      viewer_can_respond: viewer === "admin" && !authorized,
      authority_receipt_id: authorized ? "receipt-r59-current" : null,
      members: [
        {
          member_id: viewer === "owner" ? "member-owner" : null,
          display_name: "Alice",
          role: "OWNER",
          responded: ownerResponded,
          is_viewer: viewer === "owner",
        },
        {
          member_id: viewer === "admin" ? "member-admin" : null,
          display_name: "Bo",
          role: "ADMIN",
          responded: adminResponded,
          is_viewer: viewer === "admin",
        },
      ],
      options: [
        { proposal_id: GARDEN, label: "Keep the garden stop", schedule_delta_min: 5 },
        { proposal_id: MUSEUM, label: "Wait together for the museum", schedule_delta_min: 15 },
      ],
      selected_proposal_id: authorized ? GARDEN : null,
      timeline: [],
    },
    group_recovery: {
      state: authorized ? "COLLECTIVE_AUTHORIZED" : "COLLECTIVE_WAITING_FOR_MEMBERS",
      headline: authorized
        ? "The server has a current authority receipt for this exact proposal; the Journey has not changed."
        : "A shared recovery choice is waiting for the travellers it affects.",
      affected_member: {
        member_id: "member-admin",
        display_name: "Bo",
        authority: "ADVISORY_FOREGROUND_WEB",
        eta_minutes: 34,
        route_provenance: "CAPTURED_REPLAY",
        route_evidence_state: "CAPTURED_REPLAY",
      },
      shared_commitment: {
        activity_id: "protected-arrival-r59",
        title: "Protected arrival",
        slack_after_buffer_min: -8,
      },
      options: [
        { kind: "KEEP_PLAN_MEMBER_CATCH_UP", mutates_plan: false },
        { kind: "ADAPT_REMAINING_JOURNEY", mutates_plan: true },
      ],
      decision_authority: "COLLECTIVE_IF_PLAN_CHANGES",
      can_request_planning: false,
      mission: { mission_id: MISSION_ID, status: authorized ? "ANSWERED" : "WAITING_FOR_MEMBERS" },
      collective_decision: collectiveRoom,
    },
    group_presence: {
      state: "MEMBER_LOCATION_MISSING",
      authority: "ADVISORY_FOREGROUND_WEB_NOT_DEVICE_ATTESTED",
      members: [
        {
          member_id: "member-owner",
          display_name: "Alice",
          is_viewer: viewer === "owner",
          location_state: "MISSING",
          group_state: "UNKNOWN",
          age_seconds: null,
          authority: "NO_BOUND_LOCATION",
          route_eta_minutes: null,
          route_eta_provenance: null,
        },
        {
          member_id: "member-admin",
          display_name: "Bo",
          is_viewer: viewer === "admin",
          location_state: "MISSING",
          group_state: "UNKNOWN",
          age_seconds: null,
          authority: "NO_BOUND_LOCATION",
          route_eta_minutes: null,
          route_eta_provenance: null,
        },
      ],
      rendezvous: null,
      rendezvous_state: "RENDEZVOUS_TARGET_UNAVAILABLE",
      viewer_route: null,
      can_guide: false,
    },
    timeline: [],
    operator: { watching: true, will_continue_after_approval: false },
  };
}

async function prepareViewer(
  context: BrowserContext,
  page: Page,
  viewer: "owner" | "admin",
  token: string,
  authorized: () => boolean,
  onSubmit?: (route: import("@playwright/test").Route) => Promise<void>,
) {
  await page.addInitScript(({ journeyId, bearer }) => {
    localStorage.setItem("citynexus.v8.journey_id", journeyId);
    localStorage.setItem("citynexus.locale", "en-US");
    sessionStorage.setItem("citynexus.traveler.bearer", bearer);
  }, { journeyId: JOURNEY_ID, bearer: token });
  await context.route(/\/api\/v1\//, async (route) => {
    const request = route.request();
    const pathname = new URL(request.url()).pathname;
    const send = (json: unknown, status = 200) => route.fulfill({
      status,
      contentType: "application/json",
      body: JSON.stringify(json),
    });

    if (pathname.endsWith("/collective-clarification/member-admin") && request.method() === "POST" && onSubmit) {
      await onSubmit(route);
      return;
    }
    if (pathname.endsWith("/operator")) return send(operatorFor(viewer, authorized()));
    if (pathname.endsWith("/experience")) return send({
      journey: {
        id: JOURNEY_ID,
        status: "ACTIVE",
        city_code: "NARA",
        timezone: "Asia/Tokyo",
        title: "Shared day",
        start_at: "2026-10-07T05:00:00+09:00",
        end_at: "2026-10-07T14:00:00+09:00",
        traveler_id: viewer === "owner" ? "traveler-owner" : "traveler-admin",
        budget: { amount_minor: 5000, currency: "JPY" },
      },
      trip: { party_size: 2, arrival_anchor: null, departure_anchor: null, stay_budget: { amount_minor: 0, currency: "JPY" } },
      options: [],
      selected_option_id: null,
      mobility_facts: [],
      offers: [],
      active_plan: null,
      experience_flags: { needs_review: false, recovery_required: false, staleness: false, feasibility_failures: [] },
    });
    if (pathname.endsWith("/plans") || pathname.endsWith("/replans")) return send([]);
    if (pathname.endsWith("/twin")) return send({ id: `twin-r59-${viewer}`, context: { execution: {} } });
    if (pathname.endsWith("/guardian/pulse/latest")) return send({ pulse: null });
    if (pathname.endsWith("/guardian/autopilot/status")) return send({ enrollment: { enabled: true }, watch: null, readiness: null });
    if (pathname.endsWith("/execution-clock")) return send({ now: "2026-10-07T06:10:00+09:00", timezone: "Asia/Tokyo", current_activity_id: null });
    if (pathname.endsWith("/web-observations")) return send({ observations: [] });
    if (pathname.endsWith("/offline-snapshot")) return send({ snapshot: null });
    return send({});
  });
}

test("R59 shared recovery is one viewer-specific room; a receipt is not a plan mutation", async ({ browser }) => {
  const ownerContext = await browser.newContext();
  const adminContext = await browser.newContext();
  try {
    const ownerPage = await ownerContext.newPage();
    const adminPage = await adminContext.newPage();
    let adminAuthorized = false;
    let submittedAuthorization = "";
    let submittedPath = "";
    await prepareViewer(ownerContext, ownerPage, "owner", "signed-owner-r59", () => false);
    await prepareViewer(adminContext, adminPage, "admin", "signed-admin-r59", () => adminAuthorized, async (route) => {
      submittedAuthorization = route.request().headers()["authorization"] ?? "";
      submittedPath = new URL(route.request().url()).pathname;
      adminAuthorized = true;
      await route.fulfill({
        json: {
          journey_id: JOURNEY_ID,
          mission_id: MISSION_ID,
          clarification_id: CLARIFICATION_ID,
          status: "RESOLVED",
          responses: {
            "member-owner": { member_id: "member-owner", proposal_id: GARDEN },
            "member-admin": { member_id: "member-admin", proposal_id: GARDEN },
          },
          baseline_preferences_unchanged: true,
          traveler_twin_unchanged: true,
          child_mission: { id: "continuation-r59" },
        },
      });
    });

    await Promise.all([ownerPage.goto("/v8/live"), adminPage.goto("/v8/live")]);
    const ownerRoom = ownerPage.getByTestId("journey-operator-collective");
    const adminRoom = adminPage.getByTestId("journey-operator-collective");
    const ownerRecovery = ownerPage.getByTestId("journey-group-recovery");
    const adminRecovery = adminPage.getByTestId("journey-group-recovery");
    await expect(ownerRecovery).toBeVisible();
    await expect(adminRecovery).toBeVisible();
    await expect(ownerRecovery).toContainText("The shared recovery choice is open: 1/2");
    await expect(adminRecovery).toContainText("The shared recovery choice is open: 1/2");
    await expect(ownerRecovery).toContainText("replay route evidence, not current live traffic");
    await expect(ownerRecovery).toContainText("Journey has not changed");
    await expect(ownerRoom).toContainText("1/2 have answered");
    await expect(adminRoom).toContainText("1/2 have answered");
    await expect(ownerRoom).toContainText("Alice · answered");
    await expect(ownerRoom).toContainText("Bo · waiting");
    await expect(adminRoom.getByRole("button", { name: /Keep the garden stop/ })).toBeVisible();
    await expect(ownerRoom.getByRole("button", { name: /Keep the garden stop/ })).toHaveCount(0);

    await adminRoom.getByRole("button", { name: /Keep the garden stop/ }).click();
    await expect.poll(() => submittedAuthorization).toBe("Bearer signed-admin-r59");
    expect(submittedPath).toContain(`/collective-clarification/member-admin`);
    await expect(adminRoom).toContainText("normal approval and acceptance boundaries still apply");
    await expect(adminRoom).not.toContainText("The shared trip is continuing");
    await expect(adminRecovery).toContainText("current authority receipt for this exact proposal");
    await expect(adminRecovery).not.toContainText("proposal has been approved or applied");
  } finally {
    await ownerContext.close();
    await adminContext.close();
  }
});
