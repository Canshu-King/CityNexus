import { expect, test, type BrowserContext, type Page, type Route } from "@playwright/test";

const JOURNEY_ID = "99999999-9999-4999-8999-999999999962";
const RENDEZVOUS_ACTIVITY_ID = "activity-r62-rendezvous";
const OWNER_TOKEN = "signed-owner-r62";
const ADMIN_TOKEN = "signed-admin-r62";
const PLAN_ID = "plan-r62-applied";

type Viewer = "owner" | "admin";
type Phase = "owner-arrived" | "closed";

function followthroughFor(viewer: Viewer, phase: Phase) {
  const closed = phase === "closed";
  const members = [
    {
      member_id: "member-owner-r62",
      display_name: "Alice",
      role: "OWNER",
      is_viewer: viewer === "owner",
      state: "REJOINED",
      confirmed_at: "2026-10-08T02:10:00Z",
    },
    {
      member_id: "member-admin-r62",
      display_name: "Bo",
      role: "ADMIN",
      is_viewer: viewer === "admin",
      state: closed ? "REJOINED" : "WAITING",
      confirmed_at: closed ? "2026-10-08T02:12:00Z" : null,
    },
  ];
  return {
    state: closed ? "RECOVERY_CLOSED" : "REJOIN_IN_PROGRESS",
    headline: closed
      ? "Everyone has confirmed arrival at the shared Journey stop. CityNexus is continuing the Journey."
      : "1 traveller(s) have arrived; waiting for the rest.",
    incident_key: "incident-r62-shared-recovery",
    applied_plan_version_id: PLAN_ID,
    applied_proposal_id: "proposal-r62-applied",
    recovery_epoch_id: "epoch-r62",
    rendezvous: {
      activity_id: RENDEZVOUS_ACTIVITY_ID,
      title: "Shared rendezvous",
      place_id: "place-r62-rendezvous",
      place_name: "Nara Park",
    },
    viewer: {
      member_id: viewer === "owner" ? "member-owner-r62" : "member-admin-r62",
      status: viewer === "owner" || closed ? "REJOINED" : "WAITING",
      next_action: closed ? "CONTINUE_WITH_GROUP" : "ARRIVE_AT_RENDEZVOUS",
    },
    members,
    required_count: 2,
    confirmed_count: closed ? 2 : 1,
    viewer_has_confirmed: viewer === "owner" || closed,
    viewer_can_confirm: viewer === "admin" && !closed,
    membership_reconfirmation_required: false,
    evidence_level: "AUTHENTICATED_ACTIVITY_EXECUTION_TRUTH",
    physical_presence_verified: false,
    plan_unchanged_by_closure: closed,
    closed_at: closed ? "2026-10-08T02:12:01Z" : null,
  };
}

function operatorFor(viewer: Viewer, phase: Phase) {
  const closed = phase === "closed";
  return {
    journey_id: JOURNEY_ID,
    state: closed ? "ACTIVE" : "REJOIN_IN_PROGRESS",
    headline: "CityNexus is continuing the shared Journey.",
    enabled: true,
    autonomy: "PLAN_ONLY",
    brain: { state: "READY", configured_runtimes: [], preferred_runtime: null, recovery_resume: { pending: false, safe_to_resume: true } },
    attention: null,
    flow: {
      state: "READY_TO_BEGIN",
      current: { id: RENDEZVOUS_ACTIVITY_ID, title: "Shared rendezvous" },
      next: { id: "activity-r62-next", title: "Continue the Nara visit" },
      can_confirm: true,
    },
    group_presence: {
      state: "MEMBER_LOCATION_MISSING",
      authority: "ADVISORY_FOREGROUND_WEB_NOT_DEVICE_ATTESTED",
      members: [],
      rendezvous: null,
      viewer_route: null,
      can_guide: false,
    },
    group_recovery: {
      state: closed ? "RECOVERY_CLOSED" : "REJOIN_IN_PROGRESS",
      foreground: !closed,
      headline: closed
        ? "Everyone has rejoined. CityNexus is continuing the Journey."
        : "The shared recovery is active. Rejoining the group.",
      incident_key: "incident-r62-shared-recovery",
      applied: {
        selected_proposal_id: "proposal-r62-applied",
        before_plan_version_id: "plan-r62-before",
        after_plan_version_id: PLAN_ID,
        authority_receipt_id: "receipt-r62",
        applied_at: "2026-10-08T02:00:00Z",
        applied_by_member_id: "member-owner-r62",
        applied_by_role: "OWNER",
      },
      options: [],
      decision_authority: "COLLECTIVE_IF_PLAN_CHANGES",
      can_request_planning: false,
      followthrough: followthroughFor(viewer, phase),
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
  arrivals: { requests: Array<{ authorization: string; url: string; body: string }> },
) {
  await page.addInitScript(({ journeyId, bearer }) => {
    localStorage.setItem("citynexus.v8.journey_id", journeyId);
    localStorage.setItem("citynexus.locale", "en-US");
    sessionStorage.setItem("citynexus.traveler.bearer", bearer);
  }, { journeyId: JOURNEY_ID, bearer: viewer === "owner" ? OWNER_TOKEN : ADMIN_TOKEN });

  await context.route(/\/api\/v1\//, async (route: Route) => {
    const request = route.request();
    const pathname = new URL(request.url()).pathname;
    const phase = getPhase();
    const send = (json: unknown) => route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(json),
    });

    if (pathname.endsWith(`/activities/${RENDEZVOUS_ACTIVITY_ID}/arrive`) && request.method() === "POST") {
      arrivals.requests.push({
        authorization: request.headers().authorization ?? "",
        url: pathname,
        body: request.postData() ?? "",
      });
      return send({ journey_id: JOURNEY_ID, active_plan_version_id: PLAN_ID, execution: { state: "ARRIVED" } });
    }
    if (pathname.endsWith("/operator")) return send(operatorFor(viewer, phase));
    if (pathname.endsWith("/experience")) {
      return send({
        journey: {
          id: JOURNEY_ID,
          status: "ACTIVE",
          city_code: "NARA",
          timezone: "Asia/Tokyo",
          title: "Shared Nara day",
          start_at: "2026-10-08T10:00:00+09:00",
          end_at: "2026-10-08T17:00:00+09:00",
          traveler_id: viewer === "owner" ? "traveler-owner-r62" : "traveler-admin-r62",
          budget: { amount_minor: 8000, currency: "JPY" },
        },
        trip: { party_size: 2 },
        options: [],
        mobility_facts: [],
        offers: [],
        active_plan: {
          id: PLAN_ID,
          status: "ACTIVE",
          activities: [{ id: RENDEZVOUS_ACTIVITY_ID, title: "Shared rendezvous", status: "IN_PROGRESS", place_id: "place-r62-rendezvous", sequence_no: 1, start_at: "2026-10-08T10:00:00+09:00", end_at: "2026-10-08T10:45:00+09:00" }],
          legs: [],
          disruptions: [],
        },
        experience_flags: { needs_review: false, recovery_required: false, staleness: false, feasibility_failures: [] },
      });
    }
    if (pathname.endsWith("/plans")) {
      return send([{ id: PLAN_ID, status: "ACTIVE", activities: [{ id: RENDEZVOUS_ACTIVITY_ID, title: "Shared rendezvous", status: "IN_PROGRESS", place_id: "place-r62-rendezvous", sequence_no: 1, start_at: "2026-10-08T10:00:00+09:00", end_at: "2026-10-08T10:45:00+09:00" }] }]);
    }
    if (pathname.endsWith("/twin")) return send({ journey_id: JOURNEY_ID, context: { journey_status: "ACTIVE", execution: { now_activity_id: RENDEZVOUS_ACTIVITY_ID, cursor_status: "IN_PROGRESS" } } });
    if (pathname.endsWith("/replans")) return send([]);
    if (pathname.endsWith("/guardian/pulse/latest")) return send({ pulse: null });
    if (pathname.endsWith("/guardian/autopilot/status")) return send({ enrollment: { enabled: true }, watch: null, readiness: null });
    if (pathname.endsWith("/execution-clock")) return send({ now: "2026-10-08T11:12:00+09:00", timezone: "Asia/Tokyo", current_activity_id: RENDEZVOUS_ACTIVITY_ID });
    if (pathname.endsWith("/web-observations")) return send({ observations: [] });
    if (pathname.endsWith("/offline-snapshot")) return send({ snapshot: null });
    return send({});
  });
}

