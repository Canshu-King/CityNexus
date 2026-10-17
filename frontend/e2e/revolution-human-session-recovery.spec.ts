import { expect, test, type Route } from "@playwright/test";

const oldJourneyId = "00000000-0000-4000-8000-000000000117";
const newJourneyId = "00000000-0000-4000-8000-000000000118";

async function json(route: Route, status: number, body: unknown) {
  await route.fulfill({
    status,
    contentType: "application/json",
    body: JSON.stringify(body),
  });
}

/**
 * HUMAN-FIRST REPRO: these are explicit simulated API failures, NOT proof of
 * live provider / model / signed database. Their only goal is preventing the
 * 403 -> reload same Journey -> 403 trap and partial credential replacement.
 */
test.describe("Revolution signed-session recovery UI regression", () => {
  test.use({ viewport: { width: 390, height: 844 }, hasTouch: true });

  test("a stale Journey's 403 offers one-tap restart without deleting its server record", async ({ page }) => {
    await page.addInitScript(({ id }) => {
      sessionStorage.setItem("citynexus.traveler.bearer", "STALE_SIGNED_FIXTURE");
      localStorage.setItem("citynexus.revolution.firstlook.journey", JSON.stringify({
        id, cityCode: "CN-RV-OLD", cityName: "连城", status: "DRAFT",
      }));
    }, { id: oldJourneyId });
    await page.route("**/api/v1/agent/runtime-status", (r) => json(r, 200, {
      runtime_identity: "UNAVAILABLE",
      hermes_compat_configured: false,
      ai_state: "DISABLED",
    }));
    let publicProviderRequests = 0;
    page.on("request", (request) => {
      if (/bootstrap-city-search|\/trial-ai-discovery|\/bootstrap-discovery$/.test(request.url())
          && request.method() === "POST") publicProviderRequests += 1;
    });
    await page.route(`**/api/v1/journeys/${oldJourneyId}/bootstrap-discovery/readiness`,
      (r) => json(r, 403, { detail: "JOURNEY_MEMBER_REQUIRED" }));
    await page.route(`**/api/v1/journeys/${oldJourneyId}/bootstrap-shortlist`,
      (r) => json(r, 403, { detail: "JOURNEY_MEMBER_REQUIRED" }));

    await page.goto("/revolution");
    await expect(page.getByRole("button", { name: "重新开始探索" }).first()).toBeVisible();
    await page.getByRole("button", { name: "重新开始探索" }).first().click();
    await expect(page.getByTestId("rev-mobile-welcome")).toBeVisible();
    await expect(page.getByTestId("rev-firstlook-city")).toHaveValue("连城");
    await expect(page.getByRole("alert")).toContainText("这次登录无法访问之前的行程");
    const oldState = await page.evaluate(() => ({
      pointer: localStorage.getItem("citynexus.revolution.firstlook.journey"),
      bearer: sessionStorage.getItem("citynexus.traveler.bearer"),
    }));
    expect(oldState.pointer).toBeNull();
    expect(oldState.bearer).toBe("STALE_SIGNED_FIXTURE");
    expect(publicProviderRequests).toBe(0);

    let issued = false;
    await page.route("**/api/v1/travelers", async (route) => {
      expect(route.request().method()).toBe("POST");
      expect(route.request().headers()["authorization"]).toBeUndefined();
      issued = true;
      await json(route, 201, { id: "fixture-traveler-2", access_token: "NEW_SIGNED_FIXTURE" });
    });
    await page.route("**/api/v1/journeys", async (route) => {
      expect(route.request().method()).toBe("POST");
      expect(route.request().headers()["authorization"]).toBe("Bearer NEW_SIGNED_FIXTURE");
      await json(route, 201, { id: newJourneyId });
    });
    await page.route(`**/api/v1/journeys/${newJourneyId}/bootstrap-discovery/readiness`,
      (r) => json(r, 200, { journey_id: newJourneyId, status: "BLOCKED", reason_code: "TEST_OFFLINE" }));
    await page.route(`**/api/v1/journeys/${newJourneyId}/bootstrap-shortlist`,
      (r) => json(r, 200, { journey_id: newJourneyId, items: [], pocket_walk: null }));

    await page.getByTestId("rev-firstlook-start").click();
    await expect(page.getByTestId("rev-mobile-screen-explore")).toBeVisible();
    expect(issued).toBe(true);
    const latest = await page.evaluate(() => ({
      pointer: JSON.parse(localStorage.getItem("citynexus.revolution.firstlook.journey") || "{}") as { id?: string },
      bearer: sessionStorage.getItem("citynexus.traveler.bearer"),
    }));
    expect(latest.pointer.id).toBe(newJourneyId);
    expect(latest.bearer).toBe("NEW_SIGNED_FIXTURE");
    expect(publicProviderRequests).toBe(0);
  });

  test("failed create Journey never overwrites an existing signed browser session", async ({ page }) => {
    await page.addInitScript(() => {
      sessionStorage.setItem("citynexus.traveler.bearer", "ORIGINAL_SIGNED_FIXTURE");
      localStorage.removeItem("citynexus.revolution.firstlook.journey");
    });
    await page.route("**/api/v1/agent/runtime-status", (r) => json(r, 200, {
      runtime_identity: "UNAVAILABLE", hermes_compat_configured: false, ai_state: "DISABLED",
    }));
    await page.route("**/api/v1/travelers", (r) =>
      json(r, 201, { id: "fixture-traveler-2", access_token: "NEW_BUT_NOT_COMMITTED" }));
    await page.route("**/api/v1/journeys", async (r) => {
      expect(r.request().headers()["authorization"]).toBe("Bearer NEW_BUT_NOT_COMMITTED");
      await json(r, 503, { detail: "TEST_ONLY_BACKEND_UNAVAILABLE" });
    });

    await page.goto("/revolution");
    await page.getByTestId("rev-firstlook-start").click();
    await expect(page.getByRole("alert")).toContainText("HTTP 503");
    const result = await page.evaluate(() => ({
      pointer: localStorage.getItem("citynexus.revolution.firstlook.journey"),
      bearer: sessionStorage.getItem("citynexus.traveler.bearer"),
    }));
    expect(result.pointer).toBeNull();
    expect(result.bearer).toBe("ORIGINAL_SIGNED_FIXTURE");
  });
});
