import { createServer, type IncomingMessage, type ServerResponse } from "node:http";
import { expect, test, type APIRequestContext } from "@playwright/test";
import { execFileSync } from "node:child_process";

const API = `http://127.0.0.1:${Number(process.env.CITYNEXUS_BACKEND_PORT ?? 8000)}`;
const CITY_SEARCH_FIXTURE_PORT = 8261;
const OVERPASS_FIXTURE_PORT = 8262;
const VIEWPORT = { width: 390, height: 844 };
test.use({ viewport: VIEWPORT, hasTouch: true });

async function post<T>(request: APIRequestContext, path: string, data: unknown): Promise<T> {
  const response = await request.post(`${API}${path}`, { data });
  if (!response.ok()) throw new Error(`${path} -> ${response.status()}: ${(await response.text()).slice(0, 300)}`);
  return response.json() as Promise<T>;
}

function addCollaboratorToIsolatedJourney(journeyId: string, ownerId: string, collaboratorId: string) {
  const python = process.env.CITYNEXUS_PYTHON;
  if (!python) throw new Error("CITYNEXUS_PYTHON is required for the signed-member fixture");
  const script = [
    "from datetime import datetime, timezone",
    "from uuid import uuid4",
    "import sys",
    "from app.db.session import SessionLocal",
    "from app.db.models import JourneyMember",
    "journey_id, owner_id, collaborator_id = sys.argv[1:4]",
    "stamp = datetime.now(timezone.utc).isoformat()",
    "with SessionLocal() as session:",
    "    session.add(JourneyMember(id=str(uuid4()), journey_id=journey_id, traveler_id=collaborator_id, role='COLLABORATOR', invited_by=owner_id, expires_at=None, joined_at=stamp, removed_at=None, preferences_json='{}', created_at=stamp, updated_at=stamp))",
    "    session.commit()",
  ].join("\n");
  const directEnv = { ...process.env };
  delete directEnv.CITYNEXUS_E2E_RUN_ID;
  execFileSync(python, ["-c", script, journeyId, ownerId, collaboratorId], {
    cwd: "../backend",
    env: directEnv,
    stdio: "pipe",
    timeout: 15_000,
  });
}

function createProviderFixtures() {
  const cityCalls: string[] = [];
  const overpassCalls: string[] = [];
  const cityServer = createServer((_request, response) => {
    cityCalls.push("Shanghai");
    response.writeHead(200, { "content-type": "application/json" });
    response.end(JSON.stringify([{
      place_id: 107001,
      osm_type: "relation",
      osm_id: 107001,
      lat: "31.2304",
      lon: "121.4737",
      display_name: "Shanghai, China",
      type: "city",
      class: "place",
    }]));
  });
  const overpassServer = createServer((request: IncomingMessage, response: ServerResponse) => {
    const chunks: Buffer[] = [];
    request.on("data", (chunk: Buffer) => chunks.push(chunk));
    request.on("end", () => {
      overpassCalls.push(new URLSearchParams(Buffer.concat(chunks).toString("utf8")).get("data") ?? "");
      response.writeHead(200, { "content-type": "application/json" });
      response.end(JSON.stringify({
        version: 0.6,
        generator: "R107 controlled TEST_PROVIDER boundary",
        elements: [
          { type: "node", id: 107011, lat: 31.2304, lon: 121.4737, tags: { name: "R107 Shanghai Museum", tourism: "museum" } },
          { type: "node", id: 107012, lat: 31.231, lon: 121.474, tags: { name: "R107 Shanghai Gallery", tourism: "gallery" } },
          { type: "node", id: 107013, lat: 31.2315, lon: 121.4745, tags: { name: "R107 Shanghai Park", leisure: "park" } },
        ],
      }));
    });
  });
  const ready = Promise.all([
    new Promise<void>((resolve, reject) => { cityServer.once("error", reject); cityServer.listen(CITY_SEARCH_FIXTURE_PORT, "127.0.0.1", resolve); }),
    new Promise<void>((resolve, reject) => { overpassServer.once("error", reject); overpassServer.listen(OVERPASS_FIXTURE_PORT, "127.0.0.1", resolve); }),
  ]);
  return { cityServer, overpassServer, cityCalls, overpassCalls, ready };
}

