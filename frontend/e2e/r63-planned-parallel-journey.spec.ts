import { expect, test, type BrowserContext, type Page, type Route } from "@playwright/test";

const JOURNEY_ID = "99999999-9999-4999-8999-999999999963";
const RENDEZVOUS_ID = "activity-r63-shared-stop";
const OWNER_TOKEN = "signed-owner-r63";
const ADMIN_TOKEN = "signed-admin-r63";
const PLAN_ID = "plan-r63-active";

type Viewer = "owner" | "admin";
type Phase = "planned-unknown" | "trusted-risk" | "intent-ended";

function operatorFor(viewer: Viewer, phase: Phase) {
  const planned = phase !== "intent-ended";
  const risk = phase === "trusted-risk";
  const ownerIsViewer = viewer === "owner";
  return {
    journey_id: JOURNEY_ID,
    state: "ACTIVE",
    headline: "The shared Journey is active.",
    enabled: true,
    autonomy: "PLAN_ONLY",
    brain: { state: "READY", configured_runtimes: [], preferred_runtime: null, recovery_resume: { pending: false, safe_to_resume: true } },
    attention: null,
    flow: {
      state: "READY_TO_BEGIN",
      current: { id: RENDEZVOUS_ID, title: "Shared rendezvous" },
      next: { id: "activity-r63-next", title: "Continue the shared Journey" },
      can_confirm: true,
    },
    group_presence: {
      state: planned
        ? risk ? "PLANNED_SPLIT_RETURN_RISK" : "PLANNED_SPLIT_RETURN_UNKNOWN"
        : "MEMBER_LOCATION_MISSING",
      authority: "MIXED_MEMBER_LOCATION_AUTHORITY",
      members: [
        {
          member_id: "member-owner-r63",
          display_name: "Alice",
          is_viewer: ownerIsViewer,
          location_state: "MISSING",
          group_state: "UNKNOWN",
          age_seconds: null,
          authority: "NO_BOUND_LOCATION",
          route_eta_minutes: risk ? 35 : null,
          route_eta_provenance: risk ? "LIVE_PROVIDER_CAPTURE" : null,
          route_eta_state: risk ? "LIVE_PROVIDER_CAPTURE" : "ROUTE_NOT_CAPTURED",
          planned_separation: planned,
          return_state: !planned ? null : risk ? "RETURN_RISK" : "RETURN_UNKNOWN",
          planned_rendezvous: planned ? {
            activity_id: RENDEZVOUS_ID,
            title: "Shared rendezvous",
            place_name: "Nara Park",
            scheduled_at: "2026-10-08T11:00:00+09:00",
          } : null,
          shared_commitment_risk: risk ? {
            state: "COMMITMENT_AT_RISK",
            next_commitment: { activity_id: RENDEZVOUS_ID, title: "Shared rendezvous", scheduled_at: "2026-10-08T11:00:00+09:00", safety_buffer_min: 10 },
            slack_after_buffer_min: -25,
            route_duration_min: 35,
          } : null,
        },
        {
          member_id: "member-admin-r63",
          display_name: "Bo",
          is_viewer: !ownerIsViewer,
          location_state: "MISSING",
          group_state: "UNKNOWN",
          age_seconds: null,
          authority: "NO_BOUND_LOCATION",
          route_eta_minutes: null,
          route_eta_provenance: null,
          route_eta_state: "ROUTE_NOT_CAPTURED",
          planned_separation: false,
          return_state: null,
          planned_rendezvous: null,
          shared_commitment_risk: null,
        },
      ],
      rendezvous: { activity_id: RENDEZVOUS_ID, title: "Shared rendezvous", place_name: "Nara Park", basis: "ACTIVE_PLAN_EXACT_PLACE" },
      rendezvous_state: "RENDEZVOUS_TARGET_READY",
      viewer_route: { eta_minutes: risk && ownerIsViewer ? 35 : null, provenance: risk && ownerIsViewer ? "LIVE_PROVIDER_CAPTURE" : null, evidence_state: risk && ownerIsViewer ? "LIVE_PROVIDER_CAPTURE" : "ROUTE_NOT_CAPTURED" },
      planned_separation: planned ? {
        state: risk ? "PLANNED_SPLIT_RETURN_RISK" : "PLANNED_SPLIT_RETURN_UNKNOWN",
        active_plan_version_id: PLAN_ID,
        rendezvous: {
          activity_id: RENDEZVOUS_ID,
          title: "Shared rendezvous",
          place_name: "Nara Park",
          scheduled_at: "2026-10-08T11:00:00+09:00",
        },
        members: [{
          display_name: "Alice",
          is_viewer: ownerIsViewer,
          planned_separation: true,
          return_state: risk ? "RETURN_RISK" : "RETURN_UNKNOWN",
          route_provenance: risk ? "LIVE_PROVIDER_CAPTURE" : null,
          rendezvous: {
            activity_id: RENDEZVOUS_ID,
            title: "Shared rendezvous",
            place_name: "Nara Park",
            scheduled_at: "2026-10-08T11:00:00+09:00",
          },
        }],
        viewer_next_action: risk && ownerIsViewer ? "RETURN_SOON" : "ROUTE_TO_RENDEZVOUS",
        shared_plan_changed: false,
      } : null,
      can_guide: true,
    },
    group_recovery: risk ? {
      state: "VERIFIED_MEMBER_RISK",
      foreground: true,
      headline: "Trusted member location and current route evidence show the shared rendezvous may be missed.",
      affected_member: {
        member_id: "member-owner-r63",
        display_name: "Alice",
        authority: "TRUSTED_MEMBER_LOCATION",
        eta_minutes: 35,
        route_provenance: "LIVE_PROVIDER_CAPTURE",
        route_evidence_state: "LIVE_PROVIDER_CAPTURE",
      },
      shared_commitment: { activity_id: RENDEZVOUS_ID, title: "Shared rendezvous", slack_after_buffer_min: -25 },
      options: [{ kind: "KEEP_PLAN_MEMBER_CATCH_UP", mutates_plan: false }, { kind: "ADAPT_REMAINING_JOURNEY", mutates_plan: true }],
      decision_authority: "COLLECTIVE_IF_PLAN_CHANGES",
      can_request_planning: true,
    } : {
      state: "INSUFFICIENT_MEMBER_TRUTH",
      foreground: false,
      headline: "There is not enough current route evidence to assess a shared recovery.",
      affected_member: null,
      shared_commitment: null,
      options: [],
      decision_authority: "COLLECTIVE_IF_PLAN_CHANGES",
      can_request_planning: false,
    },
    timeline: [],
    operator: { watching: true, will_continue_after_approval: false },
  };
}

