import { expect, test, type Page, type Route } from "@playwright/test";

/**
 * UI consent / navigation flow with Playwright TEST_PROVIDER fixtures. Live OSM,
 * AgentRun, signed backend mutations, and device flow use separate acceptance runs.
 */
test.use({ viewport: { width: 390, height: 844 }, hasTouch: true });

const journey = "00000000-0000-4000-8000-000000000117";
const root = `**/api/v1/journeys/${journey}`;
const firstId = "sample-spot-1";
const secondId = "sample-spot-2";

function json(route: Route, object: object) {
  return route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(object) });
}

/**
 * On the mission screen the manual city search is folded behind an explicit choice, so a test that
 * wants the city box performs the same opening a traveller does. Where the pane is not folded this
 * does nothing.
 */
async function openManualSearch(page: Page) {
  const fold = page.getByTestId("rev-quick-area-secondary");
  if (await fold.isVisible().catch(() => false)) await fold.locator("> summary").click();
}

test("TEST_FIXTURE city and AI pending labels preserve consent and disclose the server-selected source", async ({ page }) => {
  let citySearchCalls = 0;
  let aiCalls = 0;
  let releaseCitySearch!: () => void;
  let markCitySearchStarted!: () => void;
  const citySearchGate = new Promise<void>((resolve) => {
    releaseCitySearch = resolve;
  });
  const citySearchStarted = new Promise<void>((resolve) => {
    markCitySearchStarted = resolve;
  });
  let releaseAi!: () => void;
  let markAiStarted!: () => void;
  const aiGate = new Promise<void>((resolve) => {
    releaseAi = resolve;
  });
  const aiStarted = new Promise<void>((resolve) => {
    markAiStarted = resolve;
  });

  await page.addInitScript((id) => {
    window.sessionStorage.setItem("citynexus.traveler.bearer", "signed-only-fixture-token");
    window.sessionStorage.setItem("citynexus.traveler.session-id", "TEST_FIXTURE_TRAVELER_CITY_AI");
    window.localStorage.setItem("citynexus.revolution.firstlook.journey", JSON.stringify({
      id, cityCode: "CN-RV-TEST", cityName: "连城", status: "DRAFT",
      ownerTravelerId: "TEST_FIXTURE_TRAVELER_CITY_AI",
    }));
  }, journey);
  await page.route("**/api/v1/**", (route) => route.abort());
  await page.route("**/api/v1/agent/runtime-status", (route) => json(route, {
    runtime_identity: "HERMES_COMPAT_ENDPOINT", hermes_compat_configured: true,
    ai_state: "CONFIGURED_UNVERIFIED",
  }));
  await page.route(`${root}/bootstrap-discovery/readiness`, (route) => json(route, {
    status: "READY", reason_code: "READY", provider: "overpass", provider_grade: "TEST_PROVIDER",
  }));
  await page.route(`${root}/bootstrap-shortlist`, (route) => json(route, {
    journey_id: journey, limit: 3, items: [], resume: null, pocket_walk: null,
  }));
  await page.route(`${root}/bootstrap-city-search`, async (route) => {
    citySearchCalls += 1;
    const payload = route.request().postDataJSON();
    expect(payload.provider_consent).toBe(true);
    expect(payload.provider).toBeUndefined();
    markCitySearchStarted();
    await citySearchGate;
    await json(route, {
      journey_id: journey, status: "CITY_RESULTS", query: "连城", provider_key: "photon", provider_attempts: [],
      results: [{
        result_id: "TEST_FIXTURE-city", name: "连城县", display_name: "连城县（测试地名结果）",
        provider: "photon", provider_provenance: "TEST_PROVIDER",
        latitude: 25.7, longitude: 116.75, coordinate_system: "WGS84",
        confidence: "CITY_CENTROID_UNCERTAIN", selection_state: "CAMERA_ONLY_TAP_REQUIRED",
      }],
    });
  });
  await page.route(`${root}/trial-ai-discovery`, async (route) => {
    aiCalls += 1;
    markAiStarted();
    await aiGate;
    await json(route, {
      status: "MODEL_TOOL_SUGGESTION", category: "park/garden",
      reason: "TEST_FIXTURE: 可以先试公园绿地这一类。",
      model: "TEST_FIXTURE", evidence: "HERMES_COMPAT_READ_ONLY_TOOL_RESPONSE",
      provider_calls: 0, agent_run_created: false,
    });
  });

  await page.goto("/revolution");
  await expect(page.getByTestId("rev-quick-explore")).toBeVisible();
  await expect(page.getByTestId("rev-quick-area")).not.toContainText(/服务器当前选择的公开地名服务|点击后使用演示地点数据/);
  await expect(page.getByTestId("rev-quick-area")).not.toContainText("TEST_PROVIDER");
  await expect(page.getByTestId("rev-quick-area")).not.toContainText("Nominatim");
  const cityButton = page.getByTestId("rev-quick-find-city");
  const aiButton = page.getByTestId("rev-quick-consult-ai");
  await openManualSearch(page);
  await page.getByLabel("城市或地区").fill("连城");
  await cityButton.click();
  await citySearchStarted;
  await expect(cityButton).toBeDisabled();
  await expect(cityButton).toHaveText("查询中…");
  await expect(aiButton).toBeDisabled();
  await expect(aiButton).toHaveText("问问 AI →");
  releaseCitySearch();
  await expect(page.getByTestId("rev-quick-city-results")).toBeVisible();
  await expect(page.getByTestId("rev-quick-area")).toContainText("刚才的地名来自 Photon。");
  await expect(cityButton).toBeEnabled();
  await expect(cityButton).toHaveText("查找位置 →");

  await page.getByLabel("写下你的想法").fill("想轻松走走");
  await expect(aiButton).toBeEnabled();
  await aiButton.click();
  await aiStarted;
  await expect(aiButton).toBeDisabled();
  await expect(aiButton).toHaveText("正在请教 AI…");
  await expect(cityButton).toBeDisabled();
  await expect(cityButton).toHaveText("查找位置 →");
  releaseAi();
  await expect(page.getByTestId("rev-quick-ai-response")).toBeVisible();
  expect(citySearchCalls).toBe(1);
  expect(aiCalls).toBe(1);
});

