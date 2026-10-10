import { test, expect } from "@playwright/test";

test("shows scoped sandbox reservation work and completion", async ({ page }) => {
  await page.route("**/api/v1/journeys/**/operator", async (route) => {
    await route.fulfill({ json: {
      journey_id: "r47-operator", state: "WAITING_FOR_APPROVAL", headline: "I found a recovery.", enabled: true,
      standing_mission_id: "standing-r47", autonomy: "EXECUTE_WITHIN_BOUNDS", incident: null, decision: null,
      approval: { required: true, approval_id: "approval-r47", status: "PENDING", action: "RECOVERY_EXECUTION", target_type: "RecoveryExecutionPlan", target_id: "plan-r47", action_label: "Approve reservation work" },
      brain: { state: "READY", headline: "Planning is available.", configured_runtimes: ["deepseek"], preferred_runtime: "deepseek", last_failure_reason: null, recovery_resume: { pending: false, safe_to_resume: true } },
      discovery: { state: "IDLE", attempt_count: 0, max_attempts: 2, raw_candidate_count: 0, materialized_place_count: 0, provider_mode: null, runtime_provenance: null, query: null },
      operations: { plan_id: "plan-r47", status: "WAITING_FOR_APPROVAL", planned_action_count: 2, completed_action_count: 0, approval_id: "approval-r47", provider_label: "LAB_SANDBOX_PROVIDER", actions: [
        { sequence_no: 1, kind: "CREATE_BOOKING", status: "PENDING", provider_label: "LAB_SANDBOX_PROVIDER", target_type: "Activity" },
        { sequence_no: 2, kind: "CANCEL_BOOKING", status: "PENDING", provider_label: "LAB_SANDBOX_PROVIDER", target_type: "Booking" },
      ] },
      collective: { state: "SINGLE_TRAVELLER", required_count: 1, response_count: 0, viewer_has_responded: false, members: [], options: [] },
      timeline: [], operator: { watching: true, will_continue_after_approval: false },
    } });
  });
  await page.route("**/api/v1/journeys/**/twin", async (route) => route.fulfill({ json: {} }));
  await page.route("**/api/v1/journeys/**/plans", async (route) => route.fulfill({ json: [] }));
  await page.route("**/api/v1/journeys/**/guardian/**", async (route) => route.fulfill({ json: {} }));
  await page.route("**/api/v1/journeys/**/replans", async (route) => route.fulfill({ json: [] }));
  await page.goto("/v8/live");
  const card = page.getByTestId("journey-operator-operations");
  await expect(card).toContainText("This recovery still needs reservation work.");
  await expect(card).toContainText("LAB_SANDBOX_PROVIDER");
  await expect(card).toContainText("0 of 2 actions complete");
  await expect(card).not.toContainText("semantic_fingerprint");
});
