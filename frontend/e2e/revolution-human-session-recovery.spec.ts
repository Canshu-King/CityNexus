import { expect, test, type Route } from "@playwright/test";

const oldJourneyId = "00000000-0000-4000-8000-000000000117";
const newJourneyId = "00000000-0000-4000-8000-000000000118";
const migratedJourneyId = "00000000-0000-4000-8000-000000000119";

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
  test.beforeEach(async ({ page }) => {
    await page.route("**/api/v1/journeys/*/planning-intent", (route) => json(route, 404, {detail:"TEST_FIXTURE_NO_TRIP_BRIEF"}));
    await page.route("**/api/v1/journeys/*/bootstrap-discovery/current", (route) => json(route, 200, null));
  });

  test("a stale Journey's 403 offers one-tap restart without deleting its server record", async ({ page }) => {
    await page.addInitScript(({ id }) => {
      sessionStorage.setItem("citynexus.traveler.bearer", "STALE_SIGNED_FIXTURE");
      sessionStorage.setItem("citynexus.traveler.session-id", "traveler-stale");
      localStorage.setItem("citynexus.revolution.firstlook.journey", JSON.stringify({
        id, cityCode: "CN-RV-OLD", cityName: "连城", status: "DRAFT", ownerTravelerId: "traveler-stale",
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
    await page.route(`**/api/v1/journeys/${oldJourneyId}/operator`,
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
    expect(oldState.bearer).toBeNull();
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

  test("failed signed-session lookup keeps the current bearer and offers a fresh-session recovery", async ({ page }) => {
    await page.addInitScript(() => {
      sessionStorage.setItem("citynexus.traveler.bearer", "ORIGINAL_SIGNED_FIXTURE");
      sessionStorage.removeItem("citynexus.traveler.session-id");
      localStorage.removeItem("citynexus.revolution.firstlook.journey");
    });
    await page.route("**/api/v1/agent/runtime-status", (r) => json(r, 200, {
      runtime_identity: "UNAVAILABLE", hermes_compat_configured: false, ai_state: "DISABLED",
    }));
    await page.route("**/api/v1/travelers/session", (r) => json(r, 401, { detail: "INVALID_SIGNED_SESSION" }));

    await page.goto("/revolution");
    await page.getByTestId("rev-firstlook-city").fill("测试地区");
    await page.getByTestId("rev-firstlook-start").click();
    await expect(page.getByRole("alert")).toContainText("401");
    await expect(page.getByTestId("rev-firstlook-new-session")).toBeVisible();

    let travelerCreates = 0;
    await page.route("**/api/v1/travelers", async (route) => {
      travelerCreates += 1;
      expect(route.request().headers()["authorization"]).toBeUndefined();
      await json(route, 201, { id: "fixture-traveler-2", access_token: "NEW_BUT_NOT_COMMITTED" });
    });
    let journeyCreates = 0;
    await page.route("**/api/v1/journeys", async (route) => {
      journeyCreates += 1;
      expect(route.request().headers()["authorization"]).toBe("Bearer NEW_BUT_NOT_COMMITTED");
      await json(route, 503, { detail: "TEST_ONLY_BACKEND_UNAVAILABLE" });
    });
    await page.getByTestId("rev-firstlook-new-session").click();
    await expect(page.getByTestId("rev-start-write-status")).toContainText("结果未知");
    await expect(page.getByTestId("rev-firstlook-start")).toBeDisabled();
    await page.locator("form").evaluate((form) => (form as HTMLFormElement).requestSubmit());
    const result = await page.evaluate(() => ({
      pointer: localStorage.getItem("citynexus.revolution.firstlook.journey"),
      bearer: sessionStorage.getItem("citynexus.traveler.bearer"),
      marker: JSON.parse(localStorage.getItem("citynexus.revolution.firstlook.start-write") ?? "null"),
    }));
    expect(result.pointer).toBeNull();
    expect(result.bearer).toBe("ORIGINAL_SIGNED_FIXTURE");
    expect(result.marker).toMatchObject({ phase: "journey", state: "unknown" });
    expect(travelerCreates).toBe(1);
    expect(journeyCreates).toBe(1);
  });

  test("one signed traveler starts and reopens Journeys in multiple cities", async ({ page }) => {
    await page.addInitScript(() => {
      sessionStorage.setItem("citynexus.traveler.bearer", "ONE_TRAVELER_FIXTURE");
      sessionStorage.setItem("citynexus.traveler.session-id", "traveler-one");
      localStorage.removeItem("citynexus.revolution.firstlook.journey");
      localStorage.removeItem("citynexus.revolution.firstlook.recent-journeys");
    });
    await page.route("**/api/v1/agent/runtime-status", (r) => json(r, 200, {
      runtime_identity: "UNAVAILABLE", hermes_compat_configured: false, ai_state: "DISABLED",
    }));
    await page.route("**/api/v1/travelers/session", async (route) => {
      expect(route.request().headers()["authorization"]).toBe("Bearer ONE_TRAVELER_FIXTURE");
      await json(route, 200, { traveler_id: "traveler-one" });
    });
    let travelerCreates = 0;
    await page.route("**/api/v1/travelers", async (route) => {
      travelerCreates += 1;
      await json(route, 500, { detail: "existing signed traveler should be reused" });
    });
    const createdJourneys: string[] = [];
    await page.route("**/api/v1/journeys", async (route) => {
      expect(route.request().method()).toBe("POST");
      expect(route.request().headers()["authorization"]).toBe("Bearer ONE_TRAVELER_FIXTURE");
      const body = route.request().postDataJSON() as { traveler_id?: string };
      expect(body.traveler_id).toBe("traveler-one");
      const id = createdJourneys.length === 0 ? oldJourneyId : newJourneyId;
      createdJourneys.push(id);
      await json(route, 201, { id });
    });
    await page.route("**/api/v1/journeys/*/bootstrap-discovery/readiness", (r) =>
      json(r, 200, { status: "BLOCKED", reason_code: "TEST_OFFLINE" }));
    await page.route("**/api/v1/journeys/*/bootstrap-shortlist", (r) =>
      json(r, 200, { items: [], pocket_walk: null }));

    await page.goto("/revolution");
    await page.getByTestId("rev-firstlook-city").fill("宁波");
    await page.getByTestId("rev-firstlook-start").click();
    await expect(page.getByTestId("rev-mobile-screen-explore")).toBeVisible();
    await page.getByRole("button", { name: "换地区" }).click();
    await expect(page.getByTestId("rev-recent-journeys")).toContainText("宁波");

    await page.getByTestId("rev-firstlook-city").fill("上海");
    await page.getByTestId("rev-firstlook-start").click();
    await expect(page.getByTestId("rev-mobile-screen-explore")).toBeVisible();
    await page.getByRole("button", { name: "换地区" }).click();
    await expect(page.getByTestId("rev-recent-journeys")).toContainText("上海");
    await expect(page.getByTestId("rev-recent-journeys")).toContainText("宁波");
    await page.getByRole("button", { name: "打开宁波行程" }).click();
    await expect(page.getByTestId("rev-mission-cockpit").getByRole("heading", { level: 2, name: "宁波", exact: true })).toBeVisible();

    const state = await page.evaluate(() => ({
      bearer: sessionStorage.getItem("citynexus.traveler.bearer"),
      travelerId: sessionStorage.getItem("citynexus.traveler.session-id"),
      pointer: JSON.parse(localStorage.getItem("citynexus.revolution.firstlook.journey") || "{}") as { id?: string; ownerTravelerId?: string },
      recent: JSON.parse(localStorage.getItem("citynexus.revolution.firstlook.recent-journeys") || "[]") as unknown[],
    }));
    expect(state.bearer).toBe("ONE_TRAVELER_FIXTURE");
    expect(state.travelerId).toBe("traveler-one");
    expect(state.pointer.id).toBe(oldJourneyId);
    expect(state.pointer.ownerTravelerId).toBe("traveler-one");
    expect(state.recent).toHaveLength(2);
    expect(travelerCreates).toBe(0);
    expect(createdJourneys).toEqual([oldJourneyId, newJourneyId]);
  });

  test("legacy bearer-only session restores a Journey after server membership proof", async ({ page }) => {
    await page.addInitScript(({ id }) => {
      sessionStorage.setItem("citynexus.traveler.bearer", "LEGACY_BEARER_FIXTURE");
      sessionStorage.removeItem("citynexus.traveler.session-id");
      localStorage.setItem("citynexus.revolution.firstlook.journey", JSON.stringify({
        id, cityCode: "CN-RV-XM", cityName: "厦门", status: "DRAFT",
      }));
    }, { id: migratedJourneyId });
    await page.route("**/api/v1/agent/runtime-status", (r) => json(r, 200, {
      runtime_identity: "UNAVAILABLE", hermes_compat_configured: false, ai_state: "DISABLED",
    }));
    await page.route("**/api/v1/travelers/session", async (route) => {
      expect(route.request().headers()["authorization"]).toBe("Bearer LEGACY_BEARER_FIXTURE");
      await json(route, 200, { traveler_id: "traveler-legacy" });
    });
    let membershipRead = false;
    await page.route(`**/api/v1/journeys/${migratedJourneyId}/operator`, async (route) => {
      expect(route.request().headers()["authorization"]).toBe("Bearer LEGACY_BEARER_FIXTURE");
      membershipRead = true;
      await json(route, 200, { journey_id: migratedJourneyId, state: "OFF" });
    });
    await page.route(`**/api/v1/journeys/${migratedJourneyId}/bootstrap-discovery/readiness`, (r) =>
      json(r, 200, { journey_id: migratedJourneyId, status: "BLOCKED", reason_code: "TEST_OFFLINE" }));

    await page.goto("/revolution");
    await expect(page.getByTestId("rev-mobile-screen-explore")).toBeVisible();
    await expect(page.getByTestId("rev-mission-cockpit").getByRole("heading", { level: 2, name: "厦门", exact: true })).toBeVisible();
    const state = await page.evaluate(() => ({
      travelerId: sessionStorage.getItem("citynexus.traveler.session-id"),
      pointer: JSON.parse(localStorage.getItem("citynexus.revolution.firstlook.journey") || "{}") as {
        id?: string; ownerTravelerId?: string;
      },
    }));
    expect(membershipRead).toBe(true);
    expect(state.travelerId).toBe("traveler-legacy");
    expect(state.pointer).toMatchObject({ id: migratedJourneyId, ownerTravelerId: "traveler-legacy" });
  });

  test("a Journey that already has a PlanVersion still restores, because a 409 shortlist is not a denial", async ({ page }) => {
    const plannedJourneyId = "00000000-0000-4000-8000-000000000120";
    await page.addInitScript(({ id }) => {
      sessionStorage.setItem("citynexus.traveler.bearer", "PLANNED_BEARER_FIXTURE");
      sessionStorage.setItem("citynexus.traveler.session-id", "traveler-planned");
      localStorage.setItem("citynexus.revolution.firstlook.journey", JSON.stringify({
        id, cityCode: "CN-RV-BJ", cityName: "北京", status: "DRAFT",
      }));
    }, { id: plannedJourneyId });
    await page.route("**/api/v1/agent/runtime-status", (r) => json(r, 200, {
      runtime_identity: "UNAVAILABLE", hermes_compat_configured: false, ai_state: "DISABLED",
    }));
    await page.route("**/api/v1/travelers/session", (route) => json(route, 200, { traveler_id: "traveler-planned" }));
    let operatorRead = false;
    await page.route(`**/api/v1/journeys/${plannedJourneyId}/operator`, async (route) => {
      expect(route.request().headers()["authorization"]).toBe("Bearer PLANNED_BEARER_FIXTURE");
      operatorRead = true;
      await json(route, 200, { journey_id: plannedJourneyId, state: "OFF" });
    });
    // The real endpoint answers this way once a PlanVersion exists; it must never be the
    // membership proof, or every planned Journey becomes unrestorable.
    await page.route(`**/api/v1/journeys/${plannedJourneyId}/bootstrap-shortlist`, (r) =>
      json(r, 409, { error: { code: "CONFLICT", message: "a shortlist is unavailable after a PlanVersion exists" } }));
    await page.route(`**/api/v1/journeys/${plannedJourneyId}/bootstrap-discovery/readiness`, (r) =>
      json(r, 200, { journey_id: plannedJourneyId, status: "BLOCKED", reason_code: "TEST_OFFLINE" }));

    await page.goto("/revolution");
    await expect(page.getByTestId("rev-mobile-screen-explore")).toBeVisible();
    await expect(page.getByTestId("rev-mission-cockpit").getByRole("heading", { level: 2, name: "北京", exact: true })).toBeVisible();
    await expect(page.getByText("旧行程无法恢复，原记录仍保存在服务器。")).toHaveCount(0);
    expect(operatorRead).toBe(true);
  });
});
