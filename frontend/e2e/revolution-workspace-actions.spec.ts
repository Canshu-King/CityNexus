import { expect, test, type Page } from "@playwright/test";

const journeyId = "00000000-0000-4000-8000-000000000921";
const owner = "REFORM_FIXTURE_OWNER";
const token = "REFORM_TEST_FIXTURE_TOKEN";
const goal = "两人旅行，少走路，下午出发。";

async function fixture(page: Page, failRuntime = false) {
  const modelCalls: string[] = [];
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
    if (path === `${root}/planning-intent`) return reply({
      journey_id: journeyId, intent: { id: "test-intent", goal, interests: [], energy: "easy", updated_at: "2026-10-18T00:00:00Z", mapped_preferences: [] },
      trip: { dates: ["2026-10-19", "2026-10-20"], party_size: 2, budget: { amount_minor: 100000, currency: "CNY" } },
      candidates: [{ candidate_id: "test-place-one", name: "TEST_FIXTURE 未核实公园", latitude: 25.037, longitude: 121.563,
        coordinate_system: "WGS84", selection_state: "OPENING_UNVERIFIED", provider_provenance: "TEST_PROVIDER",
        price_state: "UNKNOWN", opening_hours: {}, selection_blockers: ["OPENING_UNVERIFIED", "COST_UNKNOWN"] }],
    });
    if (path === `${root}/bootstrap-shortlist`) return reply({ journey_id: journeyId, pocket_walk: null });
    if (path === `${root}/bootstrap-discovery/current`) return reply({ journey_id: journeyId, receipt_id: null, candidates: [] });
    if (path === `${root}/trial-ai-discovery`) {
      expect(request.method()).toBe("POST");
      modelCalls.push(request.postDataJSON().goal);
      return reply({ status: "MODEL_TOOL_SUGGESTION", evidence: "HERMES_COMPAT_READ_ONLY_TOOL_RESPONSE", reason: "TEST_FIXTURE 可以先去室内文化地点。" });
    }
    return reply({});
  });
  return modelCalls;
}

for (const width of [390, 430, 1366]) {
  test(`TEST_FIXTURE assistant is one click from Trips at ${width}, no automatic model call`, async ({ page }) => {
    await page.setViewportSize({ width, height: 900 });
    const calls = await fixture(page);
    await page.goto("/revolution");
    await page.getByTestId("rev-mobile-tab-trips").click();
    await page.getByTestId("rev-mobile-tab-assistant").click();
    const dialog = page.getByRole("dialog");
    await expect(dialog).toBeVisible();
    await expect(dialog.getByRole("textbox")).toHaveValue(goal);
    expect(calls).toEqual([]);
    await dialog.getByRole("button", { name: "发送给 AI", exact: true }).click();
    await expect(dialog.getByRole("region", { name: "AI 返回的建议" })).toContainText("TEST_FIXTURE");
    expect(calls).toEqual([goal]);
    await dialog.getByRole("button", { name: "关闭工作台" }).click();
    await expect(dialog).not.toBeVisible();
  });
}

test("TEST_FIXTURE unknown hours and unavailable AI do not hide the map's saved places", async ({ page }) => {
  const calls = await fixture(page, true);
  let tiles = 0;
  await page.route("https://tile.openstreetmap.org/**", (route) => { tiles += 1; return route.abort(); });
  await page.goto("/revolution");
  await page.getByTestId("rev-mobile-tab-trips").click();
  await page.getByTestId("rev-mobile-tab-map").click();
  const dialog = page.getByRole("dialog");
  await expect(dialog).toContainText("TEST_FIXTURE 未核实公园");
  await expect(dialog.getByRole("button", { name: "加载地图", exact: true })).toBeEnabled();
  expect(calls).toEqual([]);
  expect(tiles).toBe(0);
});

test("TEST_FIXTURE identity change clears the open private assistant immediately", async ({ page }) => {
  await fixture(page);
  await page.goto("/revolution");
  await page.getByTestId("rev-mobile-tab-assistant").click();
  const dialog = page.getByRole("dialog");
  await expect(dialog.getByRole("textbox")).toHaveValue(goal);
  await page.evaluate(() => {
    sessionStorage.removeItem("citynexus.traveler.bearer");
    sessionStorage.removeItem("citynexus.traveler.session-id");
    window.dispatchEvent(new Event("storage"));
  });
  await expect(dialog.getByRole("textbox")).toHaveCount(0);
  await expect(dialog).not.toContainText(goal);
});
