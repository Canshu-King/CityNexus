import { expect, test, type Page, type Route } from "@playwright/test";

/**
 * UI FIXTURE ONLY: verifies the new mobile shell/navigation semantics.
 * Every returned Journey is an explicitly fake TEST_PROVIDER stub.
 * This cannot prove signed backend access, physical arrival, real POI or AI.
 */
const journeyId = "00000000-0000-4000-8000-000000000117";
const prefix = `**/api/v1/journeys/${journeyId}`;

async function fulfill(route: Route, value: unknown) {
  await route.fulfill({
    status: 200,
    contentType: "application/json",
    body: JSON.stringify(value),
  });
}

async function signedMockJourney(page: Page, saved = false) {
  await page.addInitScript(({ id }) => {
    window.sessionStorage.setItem("citynexus.traveler.bearer", "TEST_ONLY_SIGNED_FIXTURE_TOKEN");
    window.localStorage.setItem("citynexus.revolution.firstlook.journey", JSON.stringify({
      id,
      cityCode: "CN-RV-TEST",
      cityName: "连城",
      status: "DRAFT",
    }));
  }, { id: journeyId });
  await page.route("**/api/v1/agent/runtime-status", (r) => fulfill(r, {
    runtime_identity: "UNAVAILABLE",
    hermes_compat_configured: false,
    ai_state: "CONFIGURED_UNVERIFIED",
  }));
  await page.route(`${prefix}/bootstrap-discovery/readiness`, (r) => fulfill(r, {
    status: "READY",
    reason_code: "READY",
    expected_recipient: "TEST_PROVIDER",
    provider_grade: "TEST_PROVIDER",
    external_request_allowed: false,
    test_only: true,
  }));
  await page.route(`${prefix}/bootstrap-shortlist`, (r) => fulfill(r, {
    journey_id: journeyId,
    items: [],
    resume: null,
    pocket_walk: saved ? {
      pocket_walk_id: "test-only-walk",
      journey_id: journeyId,
      revision: 2,
      plan_version_id: null,
      first_stop: { name: "TEST ONLY - 第一站" },
      second_stop: { name: "TEST ONLY - 第二站" },
      go_progress: {
        state: "HEADING_TO_SECOND",
        progress_revision: 5,
        progress_class: "USER_REPORTED_PROGRESS",
        physical_arrival_state: "NOT_PHYSICAL_ARRIVAL_PROVEN",
      },
    } : null,
  }));
}

test.describe("Revolution Mobile-First UI fixture", () => {
  test.use({ viewport: { width: 390, height: 844 }, hasTouch: true });

  test("an unstarted visitor sees a clean, usable destination CTA", async ({ page }) => {
    await page.route("**/api/v1/agent/runtime-status", (r) => fulfill(r, {
      runtime_identity: "UNAVAILABLE",
      hermes_compat_configured: false,
      ai_state: "DISABLED",
    }));
    await page.goto("/revolution");
    await expect(page.getByTestId("rev-mobile-welcome")).toBeVisible();
    await expect(page.getByTestId("rev-firstlook-city")).toHaveValue("连城");
    await expect(page.getByTestId("rev-firstlook-start")).toBeVisible();
    await expect(page.getByTestId("rev-mobile-bottom-nav")).toHaveCount(0);
    const fits = await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 2);
    expect(fits).toBeTruthy();
  });

  test("three bottom tabs are tappable and never submit provider or model requests", async ({ page }) => {
    await signedMockJourney(page);
    let upstreamCalls = 0;
    page.on("request", (request) => {
      if (/bootstrap-city-search|trial-ai-discovery|bootstrap-discovery\/pocket-walk|\/bootstrap-discovery$/.test(request.url()) && request.method() === "POST") {
        upstreamCalls += 1;
      }
    });
    await page.goto("/revolution");
    const bar = page.getByTestId("rev-mobile-bottom-nav");
    await expect(bar).toBeVisible();
    await expect(page.getByTestId("rev-mobile-screen-explore")).toBeVisible();
    await expect(page.getByTestId("rev-quick-explore")).toBeVisible();

    for (const tab of ["trips", "me", "explore"] as const) {
      const button = page.getByTestId("rev-mobile-tab-" + tab);
      const bounds = await button.boundingBox();
      expect(bounds?.height ?? 0).toBeGreaterThanOrEqual(44);
      await button.click();
      await expect(button).toHaveAttribute("aria-current", "page");
      await expect(page.getByTestId("rev-mobile-screen-" + tab)).toBeVisible();
    }
    await expect(page.getByTestId("rev-quick-explore")).toBeVisible();
    expect(upstreamCalls).toBe(0);
    const fits = await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 2);
    expect(fits).toBeTruthy();
  });

  test("trip tab reflects only a saved TEST fixture, never a fabricated itinerary", async ({ page }) => {
    await signedMockJourney(page, true);
    await page.goto("/revolution");
    await page.getByTestId("rev-mobile-tab-trips").click();
    await expect(page.getByText("TEST ONLY - 第一站")).toBeVisible();
    await expect(page.getByText("TEST ONLY - 第二站")).toBeVisible();
    await expect(page.getByText("正在前往第二站")).toBeVisible();
    await page.getByRole("button", { name: "查看路线并继续 GO" }).click();
    await expect(page.getByTestId("rev-quick-walk")).toBeVisible();
  });
});
