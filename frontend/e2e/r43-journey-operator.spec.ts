import { expect, test, type Page } from "@playwright/test";

const JOURNEY_ID = "r43-journey-operator";

async function seed(page: Page) {
  await page.addInitScript(() => {
    localStorage.setItem("citynexus.v8.journey_id", "r43-journey-operator");
    localStorage.setItem("citynexus.locale", "en-US");
  });
}

async function mockApi(page: Page) {
  let enabled = false;
  await page.route(/\/api\/v1\//, async (route) => {
    const pathname = new URL(route.request().url()).pathname;
    const send = (json: unknown) => route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(json) });
    if (pathname.endsWith("/operator")) {
      return send({
        journey_id: JOURNEY_ID,
        state: enabled ? "WATCHING" : "OFF",
        headline: enabled ? "I’m watching your trip." : "Journey Operator is off.",
        enabled,
        standing_mission_id: enabled ? "mission-r43" : null,
        autonomy: enabled ? "EXECUTE_WITHIN_BOUNDS" : null,
        incident: null,
        decision: null,
        approval: null,
        timeline: enabled ? [{ at: "2026-10-06T12:00:00Z", label: "Watching your trip", kind: "operator.started" }] : [],
        operator: { watching: enabled, will_continue_after_approval: false },
      });
    }
    if (pathname.endsWith("/operator/start")) {
      enabled = true;
      return send({
        journey_id: JOURNEY_ID,
        state: "WATCHING",
        headline: "I’m watching your trip.",
        enabled: true,
        standing_mission_id: "mission-r43",
        autonomy: "EXECUTE_WITHIN_BOUNDS",
        incident: null,
        decision: null,
        approval: null,
        timeline: [{ at: "2026-10-06T12:00:00Z", label: "Watching your trip", kind: "operator.started" }],
        operator: { watching: true, will_continue_after_approval: false },
      });
    }
    if (pathname.endsWith("/experience")) return send({ journey: { id: JOURNEY_ID, status: "ACTIVE" }, active_plan: { activities: [], disruptions: [] }, experience_flags: {} });
    if (pathname.endsWith("/plans")) return send([]);
    if (pathname.endsWith("/twin")) return send({ id: "twin-r43", context: {} });
    if (pathname.endsWith("/guardian/pulse/latest")) return send({ pulse: null });
    if (pathname.endsWith("/guardian/autopilot/status")) return send({ enrollment: { enabled }, watch: null, readiness: null });
    if (pathname.endsWith("/replans")) return send([]);
    return send({});
  });
}

test("Journey Operator has a one-click care entry point", async ({ page }) => {
  await seed(page);
  await mockApi(page);
  await page.goto("/v8/live", { waitUntil: "domcontentloaded" });
  await expect(page.getByTestId("journey-operator")).toContainText("Let CityNexus take care of this trip");
  await page.getByTestId("journey-operator-start").click();
  await expect(page.getByTestId("journey-operator-state")).toContainText("Watching");
  await expect(page.getByTestId("journey-operator-timeline")).toContainText("Watching your trip");
});
