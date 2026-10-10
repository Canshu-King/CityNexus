import { execFileSync } from "node:child_process";
import { createServer } from "node:http";
import { expect, test, type APIRequestContext, type Locator } from "@playwright/test";

const API = `http://127.0.0.1:${Number(process.env.CITYNEXUS_BACKEND_PORT ?? 8000)}`;
const CITY_SEARCH_FIXTURE_PORT = 8213;
const OVERPASS_FIXTURE_PORT = 8214;

test.use({ viewport: { width: 390, height: 844 } });

async function post<T>(request: APIRequestContext, path: string, data: unknown): Promise<T> {
  const response = await request.post(`${API}${path}`, { data });
  if (!response.ok()) throw new Error(`${path} -> ${response.status()}: ${(await response.text()).slice(0, 240)}`);
  return response.json() as Promise<T>;
}

async function createProviderFixtures() {
  const cityCalls: string[] = [];
  const overpassCalls: string[] = [];
  const cityServer = createServer((request, response) => {
    cityCalls.push(request.url ?? "");
    response.writeHead(200, { "content-type": "application/json" });
    response.end(JSON.stringify([{
      place_id: 95001,
      osm_type: "relation",
      osm_id: 95001,
      lat: "31.2304",
      lon: "121.4737",
      display_name: "Shanghai, China",
      type: "city",
      class: "place",
    }]));
  });
  const overpassServer = createServer((request, response) => {
    const chunks: Buffer[] = [];
    request.on("data", (chunk: Buffer) => chunks.push(chunk));
    request.on("end", () => {
      overpassCalls.push(new URLSearchParams(Buffer.concat(chunks).toString("utf8")).get("data") ?? "");
      response.writeHead(200, { "content-type": "application/json" });
      response.end(JSON.stringify({
        version: 0.6,
        generator: "R95 controlled TEST_PROVIDER boundary",
        elements: [{
          type: "node",
          id: 95011,
          lat: 31.2304,
          lon: 121.4737,
          tags: { name: "R95 Shanghai Gallery", tourism: "gallery" },
        }, {
          type: "node",
          id: 95012,
          lat: 31.231,
          lon: 121.474,
          tags: { name: "R95 Shanghai Library", amenity: "library" },
        }],
      }));
    });
  });
  await Promise.all([
    new Promise<void>((resolve, reject) => {
      cityServer.once("error", reject);
      cityServer.listen(CITY_SEARCH_FIXTURE_PORT, "127.0.0.1", resolve);
    }),
    new Promise<void>((resolve, reject) => {
      overpassServer.once("error", reject);
      overpassServer.listen(OVERPASS_FIXTURE_PORT, "127.0.0.1", resolve);
    }),
  ]);
  return {
    cityServer,
    overpassServer,
    cityCalls,
    overpassCalls,
  };
}

