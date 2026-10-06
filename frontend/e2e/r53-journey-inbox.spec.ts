import { expect, test, type Page } from "@playwright/test";

const JOURNEY_ID = "r53-journey-inbox";

test("the running Operator accepts a pasted reservation change", async ({ page }) => {
  await page.addInitScript(() => {
    localStorage.setItem("citynexus.v8.journey_id", "r53-journey-inbox");
    localStorage.setItem("citynexus.locale", "en-US");
  });
  let submitted: unknown = null;
  await page.route(/\/api\/v1\//, async (route) => {
    const pathname = new URL(route.request().url()).pathname;
    const send = (json: unknown) => route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(json) });
    if (pathname.endsWith("/operator/inbox/intake") && route.request().method() === "POST") {
      submitted = route.request().postDataJSON();
      return send({ id: "inbox-r53", status: "APPLIED", impact: "RECOVERY_REQUIRED", provenance: "USER_PASTED_TEXT" });
    }
    if (pathname.endsWith("/operator")) return send({
      journey_id: JOURNEY_ID, state: "WATCHING", headline: "I’m watching your trip.", enabled: true,
      standing_mission_id: "standing-r53", autonomy: "EXECUTE_WITHIN_BOUNDS", incident: null, decision: null,
      approval: null, brain: { state: "READY", headline: "Ready", configured_runtimes: [], preferred_runtime: null, last_failure_reason: null, recovery_resume: { pending: false, safe_to_resume: true } },
      collective: { state: "SINGLE_TRAVELLER", mission_id: null, required_count: 0, response_count: 0, viewer_has_responded: false, members: [], options: [] },
      discovery: { state: "IDLE", attempt_count: 0, max_attempts: 0, raw_candidate_count: 0, materialized_place_count: 0 },
      inbox: { latest: null, pending_count: 0 }, intents: [], timeline: [],
    });
    if (pathname.endsWith("/experience")) return send({
      journey: { id: JOURNEY_ID, status: "ACTIVE", city_code: "CN-beijing", timezone: "Asia/Shanghai", title: "R53 Journey", start_at: "2026-10-07T00:00:00+08:00", end_at: "2026-10-08T00:00:00+08:00", traveler_id: "traveler-r53", budget: { amount_minor: 0, currency: "CNY" } },
      trip: { party_size: 1, stay_budget: { amount_minor: 0, currency: "CNY" } }, options: [], selected_option_id: null, mobility_facts: [], offers: [], active_plan: null,
      experience_flags: { needs_review: false, recovery_required: false, staleness: false, feasibility_failures: [] },
    });
    if (pathname.endsWith("/plans") || pathname.endsWith("/replans")) return send([]);
    if (pathname.endsWith("/twin")) return send({ id: "twin-r53", context: {} });
    if (pathname.endsWith("/execution-clock")) return send({ now: "2026-10-07T10:00:00+08:00", timezone: "Asia/Shanghai", current_activity_id: null });
    if (pathname.endsWith("/web-observations")) return send({ observations: [] });
    if (pathname.endsWith("/guardian/pulse/latest")) return send({ pulse: null });
    if (pathname.endsWith("/guardian/autopilot/status")) return send({ enrollment: { enabled: true }, watch: null, readiness: null });
    return send({});
  });

  await page.goto("/v8/live", { waitUntil: "domcontentloaded" });
  const input = page.getByTestId("journey-inbox-input");
  await expect(input).toBeVisible();
  await input.fill("Booking ZX42 update: departure changed from 17:40 to 18:10. Confirmation AB123.");
  await page.getByTestId("journey-inbox-submit").click();
  await expect(page.getByTestId("journey-inbox-result")).toContainText("Reservation updated");
  expect(submitted).toEqual({ source_kind: "PASTED_TEXT", text: "Booking ZX42 update: departure changed from 17:40 to 18:10. Confirmation AB123." });
});
