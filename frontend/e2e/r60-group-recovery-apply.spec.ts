import { expect, test, type BrowserContext, type Page, type Route } from "@playwright/test";

const JOURNEY_ID = "99999999-9999-4999-8999-999999999960";
const OWNER_TOKEN = "signed-owner-r60";
const ADMIN_TOKEN = "signed-admin-r60";
const OLD_PLAN = "plan-r60-before";
const NEW_PLAN = "plan-r60-after";
const SELECTED = "proposal-r60-selected";
const SIBLING = "proposal-r60-sibling";

type Viewer = "owner" | "admin";
type Stage = "authorized" | "applied" | "stale" | "regrounding" | "regrounded";

function operatorFor(viewer: Viewer, stage: Stage) {
  const authorized = stage === "authorized" || stage === "applied";
  const applied = stage === "applied";
  const waiting = stage === "stale" || stage === "regrounded";
  const regrounding = stage === "regrounding";
  const regrounded = stage === "regrounded";
  const missionId = regrounding || regrounded
    ? "r61-reground-mission"
    : waiting ? "r60-fresh-round" : "r60-shared-round";
  const clarificationId = regrounded
    ? "r61-fresh-clarification"
    : waiting ? "r60-fresh-clarification" : "r60-current-clarification";
  const collectiveState = waiting
    ? "WAITING_FOR_MEMBERS"
    : applied || regrounding ? "COLLECTIVE_STALE" : "COLLECTIVE_AUTHORIZED";
  const options = regrounded
    ? [
        { proposal_id: "proposal-r61-fresh-a", label: "Current garden option", schedule_delta_min: 5 },
        { proposal_id: "proposal-r61-fresh-b", label: "Current museum option", schedule_delta_min: 15 },
      ]
    : [
        { proposal_id: waiting ? "proposal-r60-fresh-a" : SELECTED, label: "Keep the garden stop", schedule_delta_min: 5 },
        { proposal_id: waiting ? "proposal-r60-fresh-b" : SIBLING, label: "Wait together for the museum", schedule_delta_min: 15 },
      ];
  return {
    journey_id: JOURNEY_ID,
    state: "INVESTIGATING",
    headline: "A shared trip decision is needed.",
    enabled: true,
    standing_mission_id: "standing-r60",
    autonomy: "PLAN_ONLY",
    incident: null,
    decision: null,
    approval: null,
    brain: {
      state: "READY",
      headline: "Planning is available.",
      configured_runtimes: [],
      preferred_runtime: null,
      last_failure_reason: null,
      recovery_resume: { pending: false, safe_to_resume: true },
    },
    attention: null,
    collective: {
      state: collectiveState,
      mission_id: missionId,
      clarification_id: clarificationId,
      status: waiting ? "WAITING_FOR_MEMBERS" : "RESOLVED",
      required_count: 2,
      response_count: waiting ? 0 : 2,
      waiting_for_member_count: waiting ? 2 : 0,
      viewer_member_id: viewer === "owner" ? "member-owner-r60" : "member-admin-r60",
      viewer_has_responded: !waiting,
      viewer_can_respond: waiting,
      authority_receipt_id: authorized ? "receipt-r60-current" : null,
      members: [
        { member_id: "member-owner-r60", display_name: "Alice", role: "OWNER", responded: !waiting, is_viewer: viewer === "owner" },
        { member_id: "member-admin-r60", display_name: "Bo", role: "ADMIN", responded: !waiting, is_viewer: viewer === "admin" },
      ],
      options,
      selected_proposal_id: authorized ? SELECTED : null,
      timeline: [],
    },
    group_presence: {
      state: "MEMBER_LOCATION_MISSING",
      authority: "ADVISORY_FOREGROUND_WEB_NOT_DEVICE_ATTESTED",
      members: [],
      rendezvous: null,
      rendezvous_state: "RENDEZVOUS_TARGET_UNAVAILABLE",
      viewer_route: null,
      can_guide: false,
    },
    group_recovery: {
      state: applied
        ? "RECOVERY_APPLIED"
        : regrounding
          ? "RECOVERY_REGROUNDING"
          : regrounded
            ? "RECOVERY_REGROUNDED_DECISION_REQUIRED"
            : waiting ? "COLLECTIVE_WAITING_FOR_MEMBERS" : "COLLECTIVE_AUTHORIZED",
      headline: applied
        ? "The shared recovery was applied. Everyone is now following the updated Journey."
        : regrounding
          ? "CityNexus is checking the changed trip against current evidence. The Journey has not changed."
          : regrounded
            ? "A fresh grounded shared decision is waiting for current member responses."
            : waiting
              ? "A fresh shared decision is waiting for current member responses."
              : "The group agreed on this exact recovery. A traveller with Journey editing authority can apply it.",
      old_decision: regrounding || regrounded
        ? {
            clarification_id: "r60-old-clarification",
            authority_receipt_id: "r60-old-receipt",
            selected_proposal_id: "proposal-r60-dead-choice",
          }
        : undefined,
      reground_result: regrounded
        ? {
            state: "RECOVERY_REGROUNDED_DECISION_REQUIRED",
            collective_classification: "HUMAN_TRADEOFF_REQUIRED",
            current_proposal_ids: ["proposal-r61-fresh-a", "proposal-r61-fresh-b"],
            grounded_feasible_proposal_ids: ["proposal-r61-fresh-a", "proposal-r61-fresh-b"],
            current_options: [
              { proposal_id: "proposal-r61-fresh-a", status: "GROUNDED_FEASIBLE", place_names: ["Current garden option"] },
              { proposal_id: "proposal-r61-fresh-b", status: "GROUNDED_FEASIBLE", place_names: ["Current museum option"] },
            ],
            plan_unchanged: true,
          }
        : undefined,
      affected_member: { member_id: "member-admin-r60", display_name: "Bo", authority: "ADVISORY_FOREGROUND_WEB", eta_minutes: 34, route_provenance: "CAPTURED_REPLAY", route_evidence_state: "CAPTURED_REPLAY" },
      shared_commitment: { activity_id: "protected-arrival-r60", title: "Protected arrival", slack_after_buffer_min: -8 },
      options: [{ kind: "KEEP_PLAN_MEMBER_CATCH_UP", mutates_plan: false }, { kind: "ADAPT_REMAINING_JOURNEY", mutates_plan: true }],
      decision_authority: "COLLECTIVE_IF_PLAN_CHANGES",
      can_request_planning: false,
      mission: { mission_id: missionId, status: waiting ? "WAITING_FOR_MEMBERS" : applied ? "COMPLETED" : "ANSWERED" },
      collective_decision: regrounding
        ? undefined
        : {
            mission_id: missionId,
            state: applied ? "RECOVERY_APPLIED" : collectiveState,
            required_count: 2,
            response_count: waiting ? 0 : 2,
            waiting_for_member_count: waiting ? 2 : 0,
            viewer_has_responded: !waiting,
            viewer_can_apply: !waiting && !applied && viewer === "owner",
            authority_receipt_id: authorized ? "receipt-r60-current" : null,
            selected_proposal_id: authorized ? SELECTED : null,
            selected_plan_version_id: authorized ? NEW_PLAN : null,
            selected_option_label: authorized ? "Keep the garden stop" : null,
            reconsent_required: waiting,
            proposal_ids: regrounded
              ? ["proposal-r61-fresh-a", "proposal-r61-fresh-b"]
              : waiting ? ["proposal-r60-fresh-a", "proposal-r60-fresh-b"] : [SELECTED, SIBLING],
          },
      ...(applied ? {
        applied: {
          selected_proposal_id: SELECTED,
          before_plan_version_id: OLD_PLAN,
          after_plan_version_id: NEW_PLAN,
          authority_receipt_id: "receipt-r60-current",
          applied_at: "2026-10-08T10:00:00Z",
          applied_by_member_id: viewer === "owner" ? "member-owner-r60" : null,
          applied_by_role: "OWNER",
        },
      } : {}),
    },
    timeline: [],
    operator: { watching: true, will_continue_after_approval: false },
  };
}

