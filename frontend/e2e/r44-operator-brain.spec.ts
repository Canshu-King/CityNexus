import { test, expect } from "@playwright/test";

const JOURNEY_ID = "r44-operator-brain";

test("shows a remembered recovery while the planning brain is unavailable", async ({ page }) => {
  await page.addInitScript((journeyId) => {
    localStorage.setItem("citynexus.v8.journey_id", journeyId);
  }, JOURNEY_ID);

  const projection = {
    journey_id: JOURNEY_ID,
    state: "DEGRADED",
    headline: "Journey Operator needs attention.",
    enabled: true,
    standing_mission_id: "mission-r44",
    autonomy: "EXECUTE_WITHIN_BOUNDS",
    incident: { id: "incident-r44", kind: "CLOSURE", severity: "MAJOR", activity_id: null, provenance: "PROVIDER_VERIFIED" },
    decision: null,
    approval: null,
    brain: {
      state: "TEMPORARILY_UNAVAILABLE",
      headline: "I noticed a problem. My planning AI is unavailable, so I’m holding the trip state and will retry safely.",
      configured_runtimes: ["deepseek"],
      preferred_runtime: "deepseek",
      last_failure_reason: "OPERATOR_EXTERNAL_AGENT_BLOCKED",
      recovery_resume: {
        pending: true,
        status: "PENDING",
        safe_to_resume: true,
        retry_count: 0,
        next_retry_at: "2026-10-06T14:00:00Z",
      },
    },
    timeline: [
      { at: "2026-10-06T13:00:00Z", label: "Detected: Closure", kind: "city.signal.incident.created" },
      { at: "2026-10-06T13:01:00Z", label: "CityNexus could not reach its trip Agent", kind: "operator.external_agent_blocked" },
    ],
    operator: { watching: true, will_continue_after_approval: false },
  };

  await page.route("**/api/v1/journeys/**/operator", async (route) => {
    await route.fulfill({ json: projection });
  });
  await page.route("**/api/v1/journeys/**/twin", async (route) => {
    await route.fulfill({ json: {} });
  });
  await page.route("**/api/v1/journeys/**/plans", async (route) => {
    await route.fulfill({ json: [] });
  });
  await page.route("**/api/v1/journeys/**/guardian/**", async (route) => {
    await route.fulfill({ json: {} });
  });
  await page.route("**/api/v1/journeys/**/replans", async (route) => {
    await route.fulfill({ json: [] });
  });

  await page.goto("/journey");
  await expect(page.getByTestId("journey-operator-brain")).toContainText("planning AI is unavailable");
  await expect(page.getByTestId("journey-operator-brain")).toContainText("remembered the problem");
  await expect(page.getByTestId("journey-operator-timeline")).toContainText("could not reach");
});
