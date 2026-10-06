import { expect, test, type Page } from "@playwright/test";

const JOURNEY_ID = "r51-live-journey-intent";

async function mockApi(page: Page) {
  const requestBodies: unknown[] = [];
  let enabled = true;
  await page.route(/\/api\/v1\//, async (route) => {
    const pathname = new URL(route.request().url()).pathname;
    const send = (json: unknown) => route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(json) });
    const operator = () => ({
      journey_id: JOURNEY_ID,
      state: enabled ? "WATCHING" : "OFF",
      headline: enabled ? "I’m watching your trip." : "Journey Operator is off.",
      enabled,
      standing_mission_id: enabled ? "mission-r51" : null,
      autonomy: enabled ? "EXECUTE_WITHIN_BOUNDS" : null,
      incident: null,
      decision: null,
      approval: null,
      brain: { state: "READY", headline: "Planning is ready.", configured_runtimes: [], preferred_runtime: null, last_failure_reason: null, recovery_resume: { pending: false, safe_to_resume: false } },
      collective: { state: "SINGLE_TRAVELLER", mission_id: null, clarification_id: null, required_count: 1, response_count: 0, viewer_has_responded: false, members: [], options: [] },
      discovery: { state: "IDLE", attempt_count: 0, max_attempts: 2, raw_candidate_count: 0, materialized_place_count: 0 },
      timeline: [],
      intents: [],
      operator: { watching: enabled, will_continue_after_approval: enabled },
    });
    if (pathname.endsWith("/operator/start")) {
      enabled = true;
      return send(operator());
    }
    if (pathname.endsWith("/operator")) return send(operator());
    if (pathname.endsWith("/agent/commands") && route.request().method() === "POST") {
      requestBodies.push(route.request().postDataJSON());
      return send({ outcome: "INTENT_STEERING_NEEDS_CLARIFICATION", message: "Do you mean a slower pace, less walking, or fewer stops?", intent: null });
    }
    if (pathname.endsWith("/experience")) return send({
      journey: { id: JOURNEY_ID, status: "ACTIVE", city_code: "city-tianjin", timezone: "Asia/Shanghai", title: "A Journey", start_at: "2026-10-07T00:00:00+08:00", end_at: "2026-10-08T00:00:00+08:00", traveler_id: "traveler-r51", budget: { amount_minor: 50000, currency: "CNY" }, temporal_shape: "SINGLE_DAY" },
      trip: { party_size: 2, stay_budget: { amount_minor: 50000, currency: "CNY" } },
      options: [], selected_option_id: null, mobility_facts: [], offers: [],
      active_plan: { id: "plan-r51", version_no: 1, status: "ACTIVE", current_activity_id: null, activities: [], legs: [], disruptions: [] },
      experience_flags: { needs_review: false, recovery_required: false, staleness: false, feasibility_failures: [] },
    });
    if (pathname.endsWith("/plans")) return send([]);
    if (pathname.endsWith("/twin")) return send({ id: "twin-r51", context: {} });
    if (pathname.endsWith("/guardian/pulse/latest")) return send({ pulse: null });
    if (pathname.endsWith("/guardian/autopilot/status")) return send({ enrollment: { enabled: true }, watch: null, readiness: null });
    if (pathname.endsWith("/replans")) return send([]);
    if (pathname.endsWith("/execution-clock")) return send({ now: "2026-10-07T10:00:00+08:00", timezone: "Asia/Shanghai", current_activity_id: null });
    if (pathname.endsWith("/web-observations")) return send({ observations: [] });
    return send({});
  });
  return requestBodies;
}

test("the running Journey accepts a temporary intent and renders its clarification", async ({ page }) => {
  await page.addInitScript(() => {
    localStorage.setItem("citynexus.v8.journey_id", "r51-live-journey-intent");
    localStorage.setItem("citynexus.locale", "en-US");
  });
  const submitted = await mockApi(page);
  await page.goto("/v8/live", { waitUntil: "domcontentloaded" });
  const input = page.getByTestId("journey-intent-input");
  await expect(input).toBeVisible();
  await input.fill("I'm tired. Make the rest of today easier and keep walking low.");
  await page.getByTestId("journey-intent-submit").click();
  await expect(page.getByTestId("journey-intent-result")).toContainText("Do you mean a slower pace, less walking, or fewer stops?");
  expect(submitted).toEqual([{ command: "I'm tired. Make the rest of today easier and keep walking low.", requested_autonomy: "PLAN_ONLY" }]);
});
