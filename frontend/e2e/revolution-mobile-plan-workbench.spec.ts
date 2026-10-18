import { expect, test } from "@playwright/test";

const journeyId = "00000000-0000-4000-8000-000000000331";
const planId = "00000000-0000-4000-8000-000000000332";

for (const viewport of [{ width: 390, height: 844 }, { width: 430, height: 932 }]) {
test(`TEST_FIXTURE mobile plan review requires separate select and start, and survives refresh ${viewport.width}`, async ({ page }, testInfo) => {
  await page.setViewportSize(viewport);
  const writes: string[] = [];
  let selected = false;
  let active = false;
  await page.addInitScript(({ journeyId }) => {
    sessionStorage.setItem("citynexus.traveler.bearer", "TEST_FIXTURE_PLAN_OWNER");
    sessionStorage.setItem("citynexus.traveler.session-id", "TEST_FIXTURE_PLAN_TRAVELER");
    localStorage.setItem("citynexus.revolution.firstlook.journey", JSON.stringify({
      id: journeyId, cityCode: "TEST_FIXTURE", cityName: "测试地区", status: "DRAFT", ownerTravelerId: "TEST_FIXTURE_PLAN_TRAVELER",
    }));
  }, { journeyId });
  await page.route("**/api/v1/**", async (route) => {
    const req = route.request();
    const path = new URL(req.url()).pathname;
    const respond = (data: unknown, status = 200) => route.fulfill({ status, contentType: "application/json", body: JSON.stringify(data) });
    if (req.method() === "POST") writes.push(path);
    if (path.endsWith("/travelers/session")) return respond({ traveler_id: "TEST_FIXTURE_PLAN_TRAVELER" });
    if (path.endsWith("/agent/runtime-status")) return respond({ ai_state: "DISABLED", runtime_identity: "UNAVAILABLE" });
    if (path === `/api/v1/journeys/${journeyId}`) return respond({
      id: journeyId, city_code: "TEST_FIXTURE", title: "TEST_FIXTURE 3天旅行", timezone: "Asia/Shanghai",
      status: active ? "ACTIVE" : selected ? "PLANNED" : "DRAFT",
      start_at: "2026-11-01T09:00:00+08:00", end_at: "2026-11-03T18:00:00+08:00",
    });
    if (path.endsWith("/plans") && req.method() === "GET") {
      if (req.headers().authorization !== "Bearer TEST_FIXTURE_PLAN_OWNER") return respond({ detail: "TEST_FIXTURE_OTHER_MEMBER" }, 403);
      expect(req.headers().authorization).toBe("Bearer TEST_FIXTURE_PLAN_OWNER");
      return respond([{
        id: planId, journey_id: journeyId, version_no: 1, status: active ? "ACTIVE" : selected ? "SELECTED" : "CANDIDATE",
        is_current: selected, selectable: true, stale: false, lifecycle: "ACTIVE", planning_mode: "balanced", source: "INITIAL",
        total_cost: { amount_minor: 0, currency: "CNY" }, total_cost_status: "PARTIAL_UNKNOWN",
        activities: [{
          id: "TEST_FIXTURE_ACTIVITY", sequence_no: 1, title: "TEST_FIXTURE · 城市公园", activity_type: "VISIT",
          start_at: "2026-11-01T10:00:00+08:00", end_at: "2026-11-01T11:00:00+08:00",
          travel_from_prev_min: 15, estimated_cost: { amount_minor: 0, currency: "CNY" }, cost_status: "UNKNOWN",
          metadata: { opening_hours: { source_urls: ["https://example.org/TEST_FIXTURE/place", "javascript:alert(1)"] } },
        }],
      }]);
    }
    if (path.endsWith(`/plans/${planId}/select`) && req.method() === "POST") {
      expect(req.headers().authorization).toBe("Bearer TEST_FIXTURE_PLAN_OWNER");
      selected = true;
      return respond({ status: "PLANNED" });
    }
    if (path.endsWith("/start") && req.method() === "POST") {
      expect(selected).toBe(true);
      active = true;
      return respond({ journey_id: journeyId, active_plan_version_id: planId, context: { journey_status: "ACTIVE" } });
    }
    if (path.endsWith("/bootstrap-shortlist")) return respond({ journey_id: journeyId, items: [], resume: null, pocket_walk: null });
    return respond({ detail: "TEST_FIXTURE_NOT_SEEDED" }, 404);
  });

  await page.goto("/revolution");
  await page.getByTestId("rev-mobile-tab-trips").click();
  const workbench = page.getByTestId("rev-plan-workbench");
  await expect(workbench).toContainText("TEST_FIXTURE · 城市公园");
  await expect(workbench).toContainText("10:00—11:00");
  await expect(workbench).toContainText("费用待确认");
  await expect(workbench.getByTestId("rev-plan-day-gap")).toHaveText("还有 2 天未安排，可返回探索补充地点。");
  await expect(workbench.locator('a[href^="javascript:"]')).toHaveCount(0);
  expect(writes).toEqual([]);
  await expect(page.getByTestId("rev-plan-start")).toHaveCount(0);
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  const selectBounds = await page.getByTestId("rev-plan-select").boundingBox();
  expect(selectBounds?.height ?? 0).toBeGreaterThanOrEqual(44);
  await page.screenshot({ path: testInfo.outputPath(`plan-review-${viewport.width}x${viewport.height}-TEST_FIXTURE.png`) });
  await page.getByTestId("rev-plan-select").click();
  await expect(workbench).toContainText("已选用");
  expect(writes).toEqual([`/api/v1/journeys/${journeyId}/plans/${planId}/select`]);
  await page.reload();
  await page.getByTestId("rev-mobile-tab-trips").click();
  await expect(workbench).toContainText("已选用");
  await expect(page.getByTestId("rev-plan-start")).toBeVisible();
  await page.getByTestId("rev-plan-start").click();
  await expect(workbench).toContainText("正在使用");
  expect(writes).toEqual([`/api/v1/journeys/${journeyId}/plans/${planId}/select`, `/api/v1/journeys/${journeyId}/start`]);
  await page.evaluate(() => {
    sessionStorage.setItem("citynexus.traveler.bearer", "TEST_FIXTURE_OTHER_MEMBER");
    window.dispatchEvent(new CustomEvent("citynexus.traveler.bearer.changed"));
  });
  await expect(workbench).not.toContainText("TEST_FIXTURE · 城市公园");
  await expect(workbench).toContainText("当前账号无法读取这份行程");
});
}
