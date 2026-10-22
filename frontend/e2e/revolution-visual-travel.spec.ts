import { expect, test } from "@playwright/test";

const jid = "00000000-0000-4000-8000-000000000991";
const tid = "00000000-0000-4000-8000-000000000992";
const owner = "VISUAL_TEST_FIXTURE_OWNER";

for (const width of [390, 430, 1366, 1566]) {
  test("TEST_FIXTURE: visual travel cards, grounded photos, map preview and persistent chat at " + width, async ({ page }) => {
    await page.setViewportSize({ width, height: 932 });
    await page.addInitScript(({ jid, tid, owner }) => {
      sessionStorage.setItem("citynexus.traveler.bearer", "VISUAL_TEST_FIXTURE_TOKEN");
      sessionStorage.setItem("citynexus.traveler.session-id", owner);
      localStorage.setItem("citynexus.revolution.firstlook.journey", JSON.stringify({
        id: jid, ownerTravelerId: owner, cityCode: "CN-TEST", cityName: "连城县", status: "DRAFT",
      }));
      localStorage.setItem("citynexus.revolution.goal-task." + owner + "." + jid, tid);
    }, { jid, tid, owner });

    const point = {
      candidate_id: "photon:W/846486126", name: "冠豸山风景区", latitude: 25.7158,
      longitude: 116.7757, coordinate_system: "WGS84", provider_provenance: "LIVE_PROVIDER",
      provider: "photon", selection_state: "OPENING_UNVERIFIED", source_url: "https://www.openstreetmap.org/way/846486126",
      region_status: "UNKNOWN", observation_expired: false,
    };
    const task = {
      task_id: tid, journey_id: jid, status: "PARTIAL_READY",
      goal: "连城两天，少走路", mode: "GOAL_PLANNING",
      consent: { model: true, online_research: true },
      budget: { max_model_turns: 24, max_tool_calls: 48 },
      usage: { model_turns: 3, tool_calls: 2 },
      tool_steps: [], research_places: [],
      conversation: [
        { role: "assistant", text: "**已把第二天下午改成湖边散步**\n- 上午：博物馆\n- 下午：湖边", message_id: "fixture-claim", at: "2026-10-21T09:00:00+08:00",
          draft_revision_before: 3, draft_revision_after: 3 },
        { role: "assistant", text: "已重排第二天", message_id: "fixture-write", at: "2026-10-21T09:10:00+08:00",
          draft_revision_before: 2, draft_revision_after: 3 },
      ],
      draft_artifact: {
        revision: 3, status: "DRAFT",
        days: [{ date: "2026-10-21", slots: [{ title: "冠豸山风景区", place_id: point.candidate_id, time_of_day: "morning", notes: "缓慢步行" }] }],
      },
      draft_variants: ["relaxed", "budget", "local"].map((id, index) => ({
        id, title: ["轻松版", "省钱版", "特色版"][index],
        comparison: "有真实来源地点的两日安排。你可以按自己的偏好来挑选，然后继续修改。",
        source_place_ids: [point.candidate_id], route_ids: [], unknown_summary: ["营业时间待查"],
        artifact: {
          revision: 1, status: "DRAFT",
          days: [{ date: "2026-10-21", slots: [{ title: "冠豸山风景区", place_id: point.candidate_id, time_of_day: "morning", notes: "暂定" }] }],
        },
      })),
    };
    const base = "/api/v1/journeys/" + jid;
    let externalTiles = 0;
    await page.route("https://tile.openstreetmap.org/**", async (route) => {
      externalTiles += 1; await route.abort();
    });
    await page.route("https://commons.wikimedia.org/**", async (route) => {
      await route.abort();
    });
    await page.route("**/api/v1/**", async (route) => {
      const path = new URL(route.request().url()).pathname;
      const reply = (value: unknown) => route.fulfill({
        status: 200, contentType: "application/json", body: JSON.stringify(value),
      });
      if (path === "/api/v1/travelers/session") return reply({ traveler_id: owner });
      if (path === "/api/v1/agent/runtime-status") return reply({ ai_state: "CONFIGURED_UNVERIFIED", hermes_compat_configured: true });
      if (path === base) return reply({ id: jid, status: "DRAFT", timezone: "Asia/Shanghai", title: "连城旅行" });
      if (path === base + "/plans") return reply([]);
      if (path === base + "/map-places") return reply({ journey_id: jid, candidates: [point,
        { ...point, candidate_id: "photon:W/fixture-neighbor", name: "TEST_FIXTURE 相邻地点", longitude: 116.77571 },
        { ...point, candidate_id: "photon:W/fixture-distant", name: "冠豸山风景区", longitude: 116.70, latitude: 25.63 },
      ] });
      if (path === base + "/planning-intent") return reply({
        journey_id: jid, intent: null, candidates: [],
        trip: { dates: ["2026-10-21", "2026-10-22"], party_size: 1, budget: { amount_minor: 100000, currency: "CNY" } },
      });
      if (path === base + "/bootstrap-shortlist") return reply({ journey_id: jid, pocket_walk: null });
      if (path === base + "/bootstrap-discovery/current") return reply({ journey_id: jid, candidates: [], receipt_id: null });
      if (path === base + "/agent/goal-tasks/" + tid) return reply(task);
      if (path === base + "/agent/goal-tasks/" + tid + "/events") return reply({ task_id: tid, events: [], next_cursor: null });
      return reply({});
    });

    await page.goto("/revolution");
    await page.getByTestId("rev-mission-layer-agent").click();
    await page.getByTestId("rev-mission-layer-map").click();
    const cockpit = page.getByTestId("rev-mission-cockpit");
    await expect(cockpit).toBeVisible();
    await expect(page.locator(".cn-mission-media")).toBeVisible();
    await expect(cockpit.getByRole("region", { name: "与研究地点对应的真实景点照片" })).toContainText("冠豸山");
    await expect(cockpit.locator('.cn-place-photo[data-photo-origin="curated"]')).toHaveCount(1);
    await expect(cockpit.locator(".cn-place-photo-meta a").first()).toHaveAttribute("href", /commons\.wikimedia\.org/);
    await expect(cockpit.locator('.cn-place-photo[data-photo-origin="curated"] .cn-place-photo-fallback')).toBeVisible();
    await cockpit.locator(".cn-place-photo").getByRole("button", { name: "查看对应安排" }).click();
    await expect(cockpit.locator('.rev-goal-draft-slot[data-place-id="' + point.candidate_id + '"]')).toHaveAttribute("open", "");
    await page.getByTestId("rev-mission-layer-map").click();
    await expect(cockpit.getByTestId("rev-workspace-coordinate-preview")).toBeVisible();
    await cockpit.getByRole("button", { name: /查看其他研究/ }).click();
    await expect(cockpit.locator(".cn-mission-map-top")).toContainText("3 处地点");
    await expect(cockpit.locator(".rev-workspace-preview-pin")).toHaveCount(2);
    expect(externalTiles).toBe(0);
    await cockpit.getByRole("button", { name: "展开相邻 2 处地点" }).click();
    await expect(cockpit.getByRole("group", { name: "相邻地点" })).toBeVisible();
    await cockpit.getByRole("group", { name: "相邻地点" }).getByRole("button", { name: /冠豸山风景区/ }).click();
    await expect(cockpit.locator('.rev-goal-draft-slot[data-place-id="' + point.candidate_id + '"]')).toHaveAttribute("open", "");
    if (width < 1000) await page.getByTestId("rev-mission-layer-timeline").click();

    const options = cockpit.getByRole("region", { name: "旅行方案对比" });
    await expect(options.locator(".rev-goal-variant-card")).toHaveCount(3);
    const layout = await options.evaluate((element) => {
      const list = element.querySelector(".rev-goal-variants-list")!.getBoundingClientRect();
      const card = element.querySelector(".rev-goal-variant-card")!.getBoundingClientRect();
      return { list: list.width, card: card.width };
    });
    expect(layout.card).toBeGreaterThan(layout.list * 0.82);
    const font = await options.locator("h4").first().evaluate(e => parseFloat(getComputedStyle(e).fontSize));
    expect(font).toBeGreaterThanOrEqual(16);
    await expect(cockpit.locator(".cn-mission-agent-disclosure")).not.toHaveAttribute("open", "");
    await expect(page.locator(".rev-mission-chat-dock")).toBeVisible();
    await expect(page.locator("#rev-mission-chat-input")).toBeVisible();
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1)).toBe(true);
    expect(externalTiles).toBe(0);
    const input = page.locator("#rev-mission-chat-input");
    await input.fill("先保留这句未发送的修改");
    if (width < 1000) {
      await page.getByTestId("rev-mission-layer-map").click();
      await expect(page.getByTestId("rev-mission-timeline-pane")).toBeHidden();
      await expect(page.getByTestId("rev-mission-agent-pane")).toBeHidden();
      await page.getByTestId("rev-mission-layer-agent").click();
      await expect(page.getByTestId("rev-mission-agent-pane")).toBeVisible();
      await expect(page.getByTestId("rev-mission-map-pane")).toBeHidden();
      await expect(input).toHaveValue("先保留这句未发送的修改");
      await input.blur();
      const dimensions = await page.evaluate(() => ({
        hero: document.querySelector(".cn-mission-head")!.getBoundingClientRect().height,
        dock: document.querySelector(".rev-mission-chat-dock")!.getBoundingClientRect().height,
        font: parseFloat(getComputedStyle(document.querySelector("#rev-mission-chat-input")!).fontSize),
      }));
      expect(dimensions.hero).toBeLessThanOrEqual(220);
      expect(dimensions.dock).toBeLessThanOrEqual(90);
      expect(dimensions.font).toBeGreaterThanOrEqual(16);
    }
    const settings = page.getByRole("region", { name: "对话设置", exact: true });
    await expect(settings).toBeHidden();
    await page.getByRole("button", { name: "对话设置", exact: true }).click();
    await expect(settings).toBeVisible();
    await expect(settings.getByLabel("本次允许 AI 处理旅行目标（可能产生费用）")).toBeChecked();
    // Revoking moves that row back beside 发送 — it is the row that blocks the button — so this
    // follows the row to its new home instead of acting on the element that just moved.
    await settings.getByLabel("本次允许 AI 处理旅行目标（可能产生费用）").click();
    const strip = page.getByTestId("rev-mission-consent-strip");
    await expect(strip).toBeVisible();
    await expect(strip.getByLabel("本次允许 AI 处理旅行目标（可能产生费用）")).not.toBeChecked();
    await expect(strip.getByLabel("本次允许查询公开地图和地点来源")).toBeChecked();
    await settings.getByRole("button", { name: "关闭对话设置" }).click();
    await expect(settings).toBeHidden();
    await expect(input).toHaveValue("先保留这句未发送的修改");

    // A sentence and a schedule change are different facts. The screen says which one happened using
    // the two draft revisions the server stored with the reply, and it renders the model's markdown
    // as lines rather than as literal asterisks and dashes.
    await page.getByTestId("rev-mission-layer-agent").click();
    await expect(page.locator(".rev-agent-message-receipt")).toHaveText([
      "这条回复没有改动日程（版本 3）",
      "日程：版本 2 → 3",
    ]);
    const firstReply = page.locator(".rev-agent-message-body").first();
    await expect(firstReply.locator("p").first()).toHaveText("已把第二天下午改成湖边散步");
    await expect(firstReply).not.toContainText("**");
    await expect(firstReply).not.toContainText("- 上午");
  });
}