function proposals(stage: Stage) {
  if (stage === "applied" || stage === "regrounding") return [];
  const ids = stage === "regrounded"
    ? ["proposal-r61-fresh-a", "proposal-r61-fresh-b"]
    : stage === "stale" ? ["proposal-r60-fresh-a", "proposal-r60-fresh-b"] : [SELECTED, SIBLING];
  return ids.map((id) => ({
    id,
    status: "PRESENTED",
    hard_constraints_passed: true,
    locked_commitments_preserved: true,
    diff: { added: [id] },
    explanation: { summary: "A shared recovery option." },
  }));
}

async function prepareViewer(
  context: BrowserContext,
  page: Page,
  viewer: Viewer,
  stage: () => Stage,
  handlers: { onApply?: (route: Route) => Promise<void>; observedActivePlans: string[] },
) {
  await page.addInitScript(({ journeyId, bearer }) => {
    localStorage.setItem("citynexus.v8.journey_id", journeyId);
    localStorage.setItem("citynexus.locale", "en-US");
    sessionStorage.setItem("citynexus.traveler.bearer", bearer);
  }, { journeyId: JOURNEY_ID, bearer: viewer === "owner" ? OWNER_TOKEN : ADMIN_TOKEN });
  await context.route(/\/api\/v1\//, async (route) => {
    const request = route.request();
    const pathname = new URL(request.url()).pathname;
    const current = stage();
    const send = (json: unknown, status = 200) => route.fulfill({
      status,
      contentType: "application/json",
      body: JSON.stringify(json),
    });

    if (pathname.endsWith("/group-recovery/apply") && request.method() === "POST" && handlers.onApply) {
      await handlers.onApply(route);
      return;
    }
    if (pathname.endsWith("/operator")) return send(operatorFor(viewer, current));
    if (pathname.endsWith("/experience")) {
      const activePlan = current === "applied" ? NEW_PLAN : OLD_PLAN;
      handlers.observedActivePlans.push(activePlan);
      return send({
        journey: {
          id: JOURNEY_ID,
          status: "ACTIVE",
          city_code: "NARA",
          timezone: "Asia/Tokyo",
          title: "Shared day",
          start_at: "2026-10-08T05:00:00+09:00",
          end_at: "2026-10-08T14:00:00+09:00",
          traveler_id: viewer === "owner" ? "traveler-owner-r60" : "traveler-admin-r60",
          budget: { amount_minor: 5000, currency: "JPY" },
        },
        trip: { party_size: 2, arrival_anchor: null, departure_anchor: null, stay_budget: { amount_minor: 0, currency: "JPY" } },
        options: [],
        selected_option_id: null,
        mobility_facts: [],
        offers: [],
        active_plan: { id: activePlan, status: "ACTIVE", activities: [], legs: [], disruptions: [] },
        experience_flags: { needs_review: false, recovery_required: false, staleness: false, feasibility_failures: [] },
      });
    }
    if (pathname.endsWith("/replans")) return send(proposals(current));
    if (pathname.endsWith("/plans")) return send([]);
    if (pathname.endsWith("/twin")) return send({ id: `twin-r60-${viewer}`, context: { execution: {} } });
    if (pathname.endsWith("/guardian/pulse/latest")) return send({ pulse: null });
    if (pathname.endsWith("/guardian/autopilot/status")) return send({ enrollment: { enabled: true }, watch: null, readiness: null });
    if (pathname.endsWith("/execution-clock")) return send({ now: "2026-10-08T06:10:00+09:00", timezone: "Asia/Tokyo", current_activity_id: null });
    if (pathname.endsWith("/web-observations")) return send({ observations: [] });
    if (pathname.endsWith("/offline-snapshot")) return send({ snapshot: null });
    return send({});
  });
}