test("one AI suggestion is revealed in view without repeat requests or stealing editing focus", async ({ page }) => {
  let aiCalls = 0;
  let citySearchCalls = 0;
  let poiSearchCalls = 0;
  let releaseSuggestion!: () => void;
  let markSuggestionRequestStarted!: () => void;
  const suggestionRequestStarted = new Promise<void>((resolve) => {
    markSuggestionRequestStarted = resolve;
  });
  const suggestionResponseGate = new Promise<void>((resolve) => {
    releaseSuggestion = resolve;
  });

  await page.emulateMedia({ reducedMotion: "reduce" });
  await page.addInitScript((id) => {
    const browserWindow = window as Window & {
      __quickExploreScrollCalls?: Array<{ behavior?: ScrollBehavior }>;
    };
    browserWindow.__quickExploreScrollCalls = [];
    const originalScrollIntoView = Element.prototype.scrollIntoView;
    Element.prototype.scrollIntoView = function (options?: boolean | ScrollIntoViewOptions) {
      const normalized = typeof options === "boolean" ? {} : options ?? {};
      browserWindow.__quickExploreScrollCalls?.push(normalized);
      originalScrollIntoView.call(this, options);
    };
    window.sessionStorage.setItem("citynexus.traveler.bearer", "signed-only-fixture-token");
    window.localStorage.setItem("citynexus.revolution.firstlook.journey", JSON.stringify({
      id,
      cityCode: "CN-RV-TEST",
      cityName: "连城",
      status: "DRAFT",
    }));
  }, journey);
  await page.route("**/api/v1/agent/runtime-status", (route) => json(route, {
    runtime_identity: "HERMES_COMPAT_ENDPOINT",
    hermes_compat_configured: true,
    ai_state: "CONFIGURED_UNVERIFIED",
  }));
  await page.route(`${root}/bootstrap-discovery/readiness`, (route) => json(route, {
    status: "READY", reason_code: "READY", provider: "overpass", provider_grade: "TEST_PROVIDER",
  }));
  await page.route(`${root}/bootstrap-shortlist`, (route) => json(route, {
    journey_id: journey, limit: 3, items: [], resume: null, pocket_walk: null,
  }));
  await page.route(`${root}/trial-ai-discovery`, async (route) => {
    aiCalls += 1;
    markSuggestionRequestStarted();
    expect(route.request().postDataJSON().goal).toContain("连城");
    await suggestionResponseGate;
    return json(route, {
      status: "MODEL_TOOL_SUGGESTION",
      category: "park/garden",
      reason: "公园或园林适合慢慢散步，具体地点请再用公开地图搜索。",
      model: "TEST_PROVIDER",
      evidence: "HERMES_COMPAT_READ_ONLY_TOOL_RESPONSE",
      provider_calls: 0,
      agent_run_created: false,
    });
  });
  await page.route(`${root}/bootstrap-city-search`, (route) => {
    citySearchCalls += 1;
    return route.abort();
  });
  await page.route(`${root}/bootstrap-discovery`, (route) => {
    poiSearchCalls += 1;
    return route.abort();
  });

  await page.goto("/revolution");
  const prompt = page.getByLabel("写下你的想法");
  const askAi = page.getByTestId("rev-quick-consult-ai");
  const suggestion = page.getByTestId("rev-quick-ai-response");
  await expect(prompt).toBeEnabled();
  await expect(askAi).toBeEnabled();
  await expect(suggestion).toHaveCount(0);

  await askAi.focus();
  await askAi.press("Enter");
  await suggestionRequestStarted;
  await expect(askAi).toBeDisabled();
  expect(aiCalls).toBe(1);

  // The request uses its submitted text; editing remains available while it waits.
  await prompt.fill("我在连城，下午想再轻松走走。");
  await expect(prompt).toBeFocused();
  releaseSuggestion();

  await expect(suggestion).toBeVisible();
  await expect(suggestion).toContainText("AI 给你的探索建议");
  await expect(suggestion).toContainText("建议兴趣：公园和绿地");
  await expect(suggestion).toBeInViewport();
  await expect(prompt).toBeFocused();
  await expect(prompt).toHaveValue("我在连城，下午想再轻松走走。");
  await expect(prompt).toBeEnabled();
  await prompt.fill("我还想改一下兴趣描述。");
  expect(aiCalls).toBe(1);

  const scrollCalls = await page.evaluate(() => (window as Window & {
    __quickExploreScrollCalls?: Array<{ behavior?: ScrollBehavior }>;
  }).__quickExploreScrollCalls ?? []);
  expect(scrollCalls).toHaveLength(1);
  expect(scrollCalls[0]?.behavior).toBe("instant");
  expect(aiCalls).toBe(1);
  expect(citySearchCalls).toBe(0);
  expect(poiSearchCalls).toBe(0);
});

