import { test, expect } from "@playwright/test";

test("renders one continuous Journey strip and authenticated milestone action", async ({ page }) => {
  let flowState = "READY_TO_BEGIN";
  await page.route("**/api/v1/journeys/**/operator", async (route) => {
    await route.fulfill({ json: {
      journey_id: "r48-operator", state: "WATCHING", headline: "I’m watching your trip.", enabled: true,
      standing_mission_id: "standing-r48", autonomy: "EXECUTE_WITHIN_BOUNDS", incident: null, decision: null,
      approval: null,
      brain: { state: "READY", headline: "Planning is available.", configured_runtimes: [], preferred_runtime: null, last_failure_reason: null, recovery_resume: { pending: false, safe_to_resume: true } },
      discovery: { state: "IDLE", attempt_count: 0, max_attempts: 2, raw_candidate_count: 0, materialized_place_count: 0, provider_mode: null, runtime_provenance: null, query: null },
      operations: null,
      flow: { state: flowState, recommended_action: "CONFIRM_BEGIN", can_confirm: true, current: { id: "a1", title: "Gallery", status: "ARRIVED" }, next: { id: "a2", title: "Library", status: "NOT_STARTED" }, route: { state: "AVAILABLE", exact: true, duration_min: 12 }, readiness: { state: "READY" }, notification_key: "journey-flow:r48:a1:READY_TO_BEGIN", read_only: true },
      collective: { state: "SINGLE_TRAVELLER", required_count: 1, response_count: 0, viewer_has_responded: false, members: [], options: [] },
      timeline: [], operator: { watching: true, will_continue_after_approval: false },
    } });
  });
  await page.route("**/api/v1/journeys/**/activities/a1/begin", async (route) => {
    expect(route.request().headers()["content-type"]).toContain("application/json");
    const body = route.request().postDataJSON();
    expect(body).toEqual({ truth_kind: "OPERATOR_CONFIRMED_EXECUTION", operator_confirmed: true });
    await route.fulfill({ json: {} });
  });
  await page.route("**/api/v1/journeys/**/twin", async (route) => route.fulfill({ json: {} }));
  await page.route("**/api/v1/journeys/**/plans", async (route) => route.fulfill({ json: [] }));
  await page.route("**/api/v1/journeys/**/guardian/**", async (route) => route.fulfill({ json: {} }));
  await page.route("**/api/v1/journeys/**/replans", async (route) => route.fulfill({ json: [] }));
  await page.goto("/v8/live");
  const strip = page.getByTestId("journey-continuous-flow");
  await expect(strip).toContainText("Now: Gallery");
  await expect(strip).toContainText("Exact route found");
  await strip.getByRole("button", { name: "Start" }).click();
});
