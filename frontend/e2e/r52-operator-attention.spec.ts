import { expect, test, type Page } from "@playwright/test";

const JOURNEY_ID = "r52-decision-inbox";
const intentId = "intent-r52-one-lineage";

async function seed(page: Page) {
  await page.addInitScript(() => {
    localStorage.setItem("citynexus.v8.journey_id", "r52-decision-inbox");
    localStorage.setItem("citynexus.locale", "en-US");
  });
}

test("the Operator asks one bounded question and resumes the same JourneyIntent", async ({ page }) => {
  await seed(page);
  let answered: { intentId: string; answer: string } | null = null;
  let resolved = false;
  await page.route(/\/api\/v1\//, async (route) => {
    const pathname = new URL(route.request().url()).pathname;
    const send = (json: unknown) => route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(json) });
    if (pathname.endsWith("/operator/intents/" + intentId + "/clarification") && route.request().method() === "POST") {
      const payload = route.request().postDataJSON() as { answer: string };
      answered = { intentId, answer: payload.answer };
      resolved = true;
      return send(operatorProjection());
    }
    if (pathname.endsWith("/operator")) return send(operatorProjection());
    if (pathname.endsWith("/experience")) return send({
      journey: { id: JOURNEY_ID, traveler_id: "traveler-r52", title: "Quiet Journey", city_code: "CN-beijing", timezone: "Asia/Shanghai", start_at: "2026-10-07T00:00:00Z", end_at: "2026-10-08T00:00:00Z", status: "ACTIVE", budget: { amount_minor: 0, currency: "CNY" } },
      trip: { arrival_anchor: {}, departure_anchor: {}, party_size: 1, occupancy: {}, stay_budget: { amount_minor: 0, currency: "CNY" } },
      offers: [], options: [], selected_option_id: null, mobility_facts: [], active_plan: null,
      experience_flags: { needs_review: false, recovery_required: false, staleness: false, feasibility_failures: [] },
    });
    if (pathname.endsWith("/plans")) return send([]);
    if (pathname.endsWith("/execution-clock")) return send({ now: "2026-10-07T10:00:00Z", timezone: "Asia/Shanghai", journey_status: "ACTIVE" });
    if (pathname.endsWith("/web-observations")) return send({ observations: [] });
    if (pathname.endsWith("/twin")) return send({ id: "twin-r52", context: {} });
    if (pathname.endsWith("/guardian/pulse/latest")) return send({ pulse: null });
    if (pathname.endsWith("/guardian/autopilot/status")) return send({ enrollment: { enabled: true }, watch: null, readiness: null });
    if (pathname.endsWith("/replans")) return send([]);
    return send({});
  });

  await page.goto("/v8/live", { waitUntil: "domcontentloaded" });
  const inbox = page.getByTestId("journey-operator-attention");
  await expect(inbox).toContainText("One quick question");
  await expect(inbox.getByRole("button")).toHaveCount(3);
  await inbox.getByRole("button", { name: "Less walking" }).click();
  await expect.poll(() => answered).toEqual({ intentId, answer: "LESS_WALKING" });
  await expect(page.getByTestId("journey-operator-attention")).toHaveCount(0);
  await expect(page.getByTestId("journey-operator")).toContainText("I’m watching your trip.");

  function operatorProjection() {
    return {
      journey_id: JOURNEY_ID,
      state: "WATCHING",
      headline: "I’m watching your trip.",
      enabled: true,
      standing_mission_id: "standing-r52",
      autonomy: "PLAN_ONLY",
      incident: null,
      decision: null,
      approval: null,
      brain: { state: "READY", headline: "Planning is ready.", configured_runtimes: [], preferred_runtime: null, last_failure_reason: null, recovery_resume: { pending: false, safe_to_resume: true } },
      collective: { state: "SINGLE_TRAVELLER", mission_id: null, required_count: 0, response_count: 0, viewer_has_responded: false, members: [], options: [] },
      discovery: { state: "IDLE", attempt_count: 0, max_attempts: 0, raw_candidate_count: 0, materialized_place_count: 0 },
      operations: null,
      flow: null,
      ahead: null,
      overnight: null,
      attention: resolved ? null : {
        kind: "INTENT_CLARIFICATION_REQUIRED",
        title: "One quick question",
        body: "What matters most for the rest of today?",
        action_label: "Answer",
        action_type: "ANSWER_INTENT_CLARIFICATION",
        priority: 12,
        blocking: true,
        semantic_id: "intent:" + intentId + ":clarification",
        source_ref: { intent_id: intentId },
        options: [
          { value: "SLOWER_PACE", label: "Slower pace" },
          { value: "LESS_WALKING", label: "Less walking" },
          { value: "FEWER_STOPS", label: "Fewer stops" },
        ],
        pending_count: 1,
      },
      intents: resolved ? [] : [{ id: intentId, source_text: "I'm tired. Make the rest of today easier and keep walking low.", intent_kind: "UNRESOLVED", scope_kind: "REST_OF_TODAY", status: "NEEDS_CLARIFICATION", evaluation_state: "NEEDS_CLARIFICATION", created_at: "2026-10-07T10:00:00Z" }],
      timeline: [],
      operator: { watching: true, will_continue_after_approval: false },
    };
  }
});