test("plain Chinese first-user journey preserves separate intentional provider releases", async ({ page }) => {
  let citySearchCalls = 0;
  let poiSearchCalls = 0;
  let hermesGuideCalls = 0;
  let tileRequests = 0;
  let saved = false;
  let progressRevision = 0;
  let goState = "NOT_STARTED";

  const pocket = () => ({
    status: "POCKET_WALK_SAVED",
    pocket_walk_id: "pocket-quick-1",
    revision: 1,
    journey_id: journey,
    first_stop: { name: "SAMPLE ONLY - Trailhead", shortlist_id: "s1" },
    second_stop: { name: "SAMPLE ONLY - Park", shortlist_id: "s2" },
    plan_version_id: null,
    go_progress: {
      state: goState,
      progress_revision: progressRevision,
      pocket_walk_revision: 1,
      progress_class: "USER_REPORTED_PROGRESS",
      physical_arrival_state: "NOT_PHYSICAL_ARRIVAL_PROVEN",
    },
  });

  await page.addInitScript((id) => {
    window.sessionStorage.setItem("citynexus.traveler.bearer", "signed-only-fixture-token");
    window.localStorage.setItem("citynexus.revolution.firstlook.journey", JSON.stringify({
      id, cityCode: "CN-RV-TEST", cityName: "连城", status: "DRAFT",
    }));
  }, journey);
  await page.route("**/api/v1/**", (route) => route.abort());
  await page.route("**/api/v1/agent/runtime-status", (route) => json(route, {
    runtime_identity: "HERMES_COMPAT_ENDPOINT", hermes_compat_configured: true,
    ai_state: "CONFIGURED_UNVERIFIED",
  }));
  await page.route(`${root}/trial-ai-discovery`, (route) => {
    hermesGuideCalls += 1;
    const payload = route.request().postDataJSON();
    expect(payload.goal).toContain("连城");
    return json(route, {
      status: "MODEL_TOOL_SUGGESTION", category: "park/garden",
      reason: "想轻松走走，可以先试公园绿地这一类。真实地点仍需公开搜索。",
      model: "TEST_PROVIDER", evidence: "HERMES_COMPAT_READ_ONLY_TOOL_RESPONSE",
      provider_calls: 0, agent_run_created: false,
    });
  });
  await page.route("https://tile.openstreetmap.org/**", (route) => {
    tileRequests += 1;
    return route.abort();
  });
  await page.route(`${root}/bootstrap-discovery/readiness`, (route) => json(route, {
    status: "READY", reason_code: "READY", provider: "overpass",
    provider_name: "Playwright fixture", expected_recipient: "TEST_PROVIDER",
    capability_state: "TEST_CAPABLE", provider_grade: "TEST_PROVIDER",
    external_request_allowed: true, test_only: true,
  }));
  await page.route(`${root}/bootstrap-shortlist`, (route) => json(route, {
    journey_id: journey, limit: 3, items: [], resume: null,
    pocket_walk: saved ? pocket() : null,
  }));
  await page.route(`${root}/bootstrap-city-search`, async (route) => {
    citySearchCalls += 1;
    const payload = route.request().postDataJSON();
    expect(payload.provider_consent).toBe(true);
    expect(payload.query).toBe("连城");
    await json(route, {
      journey_id: journey, status: "CITY_RESULTS", query: "连城", provider_attempts: [],
      results: [{
        result_id: "city-fixture-1", name: "连城县", display_name: "连城县（测试地名结果）",
        provider: "test", provider_provenance: "TEST_PROVIDER",
        latitude: 25.7, longitude: 116.75, coordinate_system: "WGS84",
        confidence: "CITY_CENTROID_UNCERTAIN", selection_state: "CAMERA_ONLY_TAP_REQUIRED",
      }],
    });
  });
  await page.route(`${root}/bootstrap-discovery`, async (route) => {
    poiSearchCalls += 1;
    const payload = route.request().postDataJSON();
    expect(payload.provider_consent).toBe(true);
    expect(payload.source_kind).toBe("MANUAL_PUBLIC_CENTER");
    expect(payload.latitude).toBe(25.7);
    expect(payload.longitude).toBe(116.75);
    await json(route, {
      journey_id: journey, status: "LIVE_RESULTS", source_kind: "MANUAL_PUBLIC_CENTER",
      provider: "overpass", provider_provenance: "TEST_PROVIDER", receipt_id: "receipt-quick",
      attempts: [{ http_status: 200 }],
      candidates: [
        { candidate_id: firstId, name: "SAMPLE ONLY - Trailhead",
          category: "park", source_url: "https://www.openstreetmap.org/node/123",
          provider_provenance: "TEST_PROVIDER" },
        { candidate_id: secondId, name: "SAMPLE ONLY - Park",
          category: "park", source_url: "https://www.openstreetmap.org/node/124",
          provider_provenance: "TEST_PROVIDER" },
      ],
    });
  });
  await page.route(`${root}/bootstrap-discovery/pocket-walk`, async (route) => {
    const payload = route.request().postDataJSON();
    expect(payload.receipt_id).toBe("receipt-quick");
    expect(payload.first_candidate_id).toBe(firstId);
    expect(payload.second_candidate_id).toBe(secondId);
    saved = true;
    await json(route, { pocket_walk: pocket(), items: [] });
  });
  await page.route(`${root}/bootstrap-shortlist/pocket-walk/go`, async (route) => {
    const payload = route.request().postDataJSON();
    expect(payload.action).toBe("START");
    expect(payload.expected_revision).toBe(0);
    goState = "HEADING_TO_FIRST";
    progressRevision = 1;
    await json(route, { journey_id: journey, pocket_walk: pocket(), go_progress: pocket().go_progress });
  });

  await page.goto("/revolution");
  await expect(page.getByTestId("rev-quick-explore")).toBeVisible();
  expect(citySearchCalls).toBe(0);
  expect(poiSearchCalls).toBe(0);
  expect(hermesGuideCalls).toBe(0);
  expect(tileRequests).toBe(0);

  // A real model-guidance request is only made when the signed user explicitly
  // submits their own goal. All provider replies in this test are fixtures.
  await page.getByTestId("rev-quick-consult-ai").click();
  await expect(page.getByTestId("rev-quick-ai-response")).toBeVisible();
  expect(hermesGuideCalls).toBe(1);
  expect(citySearchCalls).toBe(0);
  expect(poiSearchCalls).toBe(0);

  await openManualSearch(page);
  await page.getByTestId("rev-quick-find-city").click();
  await expect(page.getByTestId("rev-quick-city-results")).toBeVisible();
  expect(citySearchCalls).toBe(1);
  expect(poiSearchCalls).toBe(0);

  // The chosen TEST_PROVIDER geocoder result is only an approximate public
  // area. The user explicitly adopts it, then separately chooses to search
  // nearby; no blank MapLibre tiles or physical-position proof are required.
  await page.getByRole("button", { name: /连城县.*2.5公里/ }).click();
  await page.getByRole("button", { name: "直接从这片地区附近找 →" }).click();
  await expect(page.getByTestId("rev-quick-category")).toBeVisible();
  expect(poiSearchCalls).toBe(0);
  expect(tileRequests).toBe(0);

  await page.getByTestId("rev-quick-find-places").click();
  await expect(page.getByTestId("rev-quick-results")).toBeVisible();
  await expect(page.getByText("尚未选地点。点选一处加入第 1 站，再点另一处加入第 2 站。", { exact: true })).toBeVisible();
  expect(poiSearchCalls).toBe(1);
  await page.getByTestId(`rev-quick-select-${firstId}`).click();
  await expect(page.getByText("第 1 站已选；点另一处加入第 2 站。", { exact: true })).toBeVisible();
  await page.getByTestId(`rev-quick-select-${secondId}`).click();
  await expect(page.getByText("第 1 站和第 2 站已选；点选卡片可调整选择。", { exact: true })).toBeVisible();
  await page.getByTestId("rev-quick-save").click();
  await expect(page.getByTestId("rev-quick-walk")).toBeVisible();
  await page.getByRole("button", { name: "开始散步" }).click();
  await expect(page.getByText("正前往第一站", { exact: false })).toBeVisible();

  await page.reload();
  await expect(page.getByTestId("rev-quick-walk")).toBeVisible();
  await expect(page.getByText("正前往第一站", { exact: false })).toBeVisible();
});

