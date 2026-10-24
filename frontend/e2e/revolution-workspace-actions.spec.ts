import { expect, test, type Page } from "@playwright/test";

const journeyId = "00000000-0000-4000-8000-000000000921";
const taskId = "00000000-0000-4000-8000-000000000922";
const owner = "REFORM_FIXTURE_OWNER";
const token = "REFORM_TEST_FIXTURE_TOKEN";
const goal = "两人旅行，少走路，下午出发。";

async function fixture(page: Page, failRuntime = false, cachedSource = false) {
  const submittedGoals: string[] = [];
  const persistedTask: Record<string, unknown> = {
    task_id: taskId,
    journey_id: journeyId,
    mode: "GOAL_PLANNING",
    status: "PARTIAL_READY",
    goal,
    consent: { model: true, online_research: true },
    budget: { max_model_turns: 24, max_tool_calls: 48 },
    usage: { model_turns: 2, tool_calls: 2 },
    latest_run_id: "00000000-0000-4000-8000-000000000923",
    candidate_place_ids: ["test-place-one"],
    source_observation_ids: [],
    candidate_places: [{
      id: "test-place-one", name: "TEST_FIXTURE 待核实文化地点", category: "museum/gallery",
      city_code: "TEST_FIXTURE", provider_key: "TEST_FIXTURE",
      opening_state: "UNKNOWN", cost_evidence: { status: "UNKNOWN", amount_minor: null },
    }],
    tool_steps: [
      { run_id: "00000000-0000-4000-8000-000000000923", sequence_no: 1,
        tool_name: "search_city_services", status: "SUCCEEDED", result: { place_count: 0, reason_code: "NO_RESULTS" } },
      { run_id: "00000000-0000-4000-8000-000000000923", sequence_no: 2,
        tool_name: "research_place_sources", status: "SUCCEEDED", result: cachedSource
          ? { status: "CACHED_ONLY", cached_references: [{ url: "https://www.openstreetmap.org/way/12345" }] }
          : { observation_ids: ["test-observation-1"] } },
    ],
    assistant_summary: "TEST_FIXTURE 已保存一处待核实地点。",
    draft_artifact: { revision: 1, status: "DRAFT", days: [
      { date: "2026-10-19", slots: [{title: "TEST_FIXTURE 下午文化行程", time_of_day: "afternoon", notes: "营业待查"}] },
      { date: "2026-10-20", slots: [] },
    ] },
    failure_code: null,
  };
  const persistedEvents = [
    { sequence: 1, event_type: "RUN_STARTED", status: "WORKING", run_id: persistedTask.latest_run_id, step_sequence_no: null, model_turn_no: 1, tool_name: null, reason_code: null, consent: null, budget: null },
    { sequence: 2, event_type: "TOOL_SUCCEEDED", status: "PARTIAL_READY", run_id: persistedTask.latest_run_id, step_sequence_no: 1, model_turn_no: 1, tool_name: "search_city_services", reason_code: "NO_RESULTS", consent: null, budget: null },
    { sequence: 3, event_type: "TOOL_SUCCEEDED", status: "PARTIAL_READY", run_id: persistedTask.latest_run_id, step_sequence_no: 2, model_turn_no: 2, tool_name: "research_place_sources", reason_code: null, consent: null, budget: null },
    { sequence: 4, event_type: "TASK_PARTIAL_READY", status: "PARTIAL_READY", run_id: persistedTask.latest_run_id, step_sequence_no: null, model_turn_no: null, tool_name: null, reason_code: null, consent: null, budget: null },
  ];
  await page.addInitScript(({ journeyId, owner, token }) => {
    sessionStorage.setItem("citynexus.traveler.bearer", token);
    sessionStorage.setItem("citynexus.traveler.session-id", owner);
    localStorage.setItem("citynexus.revolution.firstlook.journey", JSON.stringify({
      id: journeyId, ownerTravelerId: owner, cityCode: "TEST_FIXTURE", cityName: "TEST_FIXTURE", status: "DRAFT",
    }));
  }, { journeyId, owner, token });
  const root = `/api/v1/journeys/${journeyId}`;
  await page.route("**/api/v1/**", async (route) => {
    const request = route.request();
    const path = new URL(request.url()).pathname;
    const reply = (data: unknown, status = 200) => route.fulfill({ status, contentType: "application/json", body: JSON.stringify(data) });
    if (path === "/api/v1/agent/runtime-status") {
      return reply({ runtime_identity: "HERMES_COMPAT_ENDPOINT", hermes_compat_configured: true, ai_state: "CONFIGURED_UNVERIFIED" }, failRuntime ? 503 : 200);
    }
    if (path === "/api/v1/travelers/session") return reply({ traveler_id: owner });
    if (path.startsWith(root)) expect(request.headers().authorization).toBe(`Bearer ${token}`);
    if (path === root) return reply({ id: journeyId, title: "TEST_FIXTURE", status: "DRAFT", timezone: "Asia/Shanghai" });
    if (path === `${root}/plans`) return reply([]);
    if (path === `${root}/map-places`) return reply({journey_id: journeyId, candidates: [{
      candidate_id: "test-map-archived", name: "TEST_FIXTURE 上次搜索地点", latitude: 25.037, longitude: 121.563,
      coordinate_system: "WGS84", observation_expired: true, selection_state: "OPENING_UNVERIFIED",
      provider_provenance: "TEST_PROVIDER", source_url: "https://www.openstreetmap.org/way/12345",
    }, {
      candidate_id: "test-map-foreign", name: "TEST_FIXTURE 上海浦东", latitude: 31.23, longitude: 121.47,
      coordinate_system: "WGS84", observation_expired: false, selection_state: "REGION_CONFLICT",
      region_status: "CONFLICT", provider_provenance: "LIVE_PROVIDER", source_url: "https://www.openstreetmap.org/node/98765",
    }]});
    if (path === `${root}/planning-intent`) return reply({
      journey_id: journeyId, intent: { id: "test-intent", goal, interests: [], energy: "easy", updated_at: "2026-10-18T00:00:00Z", mapped_preferences: [] },
      trip: { dates: ["2026-10-19", "2026-10-20"], party_size: 2, budget: { amount_minor: 100000, currency: "CNY" } },
      candidates: [{ candidate_id: "test-place-one", name: "TEST_FIXTURE 未核实公园", latitude: 25.037, longitude: 121.563,
        coordinate_system: "WGS84", selection_state: "OPENING_UNVERIFIED", provider_provenance: "TEST_PROVIDER",
        price_state: "UNKNOWN", opening_hours: {}, selection_blockers: ["OPENING_UNVERIFIED", "COST_UNKNOWN"] }],
    });
    if (path === `${root}/bootstrap-shortlist`) return reply({ journey_id: journeyId, pocket_walk: null });
    if (path === `${root}/bootstrap-discovery/current`) return reply({ journey_id: journeyId, receipt_id: null, candidates: [] });
    if (path === `${root}/agent/goal-tasks` && request.method() === "POST") {
      const payload = request.postDataJSON();
      expect(payload).toMatchObject({ goal: goal + "\n节奏：轻松少走", model_consent: true, online_research_consent: true, interaction_mode: "DISCUSS", unlimited_research: true });
      submittedGoals.push(payload.goal);
      return reply({ ...persistedTask, status: "ACCEPTED", assistant_summary: null, tool_steps: [] }, 201);
    }
    if (path === `${root}/agent/goal-tasks/${taskId}/run`) {
      const payload = request.postDataJSON();
      expect(payload).toMatchObject({ model_consent: true, online_research_consent: true, interaction_mode: "DISCUSS", unlimited_research: true });
      return reply(persistedTask);
    }
    if (path === `${root}/agent/goal-tasks/${taskId}`) return reply(persistedTask);
    if (path === `${root}/agent/goal-tasks/${taskId}/draft` && request.method() === "PUT") {
      const input = request.postDataJSON();
      persistedTask.draft_artifact = { revision: input.expected_revision + 1, status: "DRAFT", days: input.days };
      return reply(persistedTask);
    }
    if (path === `${root}/agent/goal-tasks/${taskId}/events`) return reply({ task_id: taskId, events: persistedEvents, next_cursor: null });
    if (path === `${root}/agent/goal-tasks/${taskId}/cancel`) return reply({ ...persistedTask, status: "CANCELLED" });
    if (path === `${root}/trial-ai-discovery`) {
      expect(request.method()).toBe("POST");
      submittedGoals.push(request.postDataJSON().goal);
      return reply({ status: "MODEL_TOOL_SUGGESTION", evidence: "TEST_FIXTURE", reason: "TEST_FIXTURE" });
    }
    return reply({});
  });
  return submittedGoals;
}

