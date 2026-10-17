import { expect, test, type Route } from "@playwright/test";

test.use({ viewport: { width: 390, height: 844 }, hasTouch: true, serviceWorkers: "block" });

const journeyId = "00000000-0000-4000-8000-000000000224";
const journeyRoot = `**/api/v1/journeys/${journeyId}`;

async function json(route: Route, value: unknown) {
  await route.fulfill({
    status: 200,
    contentType: "application/json",
    body: JSON.stringify(value),
  });
}

test("TEST_FIXTURE signed member switch immediately clears the prior Hermes run and tool events", async ({ page }) => {
  // These intercepted payloads exercise UI clearing only; they are not AgentRun evidence.
  const runId = "fixture-member-a-hermes-run";
  const fixtureToolEvent = {
    event_type: "tool.started",
    run_id: runId,
    event_id: "fixture-member-a-tool-event",
    sequence: 1,
    tool_name: "inspect_journey",
    status: "started",
    timestamp: "2026-10-17T00:00:01Z",
    source: "HERMES_NATIVE",
  };
  const fixtureTerminalEvent = {
    event_type: "run.completed",
    run_id: runId,
    event_id: "fixture-member-a-terminal-event",
    sequence: 2,
    tool_name: null,
    status: "completed",
    timestamp: "2026-10-17T00:00:02Z",
    source: "HERMES_NATIVE",
  };
  const fixtureRun = {
    run_id: runId,
    status: "running",
    runtime_identity: "HERMES_NATIVE_MCP",
    provider_key: "TEST_FIXTURE_MEMBER_A",
    mission_id: "test-fixture-only",
    reasoning_summary: "仅用于验证成员切换时清除界面状态。",
    events_url: `/api/v1/journeys/${journeyId}/agent/hermes/runs/${runId}/events`,
    timeline_url: `/api/v1/journeys/${journeyId}/agent/hermes/runs/${runId}/timeline`,
    initial_events: [],
  };
  let memberSwitched = false;
  let signalMemberBRestore: (() => void) | undefined;
  let releaseMemberBRestore: (() => void) | undefined;
  const memberBRestoreStarted = new Promise<void>((resolve) => {
    signalMemberBRestore = resolve;
  });
  const memberBRestoreGate = new Promise<void>((resolve) => {
    releaseMemberBRestore = resolve;
  });

  await page.addInitScript((id) => {
    window.sessionStorage.setItem("citynexus.traveler.bearer", "TEST_FIXTURE_MEMBER_A");
    window.localStorage.setItem("citynexus.locale", "zh-CN");
    window.localStorage.setItem("citynexus.revolution.firstlook.journey", JSON.stringify({
      id,
      cityCode: "CN-RV-HERMES-FIXTURE",
      cityName: "测试地区",
      status: "ACTIVE",
    }));
  }, journeyId);

  await page.route("**/api/v1/**", (route) => route.abort());
  await page.route("**/api/v1/agent/runtime-status", (route) => json(route, {
    runtime_identity: "TEST_FIXTURE",
    hermes_native_gateway: { configured: true, reachable: true, ready: true, runs: true, events: true },
    hermes_compat_configured: false,
    ai_state: "DISABLED",
  }));
  await page.route(`${journeyRoot}/agent/hermes/latest-run`, async (route) => {
    if (memberSwitched) {
      signalMemberBRestore?.();
      await memberBRestoreGate;
      await json(route, { journey_id: journeyId, run: null });
      return;
    }
    await json(route, { journey_id: journeyId, run: fixtureRun });
  });
  await page.route(`${journeyRoot}/agent/hermes/runs/${runId}/timeline`, (route) => json(route, {
    run_id: runId,
    journey_id: journeyId,
    runtime_identity: "HERMES_NATIVE_MCP",
    events: [fixtureToolEvent],
    observability: {
      run_id: runId,
      runtime_identity: "HERMES_NATIVE_MCP",
      current_mission: "test-fixture-only",
      tool_count: 1,
      current_tool: "inspect_journey",
      completion_status: "running",
      gateway_decision: null,
      guardian_decision: null,
      total_duration_ms: 0,
    },
  }));
  await page.route(`${journeyRoot}/agent/hermes/runs/${runId}/events`, (route) => route.fulfill({
    status: 200,
    contentType: "text/event-stream",
    body: `event: run.completed\r\ndata: ${JSON.stringify(fixtureTerminalEvent)}\r\n\r\n`,
  }));

  await page.goto("/revolution");
  await page.getByTestId("rev-mobile-tab-trips").click();
  const hermes = page.getByTestId("rev-mobile-hermes");
  const run = hermes.getByTestId("rev-mobile-hermes-run");
  await expect(run).toBeVisible();
  await expect(run).toContainText("示例事件");
  await hermes.getByRole("button", { name: "查看工作过程" }).click();
  const sheet = hermes.getByTestId("rev-mobile-hermes-sheet");
  await expect(sheet).toBeVisible();
  await expect(sheet).toContainText("测试数据");
  const toolEvents = sheet.getByRole("list", { name: "Hermes 工具调用记录" });
  await expect(toolEvents).toContainText("正在检查当前行程");

  memberSwitched = true;
  await page.evaluate(() => {
    window.sessionStorage.setItem("citynexus.traveler.bearer", "TEST_FIXTURE_MEMBER_B");
    window.dispatchEvent(new CustomEvent("citynexus.traveler.bearer.changed"));
  });
  try {
    await memberBRestoreStarted;
    await expect(run).toHaveCount(0);
    await expect(toolEvents).toHaveCount(0);
    await expect(sheet).toHaveCount(0);
    await expect(hermes).not.toContainText("正在检查当前行程");
  } finally {
    releaseMemberBRestore?.();
  }

  await expect(hermes.getByTestId("rev-mobile-hermes-empty-state")).toContainText("暂无助手运行记录。");
  await expect(hermes.getByTestId("rev-mobile-hermes-run")).toHaveCount(0);
  await expect(hermes).not.toContainText("正在检查当前行程");
});