for (const outcome of [
  {
    status: "CITY_NO_RESULTS",
    message: "没有匹配地区。换个名称或粘贴公开地图链接。",
    forbidden: "地名服务暂时连不上",
  },
  {
    status: "GEOCODER_UNAVAILABLE",
    message: "地名服务暂时连不上。换个地区，或粘贴公开地图链接。",
    forbidden: "没有匹配地区",
  },
  {
    status: "GEOCODER_DISABLED",
    message: "当前环境未开启公开地名搜索。可粘贴公开地图链接。",
    forbidden: "没有匹配地区",
  },
  {
    status: "GEOCODER_RATE_LIMITED",
    message: "地图服务正在限流，稍后重试或粘贴公开地图链接。",
    forbidden: "没有匹配地区",
  },
] as const) {
  test(`city search explains ${outcome.status} accurately`, async ({ page }) => {
    let searchCalls = 0;
    await page.addInitScript((id) => {
      window.sessionStorage.setItem("citynexus.traveler.bearer", "signed-only-fixture-token");
      window.localStorage.setItem("citynexus.revolution.firstlook.journey", JSON.stringify({
        id, cityCode: "CN-RV-TEST", cityName: "连城", status: "DRAFT",
      }));
    }, journey);
    await page.route("**/api/v1/agent/runtime-status", (route) => json(route, {
      runtime_identity: "UNCONFIGURED", hermes_compat_configured: false,
    }));
    await page.route(`${root}/bootstrap-discovery/readiness`, (route) => json(route, {
      status: "READY", reason_code: "READY", provider: "nominatim", provider_grade: "TEST_PROVIDER",
    }));
    await page.route(`${root}/bootstrap-shortlist`, (route) => json(route, {
      journey_id: journey, limit: 3, items: [], resume: null, pocket_walk: null,
    }));
    await page.route(`${root}/bootstrap-city-search`, async (route) => {
      searchCalls += 1;
      await json(route, {
        journey_id: journey,
        status: outcome.status,
        query: "连城",
        provider_attempts: outcome.status === "CITY_NO_RESULTS"
          ? [{ provider: "nominatim", answered: true, http_status: 200 }]
          : outcome.status === "GEOCODER_RATE_LIMITED"
            ? [{ provider: "nominatim", answered: true, http_status: 429 }]
            : outcome.status === "GEOCODER_DISABLED"
              ? []
              : [{ provider: "nominatim", answered: false, error: "ConnectTimeout" }],
        results: [],
      });
    });

    await page.goto("/revolution");
    await openManualSearch(page);
    await page.getByTestId("rev-quick-find-city").click();
    await expect(page.getByRole("status")).toContainText(outcome.message);
    await expect(page.getByRole("status")).not.toContainText(outcome.forbidden);
    await expect(page.locator("#rev-quick-search")).toHaveValue("连城");
    expect(searchCalls).toBe(1);
  });
}

