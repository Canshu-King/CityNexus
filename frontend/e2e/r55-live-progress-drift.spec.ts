import { expect, test } from "@playwright/test";

const journeyId = "r55-live-progress";

test("the same live Journey shows grounded delay and protected slack", async ({ page }) => {
  await page.addInitScript(() => {
    localStorage.setItem("citynexus.v8.journey_id", "r55-live-progress");
    localStorage.setItem("citynexus.locale", "en-US");
  });
  await page.route(/\/api\/v1\//, async (route) => {
    const pathname = new URL(route.request().url()).pathname;
    const send = (json: unknown) => route.fulfill({ status:  200, contentType: "application/json", body: JSON.stringify(json) });
    if (pathname.endsWith("/operator")) return send({
      journey_id: journeyId, state: "INVESTIGATING", headline: "I found a problem but could not safely resolve it.", enabled: true,
      standing_mission_id: "mission-r55", autonomy: "PLAN_ONLY", incident: null, decision: null, approval: null,
      brain: { state: "TEMPORARILY_UNAVAILABLE", headline: "Planning AI is unavailable.", configured_runtimes: [], preferred_runtime: null, last_failure_reason: "NO_RUNTIME", recovery_resume: { pending: false, safe_to_resume: false } },
      collective: { state: "SINGLE_TRAVELLER", mission_id: null, required_count: 0, response_count: 0, viewer_has_responded: false, members: [], options: [] },
      discovery: { state: "IDLE", attempt_count: 0, max_attempts: 0, raw_candidate_count: 0, materialized_place_count: 0 },
      flow: { state: "NEXT_STOP_PREPARING", recommended_action: "KEEP_WATCHING", can_confirm: false, current: { id: "activity-b", title: "Tianjin Cultural Center", status: "ACTIVE" }, next: { id: "activity-c", title: "Tianjin Eye", status: "NOT_STARTED" } },
      progress: { state: "COMMITMENT_AT_RISK", headline: "You’re 28 minutes behind. Tianjin Cultural Center is now at risk.", drift_min: 28, material: true, basis: { activity_id: "activity-a", activity_title: "Tianjin replay anchor", milestone: "COMPLETED", planned_at: "2026-10-09T00:20:00+00:00", actual_at: "2026-10-09T00:48:00+00:00", truth_kind: "OPERATOR_CONFIRMED_EXECUTION" }, next_risk: { commitment_id: "commitment-c4", activity_id: "activity-b", activity_title: "Tianjin Cultural Center", start_at: "2026-10-09T01:00:00+00:00", slack_before_min: 29, slack_after_min: 1, safety_buffer_min: 8, route: [{ from_activity_id: "activity-a", to_activity_id: "activity-b", duration_min: 11, provenance: "CAPTURED_REPLAY", provider_snapshot_id: "r55-captured-route" }] }, read_only: true },
      ahead: { state: "FUTURE_RISK_FOUND", headline: "A protected stop is exposed by actual execution drift.", recommended_action: "PREPARE_RECOVERY", horizon: { remaining_activity_count: 2, lookahead_until: "2026-10-09T22:00:00+00:00" }, top_risk: { activity_id: "activity-b", title: "Tianjin Cultural Center", risk_kind: "EXECUTION_DRIFT_EXPOSURE", grounded: true, lead_time_minutes: 17 }, risks: [{ activity_id: "activity-b", title: "Tianjin Cultural Center", risk_kind: "EXECUTION_DRIFT_EXPOSURE", grounded: true, lead_time_minutes: 17 }] },
      overnight: null, intents: [], attention: null, inbox: { latest: null, pending_count: 0 }, timeline: [], operator: { watching: true, will_continue_after_approval: true },
    });
    if (pathname.endsWith("/experience")) return send({
      journey: { id: journeyId, status: "ACTIVE", city_code: "CN-tianjin", timezone: "Asia/Shanghai", title: "R55 Journey", start_at: "2026-10-09T08:00:00+08:00", end_at: "2026-10-10T20:00:00+08:00", traveler_id: "traveler-r55", budget: { amount_minor: 0, currency: "CNY" } },
      trip: { party_size: 1, stay_budget: { amount_minor: 0, currency: "CNY" } }, options: [], selected_option_id: null, mobility_facts: [], offers: [], active_plan: null,
      experience_flags: { needs_review: false, recovery_required: false, staleness: false, feasibility_failures: [] },
    });
    if (pathname.endsWith("/plans") || pathname.endsWith("/replans")) return send([]);
    if (pathname.endsWith("/execution-clock")) return send({ now: "2026-10-09T08:48:00+08:00", timezone: "Asia/Shanghai", current_activity_id: "activity-b" });
    if (pathname.endsWith("/web-observations")) return send({ observations: [] });
    if (pathname.endsWith("/twin")) return send({ id: "twin-r55", context: {} });
    if (pathname.endsWith("/guardian/pulse/latest")) return send({ pulse: null });
    if (pathname.endsWith("/guardian/autopilot/status")) return send({ enrollment: { enabled: true }, watch: null, readiness: null });
    return send({});
  });

  await page.goto("/v8/live", { waitUntil: "domcontentloaded" });
  await expect(page.getByTestId("journey-progress-headline")).toContainText("28 minutes behind");
  await expect(page.getByTestId("journey-progress-slack")).toContainText("1 min of remaining slack");
  await expect(page.getByTestId("journey-ahead-risk")).toContainText("Tianjin Cultural Center");
});