for (const width of [390, 430, 1366]) {
  test(`TEST_FIXTURE goal task starts from Trips at ${width}, persists its trace, and does not run on open`, async ({ page }) => {
    await page.setViewportSize({ width, height: 900 });
    const calls = await fixture(page);
    await page.goto("/revolution");
    await page.getByTestId("rev-mobile-tab-trips").click();
    await page.getByTestId("rev-mission-layer-agent").click();
    const dialog = page.getByTestId("rev-mission-cockpit");
    await expect(dialog).toBeVisible();
    await expect(page.locator("dialog[open]")).toHaveCount(0);
    if (width === 1366) {
      await page.getByTestId("rev-mission-layer-map").click();
      const m = await page.getByTestId("rev-mission-map-pane").boundingBox();
      const t = await page.getByTestId("rev-mission-timeline-pane").boundingBox();
      expect(m!.x).toBeLessThan(t!.x);
      await page.getByTestId("rev-mission-layer-agent").click();
    }
    const chatDock = page.getByRole("form", { name: "与当前旅行 Agent 对话" });
    const chatInput = chatDock.locator("#rev-mission-chat-input");
    await expect(chatDock).toBeVisible();
    await expect(chatInput).toBeVisible();
    await expect(chatInput).toHaveValue(goal + "\n节奏：轻松少走");
    expect(calls).toEqual([]);
    await chatDock.getByRole("button", { name: "对话设置", exact: true }).click();
    await chatDock.getByLabel("本次允许 AI 处理旅行目标（可能产生费用）").check();
    await expect(chatDock.getByLabel("本次允许 AI 处理旅行目标（可能产生费用）")).toBeChecked();
    await chatDock.getByLabel("本次允许查询公开地图和地点来源").check();
    await expect(chatDock.getByLabel("本次允许查询公开地图和地点来源")).toBeChecked();
    await chatDock.getByRole("button", { name: "关闭对话设置" }).click();
    await chatDock.getByRole("button", { name: "发送 ↑", exact: true }).click();
    if (await page.getByTestId("rev-mission-layer-agent").isVisible()) await page.getByTestId("rev-mission-layer-agent").click();
    else await expect(dialog.locator(".cn-mission-agent-disclosure")).toBeVisible();
    await expect(dialog.getByRole("region", { name: "Agent 任务" })).toContainText("TEST_FIXTURE 已保存一处待核实地点。");
    expect(calls).toEqual([goal + "\n节奏：轻松少走"]);
    if (width !== 1366) {
      await page.getByTestId("rev-mission-layer-timeline").click();
      await expect(page.getByTestId("rev-mission-timeline-pane")).toBeVisible();
      await expect(page.getByTestId("rev-mission-map-pane")).toBeHidden();
      await expect(page.getByTestId("rev-mission-layer-timeline")).toHaveAttribute("aria-pressed", "true");
      await page.getByTestId("rev-mission-layer-map").click();
      await expect(page.getByTestId("rev-mission-map-pane")).toBeVisible();
      await expect(page.getByTestId("rev-mission-timeline-pane")).toBeHidden();
    }
    if (width !== 1366) await page.getByTestId("rev-mission-layer-agent").click();
    await dialog.getByRole("button", { name: "刷新任务", exact: true }).click();
    await expect(dialog.getByRole("region", { name: "Agent 任务" })).toContainText("搜索城市地点");
    await expect(dialog.getByRole("region", { name: "Agent 任务" })).toContainText("1 条来源记录");
    await expect(dialog.getByText("Agent 真实工作过程", { exact: false })).toBeVisible();
    await page.getByTestId("rev-mission-layer-timeline").click();
    await dialog.locator(".rev-goal-draft-slot summary").first().click();
    await dialog.getByLabel("安排", { exact: true }).fill("TEST_FIXTURE 改为下午三点出发");
    await dialog.getByRole("button", { name: "＋ 添加安排" }).first().click();
    await dialog.getByRole("button", { name: "保存草案", exact: true }).click();
    await expect(dialog).toContainText("草案已保存");
    const reloadStarted = Date.now();
    await page.reload();
    console.log(`RELOAD_MS width=${width} ms=${Date.now() - reloadStarted}`);
    await page.getByTestId("rev-mobile-tab-trips").click();
    await page.getByTestId("rev-mission-layer-agent").click();
    const restoredDialog = page.getByTestId("rev-mission-cockpit");
    if (await page.getByTestId("rev-mission-layer-agent").isVisible()) await page.getByTestId("rev-mission-layer-agent").click();
    else await expect(restoredDialog.locator(".cn-mission-agent-disclosure")).toBeVisible();
    await expect(restoredDialog.getByRole("region", { name: "Agent 任务" })).toContainText("TEST_FIXTURE 已保存一处待核实地点。");
    await expect(restoredDialog.getByRole("region", { name: "Agent 任务" })).toContainText("搜索城市地点");
    await page.getByTestId("rev-mission-layer-timeline").click();
    await restoredDialog.locator(".rev-goal-draft-slot summary").first().click();
    await expect(restoredDialog.getByLabel("安排", { exact: true })).toHaveValue("TEST_FIXTURE 改为下午三点出发");
    expect(calls).toEqual([goal + "\n节奏：轻松少走"]);
    await page.getByTestId("rev-mobile-tab-me").click();
    await expect(restoredDialog).not.toBeVisible();
  });
}