test("TEST_FIXTURE AI gateway 502 preserves the draft and recovers manually without another AI call", async ({ page }) => {
  let aiCalls = 0;
  let citySearchCalls = 0;
  let poiSearchCalls = 0;
  await page.addInitScript((id) => {
    window.sessionStorage.setItem("citynexus.traveler.bearer", "signed-only-fixture-token");
    window.localStorage.setItem("citynexus.revolution.firstlook.journey", JSON.stringify({
      id, cityCode: "CN-RV-TEST", cityName: "连城", status: "DRAFT",
    }));
  }, journey);
  await page.route("**/api/v1/agent/runtime-status", (route) => json(route, {
    runtime_identity: "HERMES_COMPAT_ENDPOINT", hermes_compat_configured: true,
    ai_state: "CONFIGURED_UNVERIFIED",
  }));
  await page.route(`${root}/bootstrap-discovery/readiness`, (route) => json(route, {
    status: "READY", reason_code: "READY", provider: "overpass", provider_grade: "TEST_PROVIDER",
  }));
  await page.route(`${root}/bootstrap-shortlist`, (route) => json(route, {
    journey_id: journey, limit: 3, items: [], resume: null, pocket_walk: null,
  }));
  await page.route(`${root}/trial-ai-discovery`, async (route) => {
    aiCalls += 1;
    expect(route.request().postDataJSON().goal).toBe("我在连城，想找个安静的地方散步。");
    return route.fulfill({
      status: 502,
      contentType: "application/json",
      body: JSON.stringify({ error: { code: "BAD_GATEWAY", reason_code: "UPSTREAM_UNAVAILABLE" } }),
    });
  });
  await page.route(`${root}/bootstrap-city-search`, (route) => {
    citySearchCalls += 1;
    return route.abort();
  });
  await page.route(`${root}/bootstrap-discovery`, (route) => {
    poiSearchCalls += 1;
    return route.abort();
  });

  await page.goto("/revolution");
  const prompt = page.getByLabel("写下你的想法");
  const goal = "我在连城，想找个安静的地方散步。";
  await prompt.fill(goal);
  await page.getByTestId("rev-quick-consult-ai").click();

  const alert = page.getByRole("alert");
  await expect(alert).toContainText(/^AI 服务暂不可用。/);
  await expect(prompt).toHaveValue(goal);
  await expect(page.getByTestId("rev-quick-error-recovery")).toHaveCount(1);
  expect(aiCalls).toBe(1);

  await page.getByTestId("rev-quick-error-recovery").click();
  await expect(page.getByRole("status")).toContainText("可以直接查找公开地名");
  await expect(page.locator("#rev-quick-search")).toBeFocused();
  await expect(prompt).toHaveValue(goal);
  expect(aiCalls).toBe(1);
  expect(citySearchCalls).toBe(0);
  expect(poiSearchCalls).toBe(0);
});

