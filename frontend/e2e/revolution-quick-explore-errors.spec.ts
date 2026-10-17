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

test.describe("地名服务失败后的 390x844 触控地图回退", () => {
  test.use({ viewport: { width: 390, height: 844 }, hasTouch: true, isMobile: true, serviceWorkers: "block" });
  test.use({ storageState: { cookies: [], origins: [] } });

test("打开地图后地图与兴趣选择都处于可操作视区", async ({ page }) => {
  let cityCalls = 0;
  let tileCalls = 0;
  const unexpectedProviderRequests: string[] = [];
  let releaseCitySearch!: () => void;
  const citySearchGate = new Promise<void>((resolve) => { releaseCitySearch = resolve; });
  await page.addInitScript((id) => {
    window.sessionStorage.setItem("citynexus.traveler.bearer", "signed-only-error-fixture-token");
    window.localStorage.setItem("citynexus.revolution.firstlook.journey", JSON.stringify({
      id, cityCode: "CN-RV-ERROR-TEST", cityName: "连城", status: "DRAFT",
    }));
  }, journey);
  await page.route("**/api/v1/travelers/session", (route) => route.fulfill({
    status: 200,
    contentType: "application/json",
    body: JSON.stringify({ traveler_id: "00000000-0000-4000-8000-000000000120" }),
  }));
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
    cityCalls += 1;
    await citySearchGate;
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        journey_id: journey,
        status: "GEOCODER_UNAVAILABLE",
        query: "连城",
        provider_key: null,
        provider_attempts: [{ provider: "nominatim", answered: false, error: "ConnectTimeout" }],
        results: [],
        provider_provenance: "UNVERIFIED",
      }),
    });
  });
  await page.route("https://tile.openstreetmap.org/**", (route) => {
    tileCalls += 1;
    return route.fulfill({ status: 200, contentType: "image/png", body: Buffer.from(
      "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+jB8sAAAAASUVORK5CYII=",
      "base64",
    ) });
  });
  await page.route(/(?:nominatim|photon|overpass)/i, async (route) => {
    unexpectedProviderRequests.push(route.request().url());
    await route.abort();
  });

  await page.goto("/revolution");
  const cityButton = page.getByTestId("rev-quick-find-city");
  await cityButton.tap();
  try {
    await expect(cityButton).toHaveText("查询中…");
    const aiButton = page.getByTestId("rev-quick-consult-ai");
    await expect(aiButton).toHaveText("问问 AI →");
    await expect(aiButton).toBeDisabled();
  } finally {
    releaseCitySearch();
  }
  await expect(page.getByRole("status")).toContainText("地名查找暂时连不上");
  await expect(page.getByTestId("rev-quick-error-recovery")).toHaveText("打开 OpenStreetMap 地图手选 →");
  await expect(page.getByText("点击后会加载 OpenStreetMap 地图底图；不会使用设备定位。")).toBeVisible();
  await expect(page.getByTestId("rev-quick-photon-search")).toHaveText("改用 Photon 地名查找 →");
  await expect(page.getByText("备用搜索会把“连城”发送至 Photon（Komoot 公开地名服务）。")).toBeVisible();
  expect(cityCalls).toBe(1);
  expect(tileCalls).toBe(0);
  expect(unexpectedProviderRequests).toEqual([]);

  await page.getByTestId("rev-quick-error-recovery").tap();
  const map = page.getByTestId("rev-quick-map-fallback");
  await expect(map).toBeVisible();
  await expect(map).toContainText("不会读取设备定位，也不代表地名搜索结果");
  await expect(map.getByTestId("bootstrap-public-map-canvas")).toBeVisible();
  await expect.poll(async () => {
    const [mapBox, headerBox, navBox] = await Promise.all([
      map.boundingBox(),
      page.locator(".rev-mobile-v1 .rev-firstlook-header").boundingBox(),
      page.locator(".rev-mobile-v1 .rev-mobile-bottom-nav").boundingBox(),
    ]);
    return Boolean(
      mapBox && headerBox && navBox &&
      mapBox.y >= headerBox.y + headerBox.height &&
      mapBox.y + mapBox.height <= navBox.y,
    );
  }).toBe(true);
  const [mapBox, headerBox, navBox] = await Promise.all([
    map.boundingBox(),
    page.locator(".rev-mobile-v1 .rev-firstlook-header").boundingBox(),
    page.locator(".rev-mobile-v1 .rev-mobile-bottom-nav").boundingBox(),
  ]);
  expect(mapBox).not.toBeNull();
  expect(headerBox).not.toBeNull();
  expect(navBox).not.toBeNull();
  expect(mapBox!.y).toBeGreaterThanOrEqual(headerBox!.y + headerBox!.height);
  expect(mapBox!.y + mapBox!.height).toBeLessThanOrEqual(navBox!.y);
  await expect.poll(() => tileCalls).toBeGreaterThan(0);
  await map.locator("canvas").tap({ position: { x: 120, y: 100 } });
  const category = page.getByTestId("rev-quick-category");
  await expect(category).toBeVisible();
  await expect(category.getByText("这次想看些什么？")).toBeInViewport();
  const firstCategory = category.locator(".rev-quick-categories button").first();
  await firstCategory.tap();
  await expect(firstCategory).toHaveAttribute("aria-pressed", "true");
  const primaryAction = category.getByTestId("rev-quick-find-places");
  await primaryAction.scrollIntoViewIfNeeded();
  const [primaryBox, navAfterScroll] = await Promise.all([primaryAction.boundingBox(), page.locator(".rev-mobile-v1 .rev-mobile-bottom-nav").boundingBox()]);
  expect(primaryBox).not.toBeNull();
  expect(navAfterScroll).not.toBeNull();
  expect(primaryBox!.height).toBeGreaterThanOrEqual(44);
  expect(primaryBox!.y + primaryBox!.height).toBeLessThanOrEqual(navAfterScroll!.y);
  expect(cityCalls).toBe(1);
  expect(unexpectedProviderRequests).toEqual([]);
});
});
