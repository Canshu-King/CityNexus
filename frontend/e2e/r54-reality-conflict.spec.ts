import { expect, test, type Page } from "@playwright/test";

const JOURNEY_ID = "r54-reality-conflict";
const CONFLICT_ID = "conflict-r54-generation-1";

test("the Operator asks once which conflicting train time to use", async ({ page }) => {
  await page.addInitScript(() => {
    localStorage.setItem("citynexus.v8.journey_id", "r54-reality-conflict");
    localStorage.setItem("citynexus.locale", "en-US");
  });
  let selected: unknown = null;
  let resolved = false;
  await page.route(/\/api\/v1\//, async (route) => {
    const pathname = new URL(route.request().url()).pathname;
    const send = (json: unknown) => route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(json) });
    if (pathname.endsWith(`/operator/reality-conflicts/${CONFLICT_ID}/resolve`) && route.request().method() === "POST") {
      selected = route.request().postDataJSON();
      resolved = true;
      return send({ conflict_id: CONFLICT_ID, generation: 1, status: "RESOLVED", resolution_provenance: "USER_CONFIRMED_REALITY_RESOLUTION" });
    }
    if (pathname.endsWith("/operator")) return send(operatorProjection());
    if (pathname.endsWith("/experience")) return send({
      journey: { id: JOURNEY_ID, status: "ACTIVE", city_code: "CN-beijing", timezone: "Asia/Shanghai", title: "R54 Journey", start_at: "2026-10-07T00:00:00+08:00", end_at: "2026-10-08T00:00:00+08:00", traveler_id: "traveler-r54", budget: { amount_minor: 0, currency: "CNY" } },
      trip: { party_size: 1, stay_budget: { amount_minor: 0, currency: "CNY" } }, options: [], selected_option_id: null, mobility_facts: [], offers: [], active_plan: null,
      experience_flags: { needs_review: false, recovery_required: false, staleness: false, feasibility_failures: [] },
    });
    if (pathname.endsWith("/plans") || pathname.endsWith("/replans")) return send([]);
    if (pathname.endsWith("/execution-clock")) return send({ now: "2026-10-07T10:00:00+08:00", timezone: "Asia/Shanghai", current_activity_id: null });
    if (pathname.endsWith("/web-observations")) return send({ observations: [] });
    if (pathname.endsWith("/twin")) return send({ id: "twin-r54", context: {} });
    if (pathname.endsWith("/guardian/pulse/latest")) return send({ pulse: null });
    if (pathname.endsWith("/guardian/autopilot/status")) return send({ enrollment: { enabled: true }, watch: null, readiness: null });
    return send({});
  });

  await page.goto("/v8/live", { waitUntil: "domcontentloaded" });
  const card = page.getByTestId("journey-operator-attention");
  await expect(card).toContainText("I have two different departure times for the same train");
  await expect(card).toContainText("Provider replay: 17:40");
  await expect(card).toContainText("Your forwarded update: 18:10");
  await expect(card.getByRole("button", { name: "Use 18:10" })).toBeVisible();
  await card.getByRole("button", { name: "Use 18:10" }).click();
  await expect.poll(() => selected).toEqual({ selected_claim_id: "claim-user-r54" });
  await expect(page.getByTestId("journey-operator-attention")).toHaveCount(0);

  function operatorProjection() {
    const realityConflict = resolved ? null : {
      id: CONFLICT_ID, generation: 1, status: "UNRESOLVED_MATERIAL_CONFLICT",
      title: "I have two different departure times for the same train",
      body: "I have conflicting departure times for train AB123. Provider replay: 17:40. Your forwarded update: 18:10. I’m holding off on replanning until you choose.",
      choices: [{ claim_id: "claim-user-r54", label: "Use 18:10" }, { claim_id: "claim-provider-r54", label: "Keep 17:40" }],
    };
    return {
      journey_id: JOURNEY_ID, state: "WATCHING", headline: "I’m watching your trip.", enabled: true,
      standing_mission_id: "standing-r54", autonomy: "EXECUTE_WITHIN_BOUNDS", incident: null, decision: null, approval: null,
      brain: { state: "READY", headline: "Ready", configured_runtimes: [], preferred_runtime: null, last_failure_reason: null, recovery_resume: { pending: false, safe_to_resume: true } },
      collective: { state: "SINGLE_TRAVELLER", mission_id: null, required_count: 0, response_count: 0, viewer_has_responded: false, members: [], options: [] },
      discovery: { state: "IDLE", attempt_count: 0, max_attempts: 0, raw_candidate_count: 0, materialized_place_count: 0 },
      inbox: { latest: null, pending_count: 0 }, reality_conflict: realityConflict,
      attention: resolved ? null : {
        kind: "REALITY_CONFLICT_REQUIRED", title: realityConflict!.title, body: realityConflict!.body,
        action_label: "Choose departure time", action_type: "RESOLVE_REALITY_CONFLICT", priority: 8,
        blocking: true, semantic_id: "reality-conflict:conflict-r54-generation-1:1",
        source_ref: { conflict_id: CONFLICT_ID }, options: realityConflict!.choices.map((item) => ({ value: item.claim_id, label: item.label })), pending_count: 1,
      }, intents: [], timeline: [],
    };
  }
});