test("TEST_FIXTURE unknown hours and unavailable AI do not hide the map's saved places", async ({ page }) => {
  const calls = await fixture(page, true);
  let tiles = 0;
  await page.route("https://tile.openstreetmap.org/**", (route) => { tiles += 1; return route.abort(); });
  await page.goto("/revolution");
  await page.getByTestId("rev-mobile-tab-trips").click();
  await page.getByTestId("rev-mission-layer-map").click();
  const dialog = page.getByTestId("rev-mission-cockpit");
  await expect(dialog).toContainText("TEST_FIXTURE 上次搜索地点");
  await expect(dialog).not.toContainText("TEST_FIXTURE 上海浦东");
  await expect(dialog).toContainText("上次搜索的地点，营业与费用需更新");
  await expect(dialog.getByRole("link", {name: "查看地点来源 ↗"})).toHaveAttribute("href", "https://www.openstreetmap.org/way/12345");
  await expect(dialog.getByRole("button", { name: "加载地图", exact: true })).toBeEnabled();
  expect(calls).toEqual([]);
  expect(tiles).toBe(0);
});

test("TEST_FIXTURE identity change clears the open private assistant immediately", async ({ page }) => {
  await fixture(page);
  await page.goto("/revolution");
  await page.getByTestId("rev-mission-layer-agent").click();
  const dialog = page.getByTestId("rev-mission-cockpit");
  const chatDock = page.getByRole("form", { name: "与当前旅行 Agent 对话" });
  const chatInput = chatDock.locator("#rev-mission-chat-input");
  await expect(chatDock).toBeVisible();
  await expect(chatInput).toBeVisible();
  await expect(chatInput).toHaveValue(goal + "\n节奏：轻松少走");
  await page.evaluate(() => {
    sessionStorage.removeItem("citynexus.traveler.bearer");
    sessionStorage.removeItem("citynexus.traveler.session-id");
    window.dispatchEvent(new Event("storage"));
  });
  await expect(chatDock).toHaveCount(0);
  await expect(dialog).not.toContainText(goal);
});

