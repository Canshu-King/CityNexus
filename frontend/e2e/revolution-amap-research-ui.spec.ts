import { expect, test } from "@playwright/test";

const journeyId = "00000000-0000-4000-8000-000000000941";
const taskId = "00000000-0000-4000-8000-000000000942";
const owner = "AMAP_UI_FIXTURE_OWNER";
const token = "AMAP_UI_TEST_FIXTURE_TOKEN";
const goal = "TEST_FIXTURE 去连城县找步行路线。";
const markerUrl = "https://uri.amap.com/marker?position=116.404,39.915&name=TEST_FIXTURE%E5%9C%B0%E7%82%B9&coordinate=gaode";
const navigationUrl = "https://uri.amap.com/navigation?from=116.404,39.915&to=116.414,39.925&mode=walk&coordinate=gaode";

test("TEST_FIXTURE Amap GCJ02 leads stay off OSM tiles and show their source and walking route", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  const lead = {
    id: "amap:fixture-poi-01", provider: "amap", provider_object_id: "fixture-poi-01",
    coordinate_system: "GCJ02", latitude: 39.915, longitude: 116.404, adcode: "350825",
    captured_at: "2026-10-19T00:00:00Z", name: "TEST_FIXTURE 连城县地点", category: "attraction",
    source_url: markerUrl, provider_provenance: "TEST_PROVIDER", region_status: "UNKNOWN",
    opening_status: "UNKNOWN", cost_status: "UNKNOWN",
    public_address: { province: "福建省", city: "龙岩市", county: "连城县", district: "连城县" },
  };
  const route = {
    id: "amap-route:fixture-01", from_place_id: lead.id, to_place_id: "amap:fixture-poi-02",
    from_name: "TEST_FIXTURE 起点", to_name: "TEST_FIXTURE 终点", provider: "amap", coordinate_system: "GCJ02",
    distance_m: 650, duration_seconds: 480, captured_at: "2026-10-19T00:01:00Z", source_url: navigationUrl,
  };
  const task = {
    task_id: taskId, journey_id: journeyId, mode: "GOAL_PLANNING", status: "PARTIAL_READY", goal,
    consent: { model: true, online_research: true }, budget: { max_model_turns: 8, max_tool_calls: 16 },
    usage: { model_turns: 1, tool_calls: 1 }, latest_run_id: null, candidate_place_ids: [],
    source_observation_ids: [], failure_code: null, assistant_summary: "TEST_FIXTURE 已整理路线线索。",
    research_places: [lead, {
      id: "osm:unknown-01", name: "TEST_FIXTURE 未归属 OSM 线索", category: "museum",
      latitude: 25.037, longitude: 121.563, coordinate_system: "WGS84", provider: "photon",
      source_url: "https://www.openstreetmap.org/node/12345", provider_provenance: "TEST_PROVIDER",
      region_status: "UNKNOWN", opening_status: "UNKNOWN", cost_status: "UNKNOWN",
    }, {
      id: "osm:conflict-01", name: "TEST_FIXTURE 明确冲突线索", category: "museum",
      latitude: 31.23, longitude: 121.47, coordinate_system: "WGS84", provider: "photon",
      source_url: "https://www.openstreetmap.org/node/98765", provider_provenance: "TEST_PROVIDER",
      region_status: "CONFLICT", opening_status: "UNKNOWN", cost_status: "UNKNOWN",
    }],
    research_areas: [],
    research_routes: [route],
    tool_steps: [{ run_id: "fixture-run", sequence_no: 1, tool_name: "route_public_places", status: "SUCCEEDED",
      result: { tool: "route_public_places", status: "ROUTE_READY", route, provider: "amap", provider_provenance: "LIVE_PROVIDER" } }],
    draft_artifact: { revision: 1, status: "DRAFT", days: [{ date: "2026-10-19", slots: [] }] },
  };

  await page.addInitScript(({ journeyId, taskId, owner, token }) => {
    sessionStorage.setItem("citynexus.traveler.bearer", token);
    sessionStorage.setItem("citynexus.traveler.session-id", owner);
    localStorage.setItem("citynexus.revolution.firstlook.journey", JSON.stringify({
      id: journeyId, ownerTravelerId: owner, cityCode: "TEST_FIXTURE", cityName: "TEST_FIXTURE 连城县", status: "DRAFT",
    }));
    localStorage.setItem(`citynexus.revolution.goal-task.${owner}.${journeyId}`, taskId);
  }, { journeyId, taskId, owner, token });

  await page.route("**/api/v1/**", async (requestRoute) => {
    const request = requestRoute.request();
    const path = new URL(request.url()).pathname;
    const reply = (value: unknown, status = 200) => requestRoute.fulfill({ status, contentType: "application/json", body: JSON.stringify(value) });
    if (path.startsWith(`/api/v1/journeys/${journeyId}`)) expect(request.headers().authorization).toBe(`Bearer ${token}`);
    if (path === "/api/v1/agent/runtime-status") return reply({ runtime_identity: "HERMES_COMPAT_ENDPOINT", hermes_compat_configured: true, ai_state: "CONFIGURED_UNVERIFIED" });
    if (path === "/api/v1/travelers/session") return reply({ traveler_id: owner });
    if (path === `/api/v1/journeys/${journeyId}`) return reply({ id: journeyId, title: "TEST_FIXTURE", status: "DRAFT", timezone: "Asia/Shanghai" });
    if (path === `/api/v1/journeys/${journeyId}/plans`) return reply([]);
    if (path === `/api/v1/journeys/${journeyId}/map-places`) return reply({ journey_id: journeyId, candidates: [] });
    if (path === `/api/v1/journeys/${journeyId}/planning-intent`) return reply({
      journey_id: journeyId,
      intent: { id: "fixture-intent", goal, interests: [], energy: "easy", updated_at: "2026-10-19T00:00:00Z", mapped_preferences: [] },
      trip: { dates: ["2026-10-19"], party_size: 1, budget: { amount_minor: 0, currency: "CNY" } }, candidates: [],
    });
    if (path === `/api/v1/journeys/${journeyId}/bootstrap-shortlist`) return reply({ journey_id: journeyId, pocket_walk: null });
    if (path === `/api/v1/journeys/${journeyId}/bootstrap-discovery/current`) return reply({ journey_id: journeyId, receipt_id: null, candidates: [] });
    if (path === `/api/v1/journeys/${journeyId}/agent/goal-tasks/${taskId}`) return reply(task);
    if (path === `/api/v1/journeys/${journeyId}/agent/goal-tasks/${taskId}/events`) return reply({
      task_id: taskId, events: [{ sequence: 1, event_type: "TOOL_SUCCEEDED", status: "PARTIAL_READY", run_id: "fixture-run",
        step_sequence_no: 1, model_turn_no: 1, tool_name: "route_public_places", reason_code: null, consent: null, budget: null }], next_cursor: null,
    });
    return reply({});
  });
  let tileRequests = 0;
  await page.route("https://tile.openstreetmap.org/**", async (tileRoute) => { tileRequests += 1; await tileRoute.abort(); });

  await page.goto("/revolution");
  await page.getByTestId("rev-mobile-tab-trips").click();
  await page.getByTestId("rev-mission-layer-agent").click();
  if (await page.getByTestId("rev-mission-layer-map").isVisible()) await page.getByTestId("rev-mission-layer-map").click();
  const cockpit = page.getByTestId("rev-mission-cockpit");
  const chatDock = page.getByRole("form", { name: "与当前旅行 Agent 对话" });
  await expect(chatDock).toBeVisible();
  for (const width of [390, 430, 1366]) {
    await page.setViewportSize({ width, height: 844 });
    const geometry = await chatDock.evaluate((dock) => {
      const row = dock.querySelector<HTMLElement>(".rev-mission-chat-row")!;
      const input = row.querySelector<HTMLTextAreaElement>("textarea")!;
      const submit = row.querySelector<HTMLButtonElement>('button[type="submit"]')!;
      const nav = document.querySelector<HTMLElement>(".rev-mobile-bottom-nav")!;
      const dockRect = dock.getBoundingClientRect();
      return {
        rowDisplay: getComputedStyle(row).display,
        rowWidth: row.clientWidth,
        rowScrollWidth: row.scrollWidth,
        inputWidth: input.getBoundingClientRect().width,
        submitWidth: submit.getBoundingClientRect().width,
        dockLeft: dockRect.left,
        dockRight: dockRect.right,
        dockBottom: dockRect.bottom,
        navTop: nav.getBoundingClientRect().top,
      };
    });
    expect(geometry.rowDisplay).toBe("grid");
    expect(geometry.inputWidth).toBeGreaterThan(0);
    expect(geometry.submitWidth).toBeGreaterThanOrEqual(44);
    expect(geometry.submitWidth).toBeLessThanOrEqual(80);
    expect(geometry.rowScrollWidth).toBeLessThanOrEqual(geometry.rowWidth);
    expect(geometry.dockLeft).toBeGreaterThanOrEqual(0);
    expect(geometry.dockRight).toBeLessThanOrEqual(width);
    expect(geometry.dockBottom).toBeLessThanOrEqual(geometry.navTop + 1);
  }
  await page.setViewportSize({ width: 390, height: 844 });
  const map = page.getByTestId("rev-mission-map-pane");
  await map.getByRole("button", { name: "查看其他研究（2）" }).click();
  await expect(map.getByTestId("rev-amap-research-leads")).toContainText("TEST_FIXTURE 连城县地点");
  await expect(map.getByTestId("rev-amap-research-leads")).toContainText("福建省 · 龙岩市 · 连城县");
  await expect(map).toContainText("TEST_FIXTURE 未归属 OSM 线索");
  await expect(map).not.toContainText("TEST_FIXTURE 明确冲突线索");
  await expect(map).toContainText("OpenStreetMap 地图地点 1 处 · 高德地点 1 处");
  await expect(map.getByRole("button", { name: "加载地图", exact: true })).toBeEnabled();
  expect(tileRequests).toBe(0);

  if (await page.getByTestId("rev-mission-layer-agent").isVisible()) await page.getByTestId("rev-mission-layer-agent").click();
  else await expect(cockpit.locator(".cn-mission-agent-disclosure")).toBeVisible();
  const taskRegion = cockpit.getByRole("region", { name: "Agent 任务", exact: true });
  await expect(taskRegion).toContainText("查询步行路线");
  await taskRegion.getByText("工具结果 · 1 次").click();
  await expect(taskRegion).toContainText("650 米 · 约 8 分钟");
  await taskRegion.locator("details").filter({ hasText: "待核实来源（2）" }).locator("summary").click();
  await expect(taskRegion.getByRole("link", { name: "在高德地图打开 ↗" })).toHaveAttribute("href", markerUrl);
  await taskRegion.getByText("高德转场路线（1）").click();
  await expect(taskRegion.getByTestId("rev-amap-research-route")).toContainText("TEST_FIXTURE 起点 → TEST_FIXTURE 终点");
  await expect(taskRegion.getByTestId("rev-amap-research-route")).toContainText("650 米 · 约 8 分钟");
  await expect(taskRegion.getByRole("link", { name: "在高德地图查看路线 ↗" })).toHaveAttribute("href", navigationUrl);

  if (await page.getByTestId("rev-mission-layer-map").isVisible()) await page.getByTestId("rev-mission-layer-map").click();
  await map.getByRole("button", { name: "加载地图", exact: true }).click();
  await expect(map.getByTestId("rev-workspace-map-canvas")).toBeVisible();
  await expect(map.locator(".rev-workspace-map-pin")).toHaveCount(1);
  await expect(map.getByTestId("rev-amap-research-leads").getByRole("link", { name: "在高德地图打开 ↗" })).toHaveAttribute("href", markerUrl);
  expect(tileRequests).toBeGreaterThan(0);
});