test("AI route 404 can be skipped without restarting the user's journey", async ({ page }) => {
  let aiCalls = 0;
  await page.addInitScript((id) => {
    window.sessionStorage.setItem("citynexus.traveler.bearer", "signed-only-fixture-token");
    window.localStorage.setItem("citynexus.revolution.firstlook.journey", JSON.stringify({
      id, cityCode: "CN-RV-TEST", cityName: "连城", status: "DRAFT",
    }));
  }, journey);
  await page.route("**/api/v1/agent/runtime-status", (route) => json(route, {
    runtime_identity: "HERMES_COMPAT_ENDPOINT", hermes_compat_configured: true,
    ai_state: "CONFIGURED_UNVERIFIED",
  }));
  await page.route(`${root}/bootstrap-discovery/readiness`, (route) => json(route, {
    status: "READY", reason_code: "READY", provider: "overpass", provider_grade: "TEST_PROVIDER",
  }));
  await page.route(`${root}/bootstrap-shortlist`, (route) => json(route, {
    journey_id: journey, limit: 3, items: [], resume: null, pocket_walk: null,
  }));
  await page.route(`${root}/trial-ai-discovery`, async (route) => {
    aiCalls += 1;
    await route.fulfill({
      status: 404,
      contentType: "application/json",
      body: JSON.stringify({ error: { code: "NOT_FOUND", reason_code: "TRIAL_AI_ROUTE_NOT_LOADED" } }),
    });
  });

  await page.goto("/revolution");
  await page.getByTestId("rev-quick-consult-ai").click();
  await expect(page.getByRole("alert")).toContainText("AI 引导暂不可用");
  await expect(page.getByTestId("rev-quick-error-recovery")).toHaveText("继续手动探索");
  expect(aiCalls).toBe(1);

  await page.getByTestId("rev-quick-error-recovery").click();
  await expect(page.getByRole("status")).toContainText("可以直接查找公开地名");
  await expect(page.getByTestId("rev-quick-find-city")).toBeEnabled();
  expect(aiCalls).toBe(1);
});