test("TEST_FIXTURE cached public source is readable without starting a new research request", async ({ page }) => {
  const writes = await fixture(page, false, true);
  await page.addInitScript(({ owner, journeyId, taskId }) => {
    localStorage.setItem(`citynexus.revolution.goal-task.${owner}.${journeyId}`, taskId);
  }, { owner, journeyId, taskId });
  await page.goto("/revolution");
  if (await page.getByTestId("rev-mission-layer-agent").isVisible()) await page.getByTestId("rev-mission-layer-agent").click();
  else await expect(page.locator(".cn-mission-agent-disclosure")).toBeVisible();
  const task = page.getByRole("region", { name: "Agent 任务", exact: true });
  await task.getByText("工具结果 · 2 次").click();
  await expect(task.getByText("已读取 1 条已有地点来源")).toBeVisible();
  expect(writes).toEqual([]);
});

test("TEST_FIXTURE map focuses draft references and separates regions from venues", async ({ page }) => {
  const writes = await fixture(page);
  await page.addInitScript(({ owner, journeyId, taskId }) => {
    localStorage.setItem(`citynexus.revolution.goal-task.${owner}.${journeyId}`, taskId);
  }, { owner, journeyId, taskId });
  const lead = (id: string, name: string, category: string, region_status: string) => ({
    id, name, category, region_status, latitude: 26.9, longitude: 119.0,
    source_url: "https://www.openstreetmap.org/node/12345", provider_provenance: "TEST_PROVIDER",
    opening_status: "UNKNOWN", cost_status: "UNKNOWN",
  });
  await page.route(`**/api/v1/journeys/${journeyId}/agent/goal-tasks/${taskId}`, (route) => route.fulfill({
    status: 200, contentType: "application/json", body: JSON.stringify({
      task_id: taskId, journey_id: journeyId, mode: "GOAL_PLANNING", goal, status: "PARTIAL_READY",
      consent: { model: true, online_research: true }, budget: { max_model_turns: 8, max_tool_calls: 16 }, usage: {},
      latest_run_id: null, candidate_place_ids: [], source_observation_ids: [], failure_code: null,
      research_places: [lead("museum", "TEST_FIXTURE 博物馆", "museum", "MATCHED"),
        lead("village", "TEST_FIXTURE 古村落", "district", "UNKNOWN"),
        lead("address", "TEST_FIXTURE 旧地址定位", "house", "UNKNOWN"),
        lead("foreign", "TEST_FIXTURE 其他县同名结果", "museum", "CONFLICT")],
      draft_artifact: { revision: 1, status: "DRAFT", days: [{ date: "2026-10-19", slots: [
        { title: "TEST_FIXTURE 村落散步", time_of_day: "afternoon", notes: "", place_id: "village" }]}] },
    }),
  }));
  await page.goto("/revolution");
  const map = page.getByTestId("rev-mission-map-pane");
  await expect(map.locator(".cn-mission-map-top")).toContainText("1 处地点");
  await expect(map).toContainText("TEST_FIXTURE 古村落");
  await expect(map).not.toContainText("TEST_FIXTURE 其他县同名结果");
  await expect(map.locator(".rev-workspace-place-list")).toContainText("地区／村落线索");
  await expect(page.locator("summary").filter({ hasText: "待核实来源（2）" })).toHaveCount(1);
  await expect(page.locator("summary").filter({ hasText: "其他地区候选（1）" })).toHaveCount(1);
  await map.getByRole("button", { name: "查看其他研究（3）" }).click();
  await expect(map).toContainText("TEST_FIXTURE 博物馆");
  await expect(map).not.toContainText("TEST_FIXTURE 其他县同名结果");
  expect(writes).toEqual([]);
});
