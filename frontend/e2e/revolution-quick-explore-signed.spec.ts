import { mkdirSync } from "node:fs";
import { createServer, type Server } from "node:http";
import { join } from "node:path";
import { expect, test, type Browser, type Page } from "@playwright/test";

/**
 * Contract-backed browser flow. Only the external geocoder/Overpass boundaries
 * are local TEST_PROVIDER servers; traveler, Journey, discovery, save, GO, and
 * reload all cross the real signed CityNexus API. No API route is intercepted.
 */
test.use({ serviceWorkers: "block" });

const baseURL = `http://127.0.0.1:${Number(process.env.CITYNEXUS_E2E_PORT ?? 4173)}`;
const apiURL = `http://127.0.0.1:${Number(process.env.CITYNEXUS_BACKEND_PORT ?? 8000)}`;
const cityPort = Number(process.env.CITYNEXUS_E2E_CITY_PORT ?? 18482);
const overpassPort = Number(process.env.CITYNEXUS_E2E_OVERPASS_PORT ?? 18483);
const artifactDir = join(process.cwd(), "output", "playwright");

type ProviderFixtures = {
  cityServer: Server;
  overpassServer: Server;
  cityQueries: string[];
  overpassQueries: string[];
};

function json(response: import("node:http").ServerResponse, value: unknown) {
  response.writeHead(200, { "content-type": "application/json; charset=utf-8" });
  response.end(JSON.stringify(value));
}

function listen(server: Server, port: number): Promise<void> {
  return new Promise((resolve, reject) => {
    server.once("error", reject);
    server.listen(port, "127.0.0.1", resolve);
  });
}

function close(server: Server): Promise<void> {
  return new Promise((resolve, reject) => {
    server.close((error) => error ? reject(error) : resolve());
  });
}

function createProviderFixtures(): ProviderFixtures {
  const cityQueries: string[] = [];
  const overpassQueries: string[] = [];
  const cityServer = createServer((incoming, response) => {
    const requestUrl = new URL(incoming.url ?? "/", `http://127.0.0.1:${cityPort}`);
    cityQueries.push(requestUrl.searchParams.get("q") ?? "");
    json(response, [{
      place_id: 198415,
      osm_type: "relation",
      osm_id: 198415,
      lat: "25.7084",
      lon: "116.7566",
      display_name: "连城县，龙岩市，福建省，中国",
      class: "boundary",
      type: "administrative",
      address: { county: "连城县", city: "龙岩市", state: "福建省", country: "中国" },
    }]);
  });
  const overpassServer = createServer((incoming, response) => {
    const chunks: Buffer[] = [];
    incoming.on("data", (chunk: Buffer) => chunks.push(chunk));
    incoming.on("end", () => {
      const encoded = Buffer.concat(chunks).toString("utf8");
      overpassQueries.push(new URLSearchParams(encoded).get("data") ?? encoded);
      json(response, {
        version: 0.6,
        generator: "CityNexus first-human local TEST_PROVIDER fixture",
        elements: [
          {
            type: "node", id: 198421, lat: 25.7088, lon: 116.7569,
            tags: { name: "连城测试公园甲", leisure: "park", access: "yes" },
          },
          {
            type: "node", id: 198422, lat: 25.7092, lon: 116.7573,
            tags: { name: "连城测试公园乙", leisure: "park", access: "yes" },
          },
        ],
      });
    });
  });
  return { cityServer, overpassServer, cityQueries, overpassQueries };
}

async function startProviderFixtures(): Promise<ProviderFixtures> {
  const fixtures = createProviderFixtures();
  await Promise.all([
    listen(fixtures.cityServer, cityPort),
    listen(fixtures.overpassServer, overpassPort),
  ]);
  return fixtures;
}

function traceResponse(page: Page, trace: string[]) {
  page.on("response", (response) => {
    const url = new URL(response.url());
    if (!url.pathname.startsWith("/api/v1/")) return;
    const safePath = url.pathname.replace(
      /\/[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}(?=\/|$)/gi,
      "/:id",
    );
    trace.push(`${response.request().method()} ${safePath} ${response.status()}`);
  });
}