test("R107 directly saves current manual discovery into a private ordered Pocket Walk", async ({ browser, page, request }) => {
  const provider = createProviderFixtures();
  await provider.ready;
  try {
    const owner = await post<{ id: string; access_token: string }>(request, "/api/v1/travelers", {
      display_name: `R107 owner ${Date.now()}`,
      locale: "en-GB",
      timezone: "Asia/Shanghai",
    });
    const collaborator = await post<{ id: string; access_token: string }>(request, "/api/v1/travelers", {
      display_name: `R107 collaborator ${Date.now()}`,
      locale: "en-GB",
      timezone: "Asia/Shanghai",
    });
    const journey = await post<{ id: string }>(request, "/api/v1/journeys", {
      traveler_id: owner.id,
      title: "R107 discovery to my Pocket Walk",
      city_code: `CN-R107-${Date.now()}`,
      timezone: "Asia/Shanghai",
      start_at: "2026-10-20T10:00:00+08:00",
      end_at: "2026-10-21T18:00:00+08:00",
      budget: { amount_minor: 10000, currency: "CNY" },
    });
    addCollaboratorToIsolatedJourney(journey.id, owner.id, collaborator.id);

    await page.context().route("https://www.google.com/maps/dir/**", async (route) => {
      await route.fulfill({ status: 200, contentType: "text/html", body: "R107 public destination-only map" });
    });
    await page.addInitScript(({ journeyId, token }) => {
      localStorage.setItem("citynexus.v8.journey_id", journeyId);
      sessionStorage.setItem("citynexus.traveler.bearer", token);
    }, { journeyId: journey.id, token: owner.access_token });
    await page.goto("/v8/hub", { waitUntil: "domcontentloaded" });
    const panel = page.getByTestId("bootstrap-discovery");
    await expect(panel.getByTestId("bootstrap-discovery-readiness")).toContainText("TEST_PROVIDER");
    await panel.getByTestId("bootstrap-source-manual").click();
    await panel.getByTestId("bootstrap-city-search-query").fill("Shanghai");
    await panel.getByTestId("bootstrap-city-search-consent").check();
    await panel.getByTestId("bootstrap-city-search-submit").click();
    await expect(panel.getByTestId("bootstrap-city-search-results")).toContainText("Shanghai, China");
    await panel.getByTestId("bootstrap-city-result-0").click();
    await panel.getByTestId("bootstrap-osm-map-link").fill("https://www.openstreetmap.org/#map=13/31.2304/121.4737");
    await panel.getByTestId("bootstrap-osm-map-link-apply").click();
    await panel.getByTestId("bootstrap-public-area-confirm").click();
    await expect(panel.getByTestId("bootstrap-selected-center")).toContainText("31.230400, 121.473700");
    await panel.getByTestId("bootstrap-city-label-confirm").check();
    await panel.getByTestId("bootstrap-intent-ART_HISTORY").click();
    await panel.getByTestId("bootstrap-provider-consent").check();
    await panel.getByTestId("bootstrap-search").click();
    await expect(panel.getByTestId("bootstrap-discovery-outcome")).toContainText("FOUND_2+");
    const results = panel.getByTestId("bootstrap-results");
    await expect(results).toContainText("R107 Shanghai Museum");
    await expect(results).toContainText("opening UNKNOWN");
    await expect(results).toContainText("price UNKNOWN");
    await expect(results).toContainText("ETA UNKNOWN");
    await expect(panel.getByTestId("bootstrap-discovery-pocket-walk")).toBeVisible();
    const firstCandidate = results.locator('[data-testid^="bootstrap-candidate-"]').nth(0);
    const secondCandidate = results.locator('[data-testid^="bootstrap-candidate-"]').nth(1);
    const firstId = (await firstCandidate.getAttribute("data-testid"))!.replace("bootstrap-candidate-", "");
    const secondId = (await secondCandidate.getAttribute("data-testid"))!.replace("bootstrap-candidate-", "");
    const firstName = (await firstCandidate.locator("h3").innerText()).trim();
    const secondName = (await secondCandidate.locator("h3").innerText()).trim();
    const discoveryWalk = panel.getByTestId("bootstrap-discovery-pocket-walk");
    await discoveryWalk.getByTestId(`bootstrap-discovery-pocket-first-${firstId}`).click();
    await discoveryWalk.getByTestId(`bootstrap-discovery-pocket-second-${secondId}`).click();
    await discoveryWalk.getByTestId("bootstrap-discovery-pocket-budget").selectOption("20");
    await discoveryWalk.getByTestId("bootstrap-discovery-pocket-consent").check();
    await discoveryWalk.getByTestId("bootstrap-discovery-pocket-save").click();
    await expect(panel.getByTestId("bootstrap-discovery-pocket-message")).toContainText("saved as a private Pocket Walk");
    const pocketCard = panel.getByTestId("bootstrap-pocket-walk-card");
    await expect(pocketCard).toBeVisible();
    await expect(panel.getByTestId("bootstrap-pocket-walk-stops")).toContainText(`1. ${firstName}`);
    await expect(panel.getByTestId("bootstrap-pocket-walk-stops")).toContainText(`2. ${secondName}`);
    expect(provider.overpassCalls).toHaveLength(1);

    await pocketCard.getByTestId("bootstrap-pocket-navigate-first").click();
    await panel.getByTestId("bootstrap-shortlist-navigation-consent-checkbox").check();
    const firstMap = page.waitForEvent("popup");
    await panel.getByTestId("bootstrap-shortlist-navigation-confirm").click();
    const firstMapPage = await firstMap;
    await firstMapPage.waitForURL(/google\.com\/maps\/dir/);
    expect(firstMapPage.url()).not.toContain("origin=");
    await firstMapPage.close();
    await pocketCard.getByTestId("bootstrap-pocket-open-walk").click();
    await panel.getByTestId("bootstrap-two-stop-consent-checkbox").check();
    const walkMap = page.waitForEvent("popup");
    await panel.getByTestId("bootstrap-two-stop-confirm").click();
    const walkMapPage = await walkMap;
    await walkMapPage.waitForURL(/google\.com\/maps\/dir/);
    expect(new URL(walkMapPage.url()).searchParams.get("travelmode")).toBe("walking");
    await walkMapPage.close();

    await page.reload({ waitUntil: "domcontentloaded" });
    const reloadedPanel = page.getByTestId("bootstrap-discovery");
    await expect(reloadedPanel.getByTestId("bootstrap-pocket-walk-card")).toBeVisible();
    await expect(reloadedPanel.getByTestId("bootstrap-pocket-walk-stops")).toContainText(`1. ${firstName}`);
    await expect(reloadedPanel.getByTestId("bootstrap-pocket-walk-budget")).toHaveValue("20");

    const collaboratorPage = await browser.newPage({ viewport: VIEWPORT });
    await collaboratorPage.addInitScript(({ journeyId, token }) => {
      localStorage.setItem("citynexus.v8.journey_id", journeyId);
      sessionStorage.setItem("citynexus.traveler.bearer", token);
    }, { journeyId: journey.id, token: collaborator.access_token });
    await collaboratorPage.goto("/v8/hub", { waitUntil: "domcontentloaded" });
    const collaboratorPanel = collaboratorPage.getByTestId("bootstrap-discovery");
    await expect(collaboratorPanel.getByTestId("bootstrap-pocket-walk-empty")).toBeVisible();
    await expect(collaboratorPanel).not.toContainText(/R107 Shanghai (Museum|Gallery)/);
    await collaboratorPage.close();

    // Run one fresh discovery so the second direct save is a real browser request.
    await page.waitForTimeout(5500);
    await reloadedPanel.getByTestId("bootstrap-source-manual").click();
    await reloadedPanel.getByTestId("bootstrap-city-search-query").fill("Shanghai");
    await reloadedPanel.getByTestId("bootstrap-city-search-consent").check();
    await reloadedPanel.getByTestId("bootstrap-city-search-submit").click();
    await expect(reloadedPanel.getByTestId("bootstrap-city-search-results")).toContainText("Shanghai, China");
    await reloadedPanel.getByTestId("bootstrap-city-result-0").click();
    await reloadedPanel.getByTestId("bootstrap-osm-map-link").fill("https://www.openstreetmap.org/#map=13/31.2304/121.4737");
    await reloadedPanel.getByTestId("bootstrap-osm-map-link-apply").click();
    await reloadedPanel.getByTestId("bootstrap-public-area-confirm").click();
    await reloadedPanel.getByTestId("bootstrap-city-label-confirm").check();
    await reloadedPanel.getByTestId("bootstrap-intent-ART_HISTORY").click();
    await reloadedPanel.getByTestId("bootstrap-provider-consent").check();
    await reloadedPanel.getByTestId("bootstrap-search").click();
    await expect(reloadedPanel.getByTestId("bootstrap-discovery-outcome")).toContainText("FOUND_2+");
    const secondDiscovery = reloadedPanel.getByTestId("bootstrap-discovery-pocket-walk");
    const secondResults = reloadedPanel.getByTestId("bootstrap-results");
    const secondFirstId = (await secondResults.locator('[data-testid^="bootstrap-candidate-"]').nth(0).getAttribute("data-testid"))!.replace("bootstrap-candidate-", "");
    const secondSecondId = (await secondResults.locator('[data-testid^="bootstrap-candidate-"]').nth(1).getAttribute("data-testid"))!.replace("bootstrap-candidate-", "");
    await secondDiscovery.getByTestId(`bootstrap-discovery-pocket-first-${secondFirstId}`).click();
    await secondDiscovery.getByTestId(`bootstrap-discovery-pocket-second-${secondSecondId}`).click();
    await secondDiscovery.getByTestId("bootstrap-discovery-pocket-consent").check();

    const ownerResponseGate = { release: () => {} };
    const heldOwnerResponse = new Promise<void>((resolve) => { ownerResponseGate.release = resolve; });
    let ownerSaveCaptured = 0;
    await page.route(`**/api/v1/journeys/${journey.id}/bootstrap-discovery/pocket-walk`, async (route) => {
      if (route.request().method() !== "POST") {
        await route.continue();
        return;
      }
      const realBackendResponse = await route.fetch();
      ownerSaveCaptured += 1;
      await heldOwnerResponse;
      await route.fulfill({ response: realBackendResponse });
    });
    await secondDiscovery.getByTestId("bootstrap-discovery-pocket-save").click();
    await expect.poll(() => ownerSaveCaptured).toBe(1);
    await page.evaluate((token) => {
      sessionStorage.setItem("citynexus.traveler.bearer", token);
      window.dispatchEvent(new CustomEvent("citynexus.traveler.bearer.changed"));
    }, collaborator.access_token);
    await expect(reloadedPanel.getByTestId("bootstrap-pocket-walk-empty")).toBeVisible();
    ownerResponseGate.release();
    await page.waitForTimeout(150);
    await expect(reloadedPanel.getByTestId("bootstrap-pocket-walk-card")).toHaveCount(0);
    await expect(reloadedPanel).not.toContainText(/R107 Shanghai (Museum|Gallery)/);
    await page.unroute(`**/api/v1/journeys/${journey.id}/bootstrap-discovery/pocket-walk`);

    await page.evaluate((token) => {
      sessionStorage.setItem("citynexus.traveler.bearer", token);
      window.dispatchEvent(new CustomEvent("citynexus.traveler.bearer.changed"));
    }, owner.access_token);
    await expect(reloadedPanel.getByTestId("bootstrap-pocket-walk-stops")).toContainText(firstName);
    expect(provider.overpassCalls.length).toBe(2);
  } finally {
    await Promise.all([
      new Promise<void>((resolve) => provider.cityServer.close(() => resolve())),
      new Promise<void>((resolve) => provider.overpassServer.close(() => resolve())),
    ]);
  }
});
