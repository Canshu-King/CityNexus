import { expect, test } from "@playwright/test";

for (const width of [390, 430, 1366]) test(`TEST_FIXTURE discuss, choose, explicitly research without quotas at ${width}`, async ({ page }) => {
  await page.setViewportSize({ width, height: 932 });
  const jid = "00000000-0000-4000-8000-000000000981", tid = "00000000-0000-4000-8000-000000000982", owner = "DISCUSSION_FIXTURE_OWNER";
  await page.addInitScript(({ jid, tid, owner }) => {
    sessionStorage.setItem("citynexus.traveler.bearer", "DISCUSSION_FIXTURE_BEARER");
    sessionStorage.setItem("citynexus.traveler.session-id", owner);
    localStorage.setItem("citynexus.revolution.firstlook.journey", JSON.stringify({ id: jid, ownerTravelerId: owner, cityCode: "CN-TEST", cityName: "广州", status: "DRAFT" }));
    localStorage.setItem(`citynexus.revolution.goal-task.${owner}.${jid}`, tid);
  }, { jid, tid, owner });
  const root = `/api/v1/journeys/${jid}`;
  const writes: Record<string, unknown>[] = [];
  let task = { task_id: tid, journey_id: jid, status: "NEEDS_DECISION", goal: "TEST_FIXTURE 广州轻松游", mode: "GOAL_PLANNING",
    interaction_mode: "DISCUSS", consent: { model: true, online_research: false }, budget: { max_model_turns: 1, max_tool_calls: 0 },
    usage: { model_turns: 1, tool_calls: 1 }, tool_steps: [], research_places: [],
    conversation: [{ role: "assistant", text: "这次更想看江景，还是室内慢逛？", message_id: "question" }],
    pending_question: { id: "question", question: "这次更想看江景，还是室内慢逛？", options: [
      { label: "江边休息", description: "少走路，留更多休息时间" }, { label: "室内慢逛", description: "先比较博物馆和展馆" }] },
  };
  await page.route("**/api/v1/**", async route => {
    const req = route.request(), path = new URL(req.url()).pathname;
    const reply = (body: unknown) => route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(body) });
    if (path === "/api/v1/travelers/session") return reply({ traveler_id: owner });
    if (path === "/api/v1/agent/runtime-status") return reply({ ai_state: "CONFIGURED_UNVERIFIED", hermes_compat_configured: true });
    if (path === root) return reply({ id: jid, status: "DRAFT" });
    if (path === root + "/plans") return reply([]);
    if (path === root + "/map-places") return reply({ journey_id: jid, candidates: [] });
    if (path === root + "/planning-intent") return reply({ journey_id: jid, intent: null, candidates: [], trip: { dates: ["2026-10-21"], party_size: 1, budget: { amount_minor: 50000, currency: "CNY" } } });
    if (path === `${root}/agent/goal-tasks/${tid}/resume`) {
      const payload = req.postDataJSON(); writes.push(payload);
      expect(req.headers().authorization).toBe("Bearer DISCUSSION_FIXTURE_BEARER");
      expect(payload.unlimited_research).toBe(true);
      expect(payload).not.toHaveProperty("max_model_turns"); expect(payload).not.toHaveProperty("max_tool_calls");
      if (payload.user_message === "江边休息") {
        task = { ...task, pending_question: null as never, conversation: [...task.conversation,
          { role: "user", text: payload.user_message, message_id: payload.message_id },
          { role: "assistant", text: "好的，先按江边休息来讨论，开始研究后再查地点。", message_id: "answer" }] };
      }
      task = { ...task, interaction_mode: payload.interaction_mode };
      return reply(task);
    }
    if (path === `${root}/agent/goal-tasks/${tid}`) return reply(task);
    if (path === `${root}/agent/goal-tasks/${tid}/events`) return reply({ task_id: tid, events: [] });
    return reply({});
  });
  await page.goto("/revolution");
  const input = page.locator("#rev-mission-chat-input");
  await expect(page.getByTestId("rev-mobile-bottom-nav").getByRole("button")).toHaveCount(3);
  await expect(input).toHaveCount(1);
  await page.getByTestId("rev-mobile-tab-trips").click();
  await expect(page.getByTestId("rev-mission-cockpit")).toHaveAttribute("data-space", "journey");
  await expect(page.getByTestId("rev-mission-timeline-pane")).toBeVisible();
  await expect(input).toBeVisible();
  await page.getByTestId("rev-mobile-tab-me").click();
  await expect(input).toBeVisible();
  await input.fill("我不想一直走路，先和我商量一下。");
  await page.getByRole("button", { name: "发送 ↑", exact: true }).click();
  await expect(page.getByRole("region", { name: "Agent 请你选择" })).toBeVisible();
  // While a question waits, the big "start research" control must not compete with the options:
  // pressing it re-runs the turn and asks the same question again (measured on the play stack,
  // six runs from one traveller pressing it instead of choosing).
  await expect(page.getByRole("button", { name: "按讨论的方向开始研究", exact: true })).toHaveCount(0);
  expect(writes[0].interaction_mode).toBe("DISCUSS");
  await page.getByRole("button", { name: "江边休息 少走路，留更多休息时间" }).click();
  await expect(page.getByRole("log", { name: "与 Agent 的真实对话" })).toContainText("好的，先按江边休息来讨论");
  expect(writes[1].interaction_mode).toBe("DISCUSS");
  await page.getByRole("button", { name: "按讨论的方向开始研究", exact: true }).click();
  await expect.poll(() => writes.length).toBe(3);
  expect(writes[2].interaction_mode).toBe("RESEARCH");
  await input.fill("想轻松一点，多一点休息时间。".repeat(10));
  const height = await input.evaluate(e => e.getBoundingClientRect().height);
  expect(height).toBeGreaterThan(48); expect(height).toBeLessThanOrEqual(132);
  await page.getByRole("button", { name: "对话设置", exact: true }).click();
  await expect(page.getByText("研究工作量", { exact: true })).toHaveCount(0);
  await page.getByRole("button", { name: "关闭对话设置", exact: true }).click();
  await page.reload();
  await page.getByTestId("rev-mission-layer-agent").click();
  await expect(page.getByRole("log", { name: "与 Agent 的真实对话" })).toContainText("江边休息");
  expect(writes).toHaveLength(3);
  expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(width);
});