test("R60 authorized member applies one selected recovery and both viewers see the same active Journey", async ({ browser }) => {
  const ownerContext = await browser.newContext();
  const adminContext = await browser.newContext();
  let currentStage: Stage = "authorized";
  let authHeader = "";
  let idempotencyKey = "";
  let requestBody = "";
  const ownerPlans: string[] = [];
  const adminPlans: string[] = [];
  try {
    const ownerPage = await ownerContext.newPage();
    const adminPage = await adminContext.newPage();
    await prepareViewer(ownerContext, ownerPage, "owner", () => currentStage, {
      observedActivePlans: ownerPlans,
      onApply: async (route) => {
        authHeader = route.request().headers()["authorization"] ?? "";
        idempotencyKey = route.request().headers()["idempotency-key"] ?? "";
        requestBody = route.request().postData() ?? "";
        currentStage = "applied";
        await route.fulfill({ json: {
          journey: { id: JOURNEY_ID, active_plan_version_id: NEW_PLAN },
          proposal: { id: SELECTED, status: "ACCEPTED" },
          collective_authority_receipt_id: "receipt-r60-current",
          group_recovery_apply: {
            result: "APPLIED",
            selected_proposal_id: SELECTED,
            authority_receipt_id: "receipt-r60-current",
            before_plan_version_id: OLD_PLAN,
            after_plan_version_id: NEW_PLAN,
            recovery_epoch_id: "epoch-r60",
            applied_at: "2026-10-08T10:00:00Z",
            journey_member_id: "member-owner-r60",
            member_role: "OWNER",
          },
        } });
      },
    });
    await prepareViewer(adminContext, adminPage, "admin", () => currentStage, { observedActivePlans: adminPlans });
    await Promise.all([ownerPage.goto("/v8/live"), adminPage.goto("/v8/live")]);

    const ownerRecovery = ownerPage.getByTestId("journey-group-recovery");
    const adminRecovery = adminPage.getByTestId("journey-group-recovery");
    await expect(ownerRecovery.getByTestId("journey-group-recovery-apply")).toBeVisible();
    await expect(adminRecovery.getByTestId("journey-group-recovery-apply")).toHaveCount(0);
    await expect(adminRecovery.getByTestId("journey-group-recovery-apply-waiting")).toBeVisible();
    await expect(ownerPage.getByTestId("live-proposal")).toHaveCount(0);
    await expect(adminPage.getByTestId("live-proposal")).toHaveCount(0);
    await expect(ownerPage.getByTestId("live-accept")).toHaveCount(0);
    await expect(adminPage.getByTestId("live-accept")).toHaveCount(0);

    await ownerRecovery.getByTestId("journey-group-recovery-apply").click();
    await expect.poll(() => authHeader).toBe(`Bearer ${OWNER_TOKEN}`);
    expect(idempotencyKey).toMatch(/^group-recovery-/);
    expect(requestBody).toBe("{}");
    await expect(ownerRecovery.getByTestId("journey-group-recovery-headline")).toContainText("shared recovery was applied");
    await expect(ownerRecovery.getByTestId("journey-group-recovery-collective-state")).toHaveCount(0);
    await expect(ownerRecovery.getByTestId("journey-group-recovery-apply")).toHaveCount(0);
    await expect(ownerPage.getByTestId("live-accept")).toHaveCount(0);

    await Promise.all([ownerPage.reload(), adminPage.reload()]);
    await expect(ownerPage.getByTestId("journey-group-recovery-headline")).toContainText("shared recovery was applied");
    await expect(adminPage.getByTestId("journey-group-recovery-headline")).toContainText("shared recovery was applied");
    expect(ownerPlans).toContain(NEW_PLAN);
    expect(adminPlans).toContain(NEW_PLAN);
    await expect(ownerPage.getByTestId("live-accept")).toHaveCount(0);
    await expect(adminPage.getByTestId("live-accept")).toHaveCount(0);
  } finally {
    await ownerContext.close();
    await adminContext.close();
  }
});