test("R62 shows member-specific progress, records self arrival through Journey execution, then retires recovery controls", async ({ browser }) => {
  const ownerContext = await browser.newContext();
  const adminContext = await browser.newContext();
  let phase: Phase = "owner-arrived";
  const arrivals = { requests: [] as Array<{ authorization: string; url: string; body: string }> };
  try {
    const ownerPage = await ownerContext.newPage();
    const adminPage = await adminContext.newPage();
    await prepareViewer(ownerContext, ownerPage, "owner", () => phase, arrivals);
    await prepareViewer(adminContext, adminPage, "admin", () => phase, arrivals);
    await Promise.all([ownerPage.goto("/v8/live"), adminPage.goto("/v8/live")]);

    await expect(ownerPage.getByTestId("product-error-boundary")).toHaveCount(0);

    const ownerRecovery = ownerPage.getByTestId("journey-group-recovery");
    const adminRecovery = adminPage.getByTestId("journey-group-recovery");
    await expect(ownerRecovery.getByTestId("group-recovery-progress-count")).toContainText("1/2");
    await expect(ownerRecovery.getByTestId("group-recovery-member-progress").first()).toContainText("You: confirmed rejoining");
    await expect(ownerRecovery.getByTestId("group-recovery-confirm-rejoin")).toHaveCount(0);
    await expect(adminRecovery.getByTestId("group-recovery-progress-count")).toContainText("1/2");
    await expect(adminRecovery.getByTestId("group-recovery-member-progress").last()).toContainText("You: waiting for your confirmation");
    await expect(adminRecovery.getByTestId("group-recovery-confirm-rejoin")).toBeVisible();

    await adminRecovery.getByTestId("group-recovery-confirm-rejoin").click();
    await expect.poll(() => arrivals.requests).toHaveLength(1);
    expect(arrivals.requests[0].authorization).toBe(`Bearer ${ADMIN_TOKEN}`);
    expect(arrivals.requests[0].url).toBe(`/api/v1/journeys/${JOURNEY_ID}/activities/${RENDEZVOUS_ACTIVITY_ID}/arrive`);
    expect(JSON.parse(arrivals.requests[0].body)).toMatchObject({
      truth_kind: "OPERATOR_CONFIRMED_EXECUTION",
      operator_confirmed: true,
    });

    phase = "closed";
    await Promise.all([ownerPage.reload(), adminPage.reload()]);
    for (const page of [ownerPage, adminPage]) {
      // Closure remains in the server read model, but the old recovery room no
      // longer owns the foreground. Normal Journey execution is primary again.
      await expect(page.getByTestId("journey-group-recovery")).toHaveCount(0);
      await expect(page.getByTestId("journey-continuous-flow")).toContainText("Now: Shared rendezvous");
    }
  } finally {
    await ownerContext.close();
    await adminContext.close();
  }
});
