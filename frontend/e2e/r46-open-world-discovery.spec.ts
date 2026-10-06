import { test, expect } from "@playwright/test";

test("shows ordinary copy while CityNexus expands a narrow recovery surface", async ({ page }) => {
  await page.addInitScript(() => localStorage.setItem("citynexus.v8.journey_id", "r46-discovery"));
  await page.route("**/api/v1/journeys/**/operator", async (route) => {
    await route.fulfill({ json: {
      journey_id: "r46-discovery", state: "INVESTIGATING", headline: "I noticed a change.", enabled: true,
      standing_mission_id: "standing-r46", autonomy: "EXECUTE_WITHIN_BOUNDS", incident: null, decision: null, approval: null,
      brain: { state: "READY", headline: "Planning is available.", configured_runtimes: ["deepseek"], preferred_runtime: "deepseek", last_failure_reason: null, recovery_resume: { pending: false, safe_to_resume: true } },
      discovery: { state: "DISCOVERY_IN_PROGRESS", attempt_count: 1, max_attempts: 2, raw_candidate_count: 5, materialized_place_count: 5, provider_mode: "captured_replay", runtime_provenance: "SEALED_REAL_REPLAY", query: "an open nearby alternative" },
      collective: { state: "SINGLE_TRAVELLER", required_count: 1, response_count: 0, viewer_has_responded: false, members: [], options: [] },
      timeline: [{ at: "2026-10-06T13:00:00Z", label: "I’m looking for more recovery options nearby", kind: "agent.recovery_discovery.started" }],
      operator: { watching: true, will_continue_after_approval: false },
    } });
  });
  await page.route("**/api/v1/journeys/**/twin", async (route) => route.fulfill({ json: {} }));
  await page.route("**/api/v1/journeys/**/plans", async (route) => route.fulfill({ json: [] }));
  await page.route("**/api/v1/journeys/**/guardian/**", async (route) => route.fulfill({ json: {} }));
  await page.route("**/api/v1/journeys/**/replans", async (route) => route.fulfill({ json: [] }));
  await page.goto("/journey");
  await expect(page.getByTestId("journey-operator-discovery")).toContainText("known choices are too narrow");
  await expect(page.getByTestId("journey-operator-discovery")).toContainText("looking nearby");
});