function addCollaboratorToIsolatedJourney(journeyId: string, ownerId: string, collaboratorId: string) {
  const python = process.env.CITYNEXUS_PYTHON;
  if (!python) throw new Error("CITYNEXUS_PYTHON is required for the isolated signed-member fixture");
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

async function chooseCenterFromOsmLink(panel: Locator, url: string) {
  await panel.getByTestId("bootstrap-source-manual").click();
  await panel.getByTestId("bootstrap-osm-map-link").fill(url);
  await panel.getByTestId("bootstrap-osm-map-link-apply").click();
  await expect(panel.getByTestId("bootstrap-public-area-pending")).toBeVisible();
  await panel.getByTestId("bootstrap-public-area-confirm").click();
}

test("R95 city jump, honest provider grade, private save, and destination-only resume", async ({ page, request }) => {
  const provider = await createProviderFixtures();
  try {
    const owner = await post<{ id: string; access_token: string }>(request, "/api/v1/travelers", {
      display_name: `R95 owner ${Date.now()}`,
      locale: "en-GB",
      timezone: "Asia/Shanghai",
    });
    const collaborator = await post<{ id: string; access_token: string }>(request, "/api/v1/travelers", {
      display_name: `R95 collaborator ${Date.now()}`,
      locale: "en-GB",
      timezone: "Asia/Shanghai",
    });
    const journey = await post<{ id: string }>(request, "/api/v1/journeys", {
      traveler_id: owner.id,
      title: "R95 city jump",
      city_code: `CN-R95-SH-${Date.now()}`,
      timezone: "Asia/Shanghai",
      start_at: "2026-10-15T10:00:00+08:00",
      end_at: "2026-10-16T18:00:00+08:00",
      budget: { amount_minor: 10000, currency: "CNY" },
    });
    addCollaboratorToIsolatedJourney(journey.id, owner.id, collaborator.id);

    const tileRequests: string[] = [];
    await page.route("https://tile.openstreetmap.org/**", async (route) => {
      tileRequests.push(route.request().url());
      await route.abort();
    });
    await page.route("https://www.google.com/maps/dir/**", async (route) => {
      await route.fulfill({ status: 200, contentType: "text/html", body: "R95 destination-only walking handoff" });
    });
    await page.addInitScript(({ journeyId, token }) => {
      localStorage.setItem("citynexus.v8.journey_id", journeyId);
      sessionStorage.setItem("citynexus.traveler.bearer", token);
    }, { journeyId: journey.id, token: owner.access_token });
    await page.goto("/v8/hub", { waitUntil: "domcontentloaded" });
    const panel = page.getByTestId("bootstrap-discovery");
    await expect(panel.getByTestId("bootstrap-center-required")).toContainText("No provider request will be made yet");

    await panel.getByTestId("bootstrap-source-manual").click();
    await panel.getByTestId("bootstrap-city-search-query").fill("Shanghai");
    await expect.poll(() => provider.cityCalls.length).toBe(0);
    await panel.getByTestId("bootstrap-city-search-consent").check();
    await panel.getByTestId("bootstrap-city-search-submit").click();
    await expect(panel.getByTestId("bootstrap-city-search-results")).toContainText("Shanghai, China");
    expect(provider.cityCalls).toHaveLength(1);
    await expect(panel.getByTestId("bootstrap-city-search-results")).toContainText("TEST_PROVIDER");
    await expect(panel.getByTestId("bootstrap-city-search-results")).toContainText("CITY_CENTROID_UNCERTAIN");

    // A city centroid only moves the camera. Tiles remain a separate release and
    // no map can mount at 0,0 before the result is chosen.
    await panel.getByTestId("bootstrap-city-result-0").click();
    await expect(panel.getByTestId("bootstrap-map-tile-consent")).toBeEnabled();
    expect(tileRequests).toHaveLength(0);
    await panel.getByTestId("bootstrap-map-tile-consent").check();
    await expect(panel.getByTestId("bootstrap-public-map-canvas")).toBeVisible();
    await expect.poll(() => panel.getByTestId("bootstrap-public-map-canvas").evaluate((element) =>
      Boolean((element as HTMLDivElement & { citynexusMap?: unknown }).citynexusMap)
    )).toBeTruthy();
    await panel.getByTestId("bootstrap-public-map-canvas").evaluate((element) => {
      const map = (element as HTMLDivElement & { citynexusMap?: { fire: (name: string, event: unknown) => void } }).citynexusMap;
      map?.fire("click", {
        point: { x: 100, y: 100 },
        lngLat: { lat: 31.2304, lng: 121.4737 },
      });
    });
    await expect(panel.getByTestId("bootstrap-public-area-pending")).toContainText("31.230400, 121.473700");
    await panel.getByTestId("bootstrap-public-area-confirm").click();
    await expect(panel.getByTestId("bootstrap-selected-center")).toContainText("31.230400, 121.473700");
    await expect.poll(() => tileRequests.length).toBeGreaterThan(0);

    await panel.getByTestId("bootstrap-provider-consent").check();
    await panel.getByTestId("bootstrap-search").click();
    await expect(panel.getByTestId("bootstrap-results")).toContainText("R95 Shanghai Gallery");
    expect(provider.overpassCalls).toHaveLength(1);
    const result = panel.getByTestId("bootstrap-results");
    await expect(result).toContainText("TEST_PROVIDER");
    await result.locator('[data-testid^="bootstrap-save-"]').first().click();
    await expect(panel.getByTestId("bootstrap-shortlist")).toContainText(/R95 Shanghai (Gallery|Library)/);
    const savedShortlistText = await panel.getByTestId("bootstrap-shortlist").innerText();
    expect(savedShortlistText).toMatch(/R95 Shanghai (Gallery|Library)/);

    // Signed A/B reads are isolated at the real backend boundary. A separate
    // page gives each member an independent sessionStorage namespace, so the
    // privacy assertion cannot be satisfied by stale UI state.
    const collaboratorPage = await page.context().newPage();
    await collaboratorPage.addInitScript(({ token, journeyId }) => {
      sessionStorage.setItem("citynexus.traveler.bearer", token);
      localStorage.setItem("citynexus.v8.journey_id", journeyId);
    }, { token: collaborator.access_token, journeyId: journey.id });
    await collaboratorPage.goto("/v8/hub", { waitUntil: "domcontentloaded" });
    const collaboratorPanel = collaboratorPage.getByTestId("bootstrap-discovery");
    await expect(collaboratorPanel.getByTestId("bootstrap-shortlist")).toContainText("Saved 0 of 3");
    await expect(collaboratorPanel).not.toContainText(/R95 Shanghai (Gallery|Library)/);
    await collaboratorPage.close();

    const ownerPanel = page.getByTestId("bootstrap-discovery");
    const shortlistItem = await ownerPanel.locator('[data-testid^="bootstrap-shortlist-item-"]').getAttribute("data-testid");
    expect(shortlistItem).toBeTruthy();
    const shortlistId = shortlistItem!.replace("bootstrap-shortlist-item-", "");
    await ownerPanel.getByTestId(`bootstrap-shortlist-go-${shortlistId}`).click();
    await expect(ownerPanel.getByTestId(`bootstrap-shortlist-navigation-consent-${shortlistId}`)).toContainText("destination");
    await ownerPanel.getByTestId("bootstrap-shortlist-navigation-consent-checkbox").check();
    const popupPromise = page.waitForEvent("popup");
    await ownerPanel.getByTestId("bootstrap-shortlist-navigation-confirm").click();
    const popup = await popupPromise;
    await popup.waitForURL(/google\.com\/maps\/dir/);
    expect(popup.url()).toContain("travelmode=walking");
    expect(popup.url()).not.toContain("origin=");
    expect(popup.url()).not.toContain("receipt");
    await popup.close();
    await expect(ownerPanel.getByTestId("bootstrap-explore-state")).toContainText("no Place, PlanVersion");
  } finally {
    await Promise.all([
      new Promise<void>((resolve) => provider.cityServer.close(() => resolve())),
      new Promise<void>((resolve) => provider.overpassServer.close(() => resolve())),
    ]);
  }
});