test("R60 stale consent is visibly expired and both members see one fresh round", async ({ browser }) => {
  const ownerContext = await browser.newContext();
  const adminContext = await browser.newContext();
  let currentStage: Stage = "authorized";
  let applyCount = 0;
  try {
    const ownerPage = await ownerContext.newPage();
    const adminPage = await adminContext.newPage();
    await prepareViewer(ownerContext, ownerPage, "owner", () => currentStage, {
      observedActivePlans: [],
      onApply: async (route) => {
        applyCount += 1;
        currentStage = "stale";
        await route.fulfill({
          status: 409,
          contentType: "application/json",
          body: JSON.stringify({ detail: {
            code: "COLLECTIVE_CONSENT_STALE_RECONSENT_REQUIRED",
            reconsent: { available: true, reused: false, mission_id: "r60-fresh-round", clarification_id: "r60-fresh-clarification", required_member_count: 2 },
          } }),
        });
      },
    });
    await prepareViewer(adminContext, adminPage, "admin", () => currentStage, { observedActivePlans: [] });
    await Promise.all([ownerPage.goto("/v8/live"), adminPage.goto("/v8/live")]);
    await ownerPage.getByTestId("journey-group-recovery-apply").click();
    await expect(ownerPage.getByTestId("journey-group-recovery-reconsent")).toContainText("previous shared choice expired");
    await expect(ownerPage.getByTestId("journey-operator-collective")).toContainText("0/2 have answered");
    await expect(ownerPage.locator(".journey-operator-collective-options button")).toHaveCount(2);
    await expect(ownerPage.getByTestId("journey-group-recovery-apply")).toHaveCount(0);
    await expect(ownerPage.getByTestId("live-accept")).toHaveCount(0);

    await adminPage.reload();
    await expect(adminPage.getByTestId("journey-group-recovery-reconsent")).toContainText("previous shared choice expired");
    await expect(adminPage.getByTestId("journey-operator-collective")).toContainText("0/2 have answered");
    await expect(adminPage.locator(".journey-operator-collective-options button")).toHaveCount(2);
    expect(applyCount).toBe(1);
  } finally {
    await ownerContext.close();
    await adminContext.close();
  }
});

