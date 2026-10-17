import { expect, test, type Page } from "@playwright/test";

const journey = "00000000-0000-4000-8000-000000000119";
const root = "**/api/v1/journeys/" + journey;
const privateMarker = "raw-provider-secret-should-never-render";

async function prepare(page: Page, status: number | "timeout") {
  let calls = 0;
  await page.addInitScript((id) => {
    window.sessionStorage.setItem("citynexus.traveler.bearer", "signed-only-error-fixture-token");
    window.localStorage.setItem("citynexus.revolution.firstlook.journey", JSON.stringify({
      id, cityCode: "CN-RV-ERROR-TEST", cityName: "连城", status: "DRAFT",
    }));
  }, journey);
  await page.route("**/api/v1/agent/runtime-status", (route) => route.fulfill({
    status: 200,
    contentType: "application/json",
    body: JSON.stringify({ runtime_identity: "UNCONFIGURED", hermes_compat_configured: false }),
  }));
  await page.route(root + "/bootstrap-discovery/readiness", (route) => route.fulfill({
    status: 200,
    contentType: "application/json",
    body: JSON.stringify({ status: "READY", provider: "overpass", provider_grade: "TEST_PROVIDER" }),
  }));
  await page.route(root + "/bootstrap-shortlist", (route) => route.fulfill({
    status: 200,
    contentType: "application/json",
    body: JSON.stringify({ journey_id: journey, limit: 3, items: [], resume: null, pocket_walk: null }),
  }));
  await page.route(root + "/bootstrap-city-search", async (route) => {
    calls += 1;
    if (status === "timeout") {
      await route.abort("timedout");
      return;
    }
    await route.fulfill({
      status,
      contentType: "application/json",
      body: JSON.stringify({
        error: {
          code: "REQUEST_ERROR",
          reason_code: "INJECTED_" + status,
          message: privateMarker,
          details: { token: privateMarker, trace_id: "private-trace-marker" },
        },
      }),
    });
  });
  await page.goto("/revolution");
  await expect(page.getByTestId("rev-quick-explore")).toBeVisible();
  expect(calls).toBe(0);
  return () => calls;
}

const httpCases = [
  { status: 401, copy: "有效的签名会话" },
  { status: 403, copy: "无法用当前登录信息操作这条行程" },
  { status: 404, copy: "服务器找不到当前行程或对应资源" },
  { status: 409, copy: "行程状态已经变化" },
  { status: 422, copy: "服务器拒绝了「查找地名」提交的数据" },
  { status: 429, copy: "进行了限流" },
  { status: 502, copy: "HTTP 502" },
  { status: 503, copy: "HTTP 503" },
] as const;

for (const item of httpCases) {
  test("地名搜索将 HTTP " + item.status + " 归类" + (item.status === 403 ? "并保留探索状态" : "并显示脱敏恢复"), async ({ page }) => {
    const calls = await prepare(page, item.status);
    const quickExplore = page.getByTestId("rev-quick-explore");
    if (item.status === 403) {
      const mapLinkSection = quickExplore.getByTestId("rev-quick-area").locator("details");
      await mapLinkSection.locator("summary").click();
      await page.getByLabel("公开地图链接").fill("https://www.openstreetmap.org/#map=13/30.248/120.146");
      await page.getByTestId("rev-quick-apply-map-link").click();
      await expect(quickExplore).toContainText("本次探索位置：地图中心已选 · 30.248, 120.146");
      await quickExplore.getByRole("button", { name: "换一个位置" }).click();
      await page.getByLabel("城市或地区").fill("杭州西湖");
    }
    await page.getByTestId("rev-quick-find-city").click();
    const alert = page.getByRole("alert");
    await expect(alert).toContainText(item.copy);
    const recovery = page.getByTestId("rev-quick-error-recovery");
    await expect(recovery).toHaveCount(1);
    if (item.status === 403) {
      await expect(quickExplore.getByTestId("rev-quick-area")).toBeVisible();
      await expect(page.getByLabel("城市或地区")).toHaveValue("杭州西湖");
      await expect(quickExplore).toContainText("本次探索位置：地图中心已选 · 30.248, 120.146");
      expect(calls()).toBe(1);
    }
    await page.getByTestId("rev-quick-error-details").locator("summary").click();
    await expect(page.getByTestId("rev-quick-error-details")).toContainText(
      "请求：POST /journeys/:id/bootstrap-city-search",
    );
    await expect(page.getByTestId("rev-quick-error-details")).toContainText("HTTP 状态：" + item.status);
    await expect(page.getByTestId("rev-quick-error-details")).toContainText("服务端原因码：INJECTED_" + item.status);
    const rendered = await page.locator("body").innerText();
    expect(rendered).not.toContain(privateMarker);
    expect(rendered).not.toContain(journey);
    expect(rendered).not.toContain("private-trace-marker");
    if (item.status === 403) {
      await recovery.click();
      await expect(page.getByTestId("rev-mobile-welcome")).toBeVisible();
      await expect(page.getByLabel("目的地")).toHaveValue("杭州西湖");
      const session = await page.evaluate(() => ({
        bearer: window.sessionStorage.getItem("citynexus.traveler.bearer"),
        journey: window.localStorage.getItem("citynexus.revolution.firstlook.journey"),
      }));
      expect(session).toEqual({ bearer: null, journey: null });
      expect(calls()).toBe(1);
    }
    if (item.status === 503) {
      await page.getByTestId("rev-quick-error-recovery").click();
      await expect(alert).toContainText("HTTP 503");
      expect(calls()).toBe(2);
    }
  });
}

test("地名搜索超时显示没有 HTTP 回答，并保留准确请求路径", async ({ page }) => {
  await prepare(page, "timeout");
  await page.getByTestId("rev-quick-find-city").click();
  await expect(page.getByRole("alert")).toContainText("没有收到 HTTP 答复");
  await expect(page.getByTestId("rev-quick-error-recovery")).toHaveCount(1);
  await page.getByTestId("rev-quick-error-details").locator("summary").click();
  await expect(page.getByTestId("rev-quick-error-details")).toContainText(
    "请求：POST /journeys/:id/bootstrap-city-search",
  );
  await expect(page.getByTestId("rev-quick-error-details")).toContainText("HTTP 状态：未收到 HTTP 状态");
});
