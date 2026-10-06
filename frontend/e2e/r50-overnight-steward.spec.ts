import { test, expect } from "@playwright/test";

test("shows the prepared overnight handoff alongside Journey Ahead", async ({ page }) => {
  await page.route("**/api/v1/journeys/**/operator", async (route) => {
    await route.fulfill({ json: {
      journey_id: "r49-operator", state: "WATCHING", headline: "I’m watching your trip.", enabled: true,
      standing_mission_id: "standing-r49", autonomy: "PLAN_ONLY", incident: null, decision: null,
      approval: null,
      brain: { state: "READY", headline: "Planning is available.", configured_runtimes: [], preferred_runtime: null, last_failure_reason: null, recovery_resume: { pending: false, safe_to_resume: true } },
      discovery: { state: "IDLE", attempt_count: 0, max_attempts: 2, raw_candidate_count: 0, materialized_place_count: 0, provider_mode: null, runtime_provenance: null, query: null },
      operations: null,
      flow: { state: "IN_ACTIVITY", recommended_action: "CONTINUE", can_confirm: false, current: { id: "a1", title: "Current Gallery", status: "IN_PROGRESS" }, next: { id: "a2", title: "Next Library", status: "NOT_STARTED" }, route: { state: "AVAILABLE", exact: true, duration_min: 12 }, readiness: { state: "READY" }, notification_key: "journey-flow:r49:a1:IN_ACTIVITY", read_only: true },
      ahead: { state: "WATCHING_FUTURE", headline: "I’m watching a possible risk later in the journey.", recommended_action: "KEEP_WATCHING", horizon: { remaining_activity_count: 2, lookahead_until: "2026-10-07T15:00:00+00:00", bounded_hours: 12 }, top_risk: { activity_id: "a3", title: "Outdoor Garden", risk_kind: "FORECAST_WEATHER_EXPOSURE", lead_time_minutes: 420, grounded: true, risk_identity: "ahead:r49-a3" }, risks: [], read_only: true, predictive_only: true },
      overnight: { state: "MORNING_NEEDS_ATTENTION", local_date: "2026-10-07", next_local_date: "2026-10-08", cycle_key: "overnight:r50", read_only: true, learning_summary: { summary: "No new preference was learned from today’s eligible outcomes." }, briefing: { first_activities: [{ id: "a2", title: "Next Library", status: "NOT_STARTED", start_at: "2026-10-08T09:00:00+09:00" }], route: { state: "ROUTE_NEEDED", exact: false, duration_min: null, must_leave_by: null }, future_risk: { title: "Outdoor Garden" } } },
      collective: { state: "SINGLE_TRAVELLER", required_count: 1, response_count: 0, viewer_has_responded: false, members: [], options: [] },
      timeline: [], operator: { watching: true, will_continue_after_approval: false },
    } });
  });
  await page.route("**/api/v1/journeys/**/twin", async (route) => route.fulfill({ json: {} }));
  await page.route("**/api/v1/journeys/**/plans", async (route) => route.fulfill({ json: [] }));
  await page.route("**/api/v1/journeys/**/guardian/**", async (route) => route.fulfill({ json: {} }));
  await page.route("**/api/v1/journeys/**/replans", async (route) => route.fulfill({ json: [] }));

  await page.goto("/v8/live");
  await expect(page.getByTestId("journey-continuous-flow")).toContainText("Now: Current Gallery");
  const ahead = page.getByTestId("journey-ahead");
  await expect(ahead).toContainText("Looking ahead");
  await expect(page.getByTestId("journey-ahead-risk")).toContainText("Outdoor Garden");
  const overnight = page.getByTestId("journey-overnight");
  await expect(overnight).toContainText("Next Library");
  await expect(overnight).toContainText("Outdoor Garden");
  await expect(overnight).not.toContainText("Leave around");
});