test("R61 re-grounding remains read-only and opens one genuinely fresh room for both members", async ({ browser }) => {
  const ownerContext = await browser.newContext();
  const adminContext = await browser.newContext();
  let currentStage: Stage = "regrounding";
  const ownerPlans: string[] = [];
  const adminPlans: string[] = [];
  try {
    const ownerPage = await ownerContext.newPage();
    const adminPage = await adminContext.newPage();
    await prepareViewer(ownerContext, ownerPage, "owner", () => currentStage, {
      observedActivePlans: ownerPlans,
    });
    await prepareViewer(adminContext, adminPage, "admin", () => currentStage, {
      observedActivePlans: adminPlans,
    });
    await Promise.all([ownerPage.goto("/v8/live"), adminPage.goto("/v8/live")]);

    for (const page of [ownerPage, adminPage]) {
      const recovery = page.getByTestId("journey-group-recovery");
      await expect(recovery.getByTestId("journey-group-recovery-old-decision")).toBeVisible();
      await expect(recovery.getByTestId("journey-group-recovery-regrounding")).toContainText("cannot apply a plan");
      await expect(recovery.getByTestId("journey-group-recovery-apply")).toHaveCount(0);
      await expect(page.getByTestId("live-accept")).toHaveCount(0);
    }
    expect(ownerPlans.every((id) => id === OLD_PLAN)).toBe(true);
    expect(adminPlans.every((id) => id === OLD_PLAN)).toBe(true);

    currentStage = "regrounded";
    await Promise.all([ownerPage.reload(), adminPage.reload()]);
    for (const page of [ownerPage, adminPage]) {
      const recovery = page.getByTestId("journey-group-recovery");
      await expect(recovery.getByTestId("journey-group-recovery-old-decision")).toBeVisible();
      await expect(recovery.getByTestId("journey-group-recovery-collective-state")).toContainText("0/2");
      await expect(page.getByTestId("journey-operator-collective")).toContainText("0/2 have answered");
      const freshOptions = page.locator(".journey-operator-collective-options button");
      await expect(freshOptions).toHaveCount(2);
      await expect(freshOptions.nth(0)).toContainText("Current garden option");
      await expect(freshOptions.nth(1)).toContainText("Current museum option");
      await expect(recovery.getByTestId("journey-group-recovery-apply")).toHaveCount(0);
      await expect(page.getByTestId("live-accept")).toHaveCount(0);
    }
    expect(ownerPlans.every((id) => id === OLD_PLAN)).toBe(true);
    expect(adminPlans.every((id) => id === OLD_PLAN)).toBe(true);
  } finally {
    await ownerContext.close();
    await adminContext.close();
  }
});