test("AI authentication expiry explains itself and still allows manual exploration", async ({ page }) => {
  let aiCalls = 0;
  let readinessCalls = 0;
  await page.addInitScript((id) => {
    window.sessionStorage.setItem("citynexus.traveler.bearer", "signed-only-fixture-token");
    window.localStorage.setItem("citynexus.revolution.firstlook.journey", JSON.stringify({
      id, cityCode: "CN-RV-TEST", cityName: "连城", status: "DRAFT",
    }));
  }, journey);
  await page.route("**/api/v1/agent/runtime-status", (route) => json(route, {
    runtime_identity: "HERMES_COMPAT_ENDPOINT", hermes_compat_configured: true,
    ai_state: "CONFIGURED_UNVERIFIED",
  }));
  await page.route(`${root}/bootstrap-discovery/readiness`, (route) => {
    readinessCalls += 1;
    return json(route, {
      status: "READY", reason_code: "READY", provider: "overpass", provider_grade: "TEST_PROVIDER",
    });
  });
  await page.route(`${root}/bootstrap-shortlist`, (route) => json(route, {
    journey_id: journey, limit: 3, items: [], resume: null, pocket_walk: null,
  }));
  await page.route(`${root}/trial-ai-discovery`, async (route) => {
    aiCalls += 1;
    await route.fulfill({
      status: 401,
      contentType: "application/json",
      body: JSON.stringify({ error: { code: "UNAUTHENTICATED", reason_code: "TRAVELER_SESSION_EXPIRED" } }),
    });
  });

  await page.goto("/revolution");
  await page.getByTestId("rev-quick-consult-ai").click();
  await expect(page.getByRole("alert")).toContainText("登录会话已过期");
  await expect(page.getByTestId("rev-quick-error-recovery")).toHaveText("继续手动探索");
  expect(aiCalls).toBe(1);
  const readinessCallsBeforeSkip = readinessCalls;

  await page.getByTestId("rev-quick-error-recovery").click();
  await expect(page.getByRole("status")).toContainText("可以直接查找公开地名");
  await expect(page.getByTestId("rev-quick-find-city")).toBeEnabled();
  expect(readinessCalls).toBe(readinessCallsBeforeSkip);
  expect(aiCalls).toBe(1);
});

