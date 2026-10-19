import { expect, test } from "@playwright/test";

const jid = "00000000-0000-4000-8000-000000000991";
const tid = "00000000-0000-4000-8000-000000000992";
const owner = "VISUAL_TEST_FIXTURE_OWNER";

for (const width of [390, 1366]) {
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
      candidate_id: "photon:W/12345", name: "冠豸山风景区", latitude: 25.7158,
      longitude: 116.7757, coordinate_system: "WGS84", provider_provenance: "LIVE_PROVIDER",
      provider: "photon", selection_state: "OPENING_UNVERIFIED", source_url: "https://www.openstreetmap.org/way/12345",
      region_status: "MATCHED", observation_expired: false,
    };
    const task = {
      task_id: tid, journey_id: jid, status: "PARTIAL_READY",
      goal: "连城两天，少走路", mode: "GOAL_PLANNING",
      consent: { model: true, online_research: true },
      budget: { max_model_turns: 24, max_tool_calls: 48 },
      usage: { model_turns: 3, tool_calls: 2 },
      tool_steps: [], research_places: [], conversation: [],
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
      if (path === base + "/map-places") return reply({ journey_id: jid, candidates: [point] });
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
    await page.getByTestId("rev-mobile-tab-assistant").click();
    const cockpit = page.getByTestId("rev-mission-cockpit");
    await expect(cockpit).toBeVisible();
    await expect(page.locator(".cn-mission-media")).toBeVisible();
    await expect(cockpit.getByRole("region", { name: "与研究地点对应的真实景点照片" })).toContainText("冠豸山");
    await expect(cockpit.locator(".cn-place-photo-meta a").first()).toHaveAttribute("href", /commons\.wikimedia\.org/);
    await expect(cockpit.getByTestId("rev-workspace-coordinate-preview")).toBeVisible();
    await expect(cockpit.locator(".rev-workspace-preview-pin")).toHaveCount(1);
    expect(externalTiles).toBe(0);

    const options = cockpit.getByRole("region", { name: "旅行方案对比" });
    await expect(options.locator(".rev-goal-variant-card")).toHaveCount(3);
    const layout = await options.evaluate((element) => {
      const list = element.querySelector(".rev-goal-variants-list")!.getBoundingClientRect();
      const card = element.querySelector(".rev-goal-variant-card")!.getBoundingClientRect();
      return { list: list.width, card: card.width };
    });
    expect(layout.card).toBeGreaterThan(layout.list * 0.82);
    await expect(cockpit.locator(".cn-mission-agent-disclosure")).not.toHaveAttribute("open", "");
    await expect(page.locator(".rev-mission-chat-dock")).toBeVisible();
    await expect(page.locator("#rev-mission-chat-input")).toBeVisible();
  });
}