async function prepareViewer(
  context: BrowserContext,
  page: Page,
  viewer: Viewer,
  getPhase: () => Phase,
) {
  await page.addInitScript(({ journeyId, bearer }) => {
    localStorage.setItem("citynexus.v8.journey_id", journeyId);
    localStorage.setItem("citynexus.locale", "en-US");
    sessionStorage.setItem("citynexus.traveler.bearer", bearer);
  }, { journeyId: JOURNEY_ID, bearer: viewer === "owner" ? OWNER_TOKEN : ADMIN_TOKEN });

  await context.route(/\/api\/v1\//, async (route: Route) => {
    const pathname = new URL(route.request().url()).pathname;
    const send = (json: unknown) => route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(json) });
    if (pathname.endsWith("/operator")) return send(operatorFor(viewer, getPhase()));
    if (pathname.endsWith("/experience")) {
      return send({
        journey: {
          id: JOURNEY_ID,
          status: "ACTIVE",
          city_code: "NARA",
          timezone: "Asia/Tokyo",
          title: "Shared Nara day",
          start_at: "2026-10-08T09:00:00+09:00",
          end_at: "2026-10-08T17:00:00+09:00",
          traveler_id: viewer === "owner" ? "traveler-owner-r63" : "traveler-admin-r63",
          budget: { amount_minor: 8000, currency: "JPY" },
        },
        trip: { party_size: 2 },
        options: [], offers: [], mobility_facts: [],
        active_plan: {
          id: PLAN_ID,
          status: "ACTIVE",
          activities: [{ id: RENDEZVOUS_ID, title: "Shared rendezvous", status: "IN_PROGRESS", place_id: "place-r63-rendezvous", sequence_no: 2, start_at: "2026-10-08T11:00:00+09:00", end_at: "2026-10-08T11:30:00+09:00" }],
          legs: [], disruptions: [],
        },
        experience_flags: { needs_review: false, recovery_required: false, staleness: false, feasibility_failures: [] },
      });
    }
    if (pathname.endsWith("/plans")) {
      return send([{ id: PLAN_ID, status: "ACTIVE", activities: [{ id: RENDEZVOUS_ID, title: "Shared rendezvous", status: "IN_PROGRESS", place_id: "place-r63-rendezvous", sequence_no: 2, start_at: "2026-10-08T11:00:00+09:00", end_at: "2026-10-08T11:30:00+09:00" }] }]);
    }
    if (pathname.endsWith("/twin")) return send({ journey_id: JOURNEY_ID, context: { journey_status: "ACTIVE", execution: { now_activity_id: "activity-r63-current", cursor_status: "IN_PROGRESS" } } });
    if (pathname.endsWith("/replans")) return send([]);
    if (pathname.endsWith("/guardian/pulse/latest")) return send({ pulse: null });
    if (pathname.endsWith("/guardian/autopilot/status")) return send({ enrollment: { enabled: true }, watch: null, readiness: null });
    if (pathname.endsWith("/execution-clock")) return send({ now: "2026-10-08T10:15:00+09:00", timezone: "Asia/Tokyo", current_activity_id: "activity-r63-current" });
    if (pathname.endsWith("/web-observations")) return send({ observations: [] });
    if (pathname.endsWith("/offline-snapshot")) return send({ snapshot: null });
    return send({});
  });
}