async function walkThrough(
  browser: Browser,
  fixtures: ProviderFixtures,
  viewport: { width: number; height: number },
  screenshot: string,
) {
  const context = await browser.newContext({
    viewport,
    deviceScaleFactor: 1,
    hasTouch: viewport.width < 500,
    serviceWorkers: "block",
  });
  const page = await context.newPage();
  const trace: string[] = [];
  let tileRequests = 0;
  traceResponse(page, trace);
  // Tiles are deliberately unavailable: they are optional and cannot block the
  // directly selected approximate public geocoder center.
  await context.route("https://tile.openstreetmap.org/**", async (route) => {
    tileRequests += 1;
    await route.abort();
  });

  await page.goto(`${baseURL}/revolution`, { waitUntil: "domcontentloaded" });
  await expect(page.getByTestId("rev-firstlook-city")).toHaveValue("连城");
  await page.getByTestId("rev-firstlook-start").click();
  await expect(page.getByTestId("rev-quick-explore")).toBeVisible();
  await page.locator("#rev-quick-ai-prompt").fill("我在连城，今晚两小时，想轻松走走。");
  await expect(page.getByTestId("rev-quick-consult-ai")).toBeDisabled();
  await expect(page.getByTestId("rev-quick-area")).toContainText("模型尚未接通，不影响手动探索");

  const cityCallsBefore = fixtures.cityQueries.length;
  const overpassCallsBefore = fixtures.overpassQueries.length;
  expect(cityCallsBefore).toBeLessThan(2);
  expect(overpassCallsBefore).toBeGreaterThanOrEqual(0);
  expect(tileRequests).toBe(0);

  // No geocoder request occurs while typing or before the explicit action.
  await expect(page.getByLabel("城市或地区")).toHaveValue("连城");
  await page.getByTestId("rev-quick-find-city").click();
  await expect(page.getByTestId("rev-quick-city-results")).toContainText("连城县，龙岩市，福建省，中国");
  // The API request is explicit in each viewport. A second identical query may
  // be served from the real backend's durable city-search cache, so it need not
  // hit the local provider fixture again.
  const providerCallsAdded = fixtures.cityQueries.length - cityCallsBefore;
  expect(providerCallsAdded).toBeGreaterThanOrEqual(0);
  expect(providerCallsAdded).toBeLessThanOrEqual(1);
  if (cityCallsBefore === 0) expect(providerCallsAdded).toBe(1);
  expect(fixtures.overpassQueries.length).toBe(overpassCallsBefore);

  // One card tap enters the next screen even though every map tile is blocked.
  await page.getByTestId("rev-quick-city-results").locator("button").first().click();
  await expect(page.getByTestId("rev-quick-category")).toBeVisible();
  expect(tileRequests).toBe(0);
  expect(fixtures.overpassQueries.length).toBe(overpassCallsBefore);

  // Only this explicit action crosses the local Overpass TEST_PROVIDER boundary.
  await page.getByTestId("rev-quick-find-places").click();
  await expect(page.getByTestId("rev-quick-results")).toContainText("连城测试公园甲");
  await expect(page.getByTestId("rev-quick-results")).toContainText("测试来源");
  expect(fixtures.overpassQueries.length).toBe(overpassCallsBefore + 1);

  const candidates = page.locator('[data-testid^="rev-quick-select-"]');
  await expect(candidates).toHaveCount(2);
  await candidates.nth(0).click();
  await candidates.nth(1).click();
  await page.getByTestId("rev-quick-save").click();
  await expect(page.getByTestId("rev-quick-walk")).toContainText("连城测试公园甲");
  await page.getByRole("button", { name: "开始散步" }).click();
  await expect(page.getByTestId("rev-quick-walk")).toContainText("正前往第一站");

  const identity = await page.evaluate(() => ({
    token: sessionStorage.getItem("citynexus.traveler.bearer"),
    journeyId: JSON.parse(localStorage.getItem("citynexus.revolution.firstlook.journey") ?? "null")?.id,
  }));
  expect(identity.token).toBeTruthy();
  expect(identity.journeyId).toMatch(/^[0-9a-f-]{36}$/i);

  await page.reload({ waitUntil: "domcontentloaded" });
  await expect(page.getByTestId("rev-quick-walk")).toContainText("正前往第一站");
  expect(tileRequests).toBe(0);
  if (process.env.CITYNEXUS_CAPTURE_FIRST_HUMAN === "1") {
    mkdirSync(artifactDir, { recursive: true });
    await page.evaluate(() => {
      const section = document.querySelector(".rev-quick");
      if (section) window.scrollTo(0, Math.max(0, window.scrollY + section.getBoundingClientRect().top));
    });
    await page.screenshot({ path: join(artifactDir, screenshot), fullPage: false });
  }

  await context.close();
  return { trace, identity };
}