test("Overpass outage is distinguished from zero places and retries only on a clear click", async ({ page }) => {
  let citySearchCalls = 0;
  let poiSearchCalls = 0;
  await page.addInitScript((id) => {
    window.sessionStorage.setItem("citynexus.traveler.bearer", "signed-only-fixture-token");
    window.localStorage.setItem("citynexus.revolution.firstlook.journey", JSON.stringify({
      id, cityCode: "CN-RV-TEST", cityName: "连城", status: "DRAFT",
    }));
  }, journey);
  await page.route("**/api/v1/agent/runtime-status", (route) => json(route, {
    runtime_identity: "UNCONFIGURED", hermes_compat_configured: false,
  }));
  await page.route(`${root}/bootstrap-discovery/readiness`, (route) => json(route, {
    status: "READY", reason_code: "READY", provider: "overpass", provider_grade: "LIVE_CAPABLE",
    external_request_allowed: true, test_only: false,
  }));
  await page.route(`${root}/bootstrap-shortlist`, (route) => json(route, {
    journey_id: journey, limit: 3, items: [], resume: null, pocket_walk: null,
  }));
  await page.route(`${root}/bootstrap-city-search`, async (route) => {
    citySearchCalls += 1;
    await json(route, {
      journey_id: journey, status: "CITY_RESULTS", query: "连城", provider_attempts: [],
      results: [{
        result_id: "city-live-fixture", name: "连城县", display_name: "连城县，龙岩市，福建省，中国",
        provider: "test", provider_provenance: "TEST_PROVIDER",
        latitude: 25.7, longitude: 116.75, coordinate_system: "WGS84",
        confidence: "CITY_CENTROID_UNCERTAIN", selection_state: "CAMERA_ONLY_TAP_REQUIRED",
      }],
    });
  });
  await page.route(`${root}/bootstrap-discovery`, async (route) => {
    poiSearchCalls += 1;
    await json(route, {
      journey_id: journey, status: "PROVIDER_UNAVAILABLE", result_state: "UNAVAILABLE",
      failure_code: "PROVIDER_UNAVAILABLE", provider: "overpass", provider_provenance: "UNVERIFIED",
      source_kind: "MANUAL_PUBLIC_CENTER", receipt_id: null, expires_at: null,
      attempts: [{ answered: false, http_status: 504 }], candidates: [],
    });
  });

  await page.goto("/revolution");
  await openManualSearch(page);
  await page.getByTestId("rev-quick-find-city").click();
  await expect(page.getByTestId("rev-quick-city-results")).toBeVisible();
  expect(citySearchCalls).toBe(1);
  await page.getByTestId("rev-quick-city-results").locator("button").first().click();
  await page.getByTestId("rev-quick-find-places").click();
  await expect(page.getByTestId("rev-quick-results")).toBeVisible();
  await expect(page.getByRole("alert")).toContainText("公开地点服务刚才没有响应");
  await expect(page.getByTestId("rev-quick-results")).toContainText("公开地点服务没有回答，附近情况尚未确认");
  await expect(page.getByTestId("rev-quick-results")).not.toContainText("暂时没有找到符合条件的地点");
  await expect(page.getByTestId("rev-quick-error-recovery")).toHaveText("重新搜索附近地点");
  expect(poiSearchCalls).toBe(1);

  await page.getByTestId("rev-quick-error-recovery").click();
  await expect(page.getByRole("alert")).toContainText("公开地点服务刚才没有响应");
  expect(poiSearchCalls).toBe(2);
});
