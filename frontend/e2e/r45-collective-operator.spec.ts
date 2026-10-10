import { test, expect } from "@playwright/test";

test("shows viewer-specific shared-trip choices and response progress", async ({ page }) => {
  await page.addInitScript(() => localStorage.setItem("citynexus.v8.journey_id", "r45-shared"));
  await page.route("**/api/v1/journeys/**/operator", async (route) => {
    await route.fulfill({ json: {
      journey_id: "r45-shared", state: "INVESTIGATING", headline: "I noticed a change.", enabled: true,
      standing_mission_id: "standing-r45", autonomy: "EXECUTE_WITHIN_BOUNDS", incident: null, decision: null, approval: null,
      brain: { state: "READY", headline: "Planning is available.", configured_runtimes: ["deepseek"], preferred_runtime: "deepseek", last_failure_reason: null, recovery_resume: { pending: false, safe_to_resume: true } },
      collective: {
        state: "WAITING_FOR_MEMBERS", mission_id: "collective-r45", clarification_id: "clar-r45", required_count: 2, response_count: 1,
        viewer_member_id: "member-b", viewer_has_responded: false, viewer_can_respond: true,
        members: [
          { member_id: null, display_name: "Alice", role: "OWNER", responded: true, is_viewer: false },
          { member_id: "member-b", display_name: "Bob", role: "ADMIN", responded: false, is_viewer: true },
        ],
        options: [{ proposal_id: "proposal-a", label: "Keep the museum", schedule_delta_min: 10 }, { proposal_id: "proposal-b", label: "Take the garden", schedule_delta_min: 25 }],
        timeline: [{ at: "2026-10-06T13:02:00Z", label: "Alice responded", kind: "agent.collective_decision.response" }],
      },
      timeline: [{ at: "2026-10-06T13:00:00Z", label: "CityNexus found recovery options for the group", kind: "agent.collective_decision.requested" }],
      operator: { watching: true, will_continue_after_approval: false },
    } });
  });
  await page.route("**/api/v1/journeys/**/twin", async (route) => route.fulfill({ json: {} }));
  await page.route("**/api/v1/journeys/**/plans", async (route) => route.fulfill({ json: [] }));
  await page.route("**/api/v1/journeys/**/guardian/**", async (route) => route.fulfill({ json: {} }));
  await page.route("**/api/v1/journeys/**/replans", async (route) => route.fulfill({ json: [] }));
  await page.goto("/journey");
  await expect(page.getByTestId("journey-operator-collective")).toContainText("1 have responded");
  await expect(page.getByTestId("journey-operator-collective")).toContainText("Alice · answered");
  await expect(page.getByTestId("journey-operator-collective")).toContainText("Which recovery fits you?");
  await expect(page.getByTestId("journey-operator-collective")).toContainText("Keep the museum");
});
