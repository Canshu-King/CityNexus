import { expect, test, type Page } from "@playwright/test";

const JOURNEY_ID = "r35-live-guardian-journey";

async function seed(page: Page) {
  await page.addInitScript(() => {
    localStorage.setItem("citynexus.v8.journey_id", "r35-live-guardian-journey");
    localStorage.setItem("citynexus.locale", "zh-CN");
    try {
      (navigator as any).serviceWorker.register = () => Promise.resolve({});
    } catch {
      /* no-op */
    }
  });
}

async function mockApi(page: Page, pulse: unknown) {
  await page.route(/\/api\/v1\//, (route) => {
    const pathname = new URL(route.request().url()).pathname;
    const send = (json: unknown) =>
      route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(json) });
    if (pathname.endsWith("/experience")) {
      return send({
        journey: {
          id: JOURNEY_ID,
          traveler_id: "r35-traveler",
          title: "R35 live check",
          city_code: "NARA",
          timezone: "Asia/Tokyo",
          status: "ACTIVE",
        },
        active_plan: { id: "plan-r35", status: "ACTIVE", activities: [], legs: [], disruptions: [] },
        trip: { party_size: 1 },
        offers: [],
        options: [],
        mobility_facts: [],
        recovery: null,
        experience_flags: { needs_review: false, recovery_required: false, staleness: false, feasibility_failures: [] },
      });
    }
    if (pathname.endsWith("/guardian/pulse/latest")) return send({ journey_id: JOURNEY_ID, pulse });
    if (pathname.endsWith("/replans")) return send([]);
    if (pathname.endsWith("/plans")) return send([]);
    if (pathname.endsWith("/twin")) return send({ id: "twin-r35", context: {} });
    if (pathname.endsWith("/agent-policy")) return send({ mode: "ADVISORY", auto_accept_replan: false });
    if (pathname.endsWith("/wallet")) return send({ reservations: [], commitments: [], offline_ready: true });
    if (pathname.endsWith("/offline-snapshot")) return send({ journey_id: JOURNEY_ID, sequence: 1, snapshot: {}, provider_freshness: {} });
    if (pathname.endsWith("/runtime-status")) return send({});
    if (pathname.endsWith("/execution-clock")) return send({ now: "2026-10-08T09:00:00+09:00", timezone: "Asia/Tokyo", current_activity_id: null });
    if (pathname.endsWith("/web-observations")) return send({ observations: [] });
    return send({});
  });
}

test.describe("R35 Guardian status on Live Recovery", () => {
  test("shows a calm checked-and-clear state", async ({ page }) => {
    await seed(page);
    await mockApi(page, {
      id: "pulse-clear",
      status: "COMPLETED",
      completed_at: "2026-10-08T01:00:00+00:00",
      result: { signals: { degraded: false }, context_watch: { status: "NO_MATERIAL_CHANGE" } },
    });
    await page.goto("/v8/live", { waitUntil: "domcontentloaded" });
    const check = page.getByTestId("live-guardian-check");
    await expect(check).toHaveAttribute("data-state", "clear");
    await expect(check).toContainText("刚刚检查过");
    await expect(check).toContainText("目前的安排仍然可行");
  });

  test("shows incomplete verification without alarming recovery copy", async ({ page }) => {
    await seed(page);
    await mockApi(page, {
      id: "pulse-unknown",
      status: "COMPLETED",
      completed_at: "2026-10-08T01:00:00+00:00",
      result: { signals: { degraded: true }, context_watch: { status: "UNKNOWN" } },
    });
    await page.goto("/v8/live", { waitUntil: "domcontentloaded" });
    const check = page.getByTestId("live-guardian-check");
    await expect(check).toHaveAttribute("data-state", "incomplete");
    await expect(check).toContainText("部分实时信息暂时无法确认");
    await expect(check).not.toContainText("发生真实变化");
  });
});