test("R63 shows a planned split without recovery, then exposes only the trusted-risk handoff", async ({ browser }) => {
  const ownerContext = await browser.newContext();
  const adminContext = await browser.newContext();
  let phase: Phase = "planned-unknown";
  try {
    const ownerPage = await ownerContext.newPage();
    const adminPage = await adminContext.newPage();
    await prepareViewer(ownerContext, ownerPage, "owner", () => phase);
    await prepareViewer(adminContext, adminPage, "admin", () => phase);
    await Promise.all([ownerPage.goto("/v8/live"), adminPage.goto("/v8/live")]);

    const ownerSplit = ownerPage.getByTestId("journey-planned-separation");
    const adminSplit = adminPage.getByTestId("journey-planned-separation");
    await expect(ownerPage.getByTestId("product-error-boundary")).toHaveCount(0);
    await expect(ownerSplit).toContainText("You’re on a planned side trip");
    await expect(ownerSplit).toContainText("Nara Park");
    await expect(ownerSplit).toContainText("Return status unknown");
    await expect(adminSplit).toContainText("Alice is on a planned side trip");
    await expect(adminSplit).toContainText("Nara Park");
    await expect(adminSplit).not.toContainText("Secret side-trip destination");
    await expect(ownerPage.getByTestId("journey-group-recovery")).toHaveCount(0);
    await expect(adminPage.getByTestId("journey-group-recovery")).toHaveCount(0);
    await expect(ownerSplit.getByTestId("journey-planned-separation-plan-unchanged")).toContainText("Update your status after rejoining.");

    phase = "trusted-risk";
    await Promise.all([ownerPage.reload(), adminPage.reload()]);
    await expect(ownerPage.getByTestId("journey-planned-separation")).toHaveAttribute("data-state", "PLANNED_SPLIT_RETURN_RISK");
    await expect(ownerPage.getByTestId("journey-planned-separation-return-state")).toContainText("Trusted current location and live route evidence");
    await expect(ownerPage.getByTestId("journey-group-recovery")).toContainText("Trusted member location and current route evidence");
    await expect(ownerPage.getByTestId("journey-group-recovery").getByTestId("journey-group-recovery-adjust")).toBeVisible();

    phase = "intent-ended";
    await Promise.all([ownerPage.reload(), adminPage.reload()]);
    await expect(ownerPage.getByTestId("journey-planned-separation")).toHaveCount(0);
    await expect(ownerPage.getByTestId("journey-group-presence")).toHaveAttribute("data-group-state", "MEMBER_LOCATION_MISSING");
    await expect(ownerPage.getByTestId("journey-group-presence")).not.toContainText("everyone is together");
  } finally {
    await ownerContext.close();
    await adminContext.close();
  }
});