test("signed browser can move from 连城 to a sourced private GO walk with blank map tiles", async ({ browser, request }) => {
  const fixtures = await startProviderFixtures();
  try {
    const mobile = await walkThrough(browser, fixtures, { width: 390, height: 844 }, "20261015-first-human-signed-testprovider-mobile.png");
    expect(mobile.trace.some((line) => line.startsWith("POST /api/v1/journeys/:id/bootstrap-city-search 200"))).toBeTruthy();
    expect(mobile.trace.some((line) => line.startsWith("POST /api/v1/journeys/:id/bootstrap-discovery 200"))).toBeTruthy();
    expect(mobile.trace.some((line) => line.startsWith("POST /api/v1/journeys/:id/bootstrap-discovery/pocket-walk 200"))).toBeTruthy();
    expect(mobile.trace.some((line) => line.startsWith("POST /api/v1/journeys/:id/bootstrap-shortlist/pocket-walk/go 200"))).toBeTruthy();

    const outsider = await request.post("/api/v1/travelers", {
      data: { display_name: "Unrelated signed member", locale: "zh-CN", timezone: "Asia/Shanghai" },
    });
    expect(outsider.status()).toBe(201);
    const outsiderBody = await outsider.json() as { access_token: string };
    const privateRead = await request.get(
      `${apiURL}/api/v1/journeys/${mobile.identity.journeyId}/bootstrap-shortlist`,
      { headers: { Authorization: `Bearer ${outsiderBody.access_token}` } },
    );
    expect([403, 404]).toContain(privateRead.status());

    // The backend enforces a global geocoder spacing gate. Wait before the
    // second viewport's independent signed journey instead of racing the gate.
    await new Promise((resolve) => setTimeout(resolve, 1100));
    const desktop = await walkThrough(browser, fixtures, { width: 1440, height: 900 }, "20261015-first-human-signed-testprovider-desktop.png");
    expect(desktop.trace.some((line) => line.startsWith("POST /api/v1/journeys/:id/bootstrap-city-search 200"))).toBeTruthy();
    expect(desktop.trace.some((line) => line.startsWith("POST /api/v1/journeys/:id/bootstrap-shortlist/pocket-walk/go 200"))).toBeTruthy();

    expect(fixtures.cityQueries.length).toBeGreaterThanOrEqual(1);
    expect(fixtures.cityQueries.length).toBeLessThanOrEqual(2);
    expect(fixtures.cityQueries.every((query) => query === "连城")).toBeTruthy();
    expect(fixtures.overpassQueries).toHaveLength(2);
    expect(fixtures.overpassQueries.every((query) => query.includes("around:2500,25.7084,116.7566"))).toBeTruthy();
    expect([...mobile.trace, ...desktop.trace].some((line) => line.includes("trial-ai-discovery"))).toBeFalsy();
    test.info().annotations.push({
      type: "signed-api-trace",
      description: [...mobile.trace, ...desktop.trace].join("\n"),
    });
    console.log("[first-human signed API trace]\n" + [...mobile.trace, ...desktop.trace].join("\n"));
  } finally {
    await Promise.all([close(fixtures.cityServer), close(fixtures.overpassServer)]);
  }
});
