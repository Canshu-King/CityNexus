import { execFileSync } from "node:child_process";
import { createServer } from "node:http";
import { expect, test, type APIRequestContext, type Locator } from "@playwright/test";

const API = `http://127.0.0.1:${Number(process.env.CITYNEXUS_BACKEND_PORT ?? 8000)}`;
const CITY_SEARCH_FIXTURE_PORT = 8237;
const OVERPASS_FIXTURE_PORT = 8238;

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
      place_id: 97001,
      osm_type: "relation",
      osm_id: 97001,
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
        generator: "R97 controlled TEST_PROVIDER boundary",
        elements: [{
          type: "node",
          id: 97011,
          lat: 31.2304,
          lon: 121.4737,
          tags: { name: "R97 Shanghai Museum", tourism: "museum" },
        }, {
          type: "node",
          id: 97012,
          lat: 31.231,
          lon: 121.474,
          tags: { name: "R97 Shanghai Gallery", tourism: "gallery" },
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

function readExploreOnlyCounts(journeyId: string, cityCode: string) {
  const python = process.env.CITYNEXUS_PYTHON;
  if (!python) throw new Error("CITYNEXUS_PYTHON is required for the explore-only invariant");
  const script = [
    "import json",
    "import sys",
    "from sqlalchemy import func, select",
    "from app.db.session import SessionLocal",
    "from app.db.models import AgentRun, Booking, GuardianRun, Place, PlanVersion",
    "journey_id, city_code = sys.argv[1:3]",
    "with SessionLocal() as session:",
    "    result = {",
    "        'place_count': session.scalar(select(func.count()).select_from(Place).where(Place.city_code == city_code)),",
    "        'plan_count': session.scalar(select(func.count()).select_from(PlanVersion).where(PlanVersion.journey_id == journey_id)),",
    "        'agent_run_count': session.scalar(select(func.count()).select_from(AgentRun).where(AgentRun.journey_id == journey_id)),",
    "        'guardian_run_count': session.scalar(select(func.count()).select_from(GuardianRun).where(GuardianRun.journey_id == journey_id)),",
    "        'booking_count': session.scalar(select(func.count()).select_from(Booking).where(Booking.journey_id == journey_id)),",
    "    }",
    "    print(json.dumps(result))",
  ].join("\n");
  const directEnv = { ...process.env };
  delete directEnv.CITYNEXUS_E2E_RUN_ID;
  return JSON.parse(execFileSync(python, ["-c", script, journeyId, cityCode], {
    cwd: "../backend",
    env: directEnv,
    encoding: "utf8",
    stdio: "pipe",
    timeout: 15_000,
  }));
}

async function chooseCenterFromOsmLink(panel: Locator, url: string) {
  await panel.getByTestId("bootstrap-source-manual").click();
  await panel.getByTestId("bootstrap-osm-map-link").fill(url);
  await panel.getByTestId("bootstrap-osm-map-link-apply").click();
  await expect(panel.getByTestId("bootstrap-public-area-pending")).toBeVisible();
  await panel.getByTestId("bootstrap-public-area-confirm").click();
}

test("R97 one-tap intent outing, private save, and destination-only resume", async ({ page, request }) => {
  const provider = await createProviderFixtures();
  try {
    const owner = await post<{ id: string; access_token: string }>(request, "/api/v1/travelers", {
      display_name: `R97 owner ${Date.now()}`,
      locale: "en-GB",
      timezone: "Asia/Shanghai",
    });
    const collaborator = await post<{ id: string; access_token: string }>(request, "/api/v1/travelers", {
      display_name: `R97 collaborator ${Date.now()}`,
      locale: "en-GB",
      timezone: "Asia/Shanghai",
    });
    const cityCode = `CN-R97-SH-${Date.now()}`;
    const journey = await post<{ id: string }>(request, "/api/v1/journeys", {
      traveler_id: owner.id,
      title: "R97 first outing",
      city_code: cityCode,
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
    await page.context().route("https://www.google.com/maps/dir/**", async (route) => {
      await route.fulfill({ status: 200, contentType: "text/html", body: "R97 destination-only walking handoff" });
    });
    await page.addInitScript(({ journeyId, token }) => {
      localStorage.setItem("citynexus.v8.journey_id", journeyId);
      sessionStorage.setItem("citynexus.traveler.bearer", token);
    }, { journeyId: journey.id, token: owner.access_token });
    await page.goto("/v8/hub", { waitUntil: "domcontentloaded" });
    // The dependent real-seed project can restore a different sessionStorage
    // snapshot. Reassert this fresh signed member at the browser boundary and
    // emit the product's normal identity-change signal before private reads.
    await page.evaluate((token) => {
      sessionStorage.setItem("citynexus.traveler.bearer", token);
      window.dispatchEvent(new CustomEvent("citynexus.traveler.bearer.changed"));
    }, owner.access_token);
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

    await panel.getByTestId("bootstrap-intent-ART_HISTORY").click();
    await expect(panel.getByTestId("bootstrap-intent-selected")).toContainText("museum/gallery");
    await panel.getByTestId("bootstrap-provider-consent").check();
    await panel.getByTestId("bootstrap-search").click();
    await expect(panel.getByTestId("bootstrap-results")).toContainText("R97 Shanghai Museum");
    expect(provider.overpassCalls).toHaveLength(1);
    expect(provider.overpassCalls[0]).toContain('"tourism"~"museum|gallery"');
    const result = panel.getByTestId("bootstrap-results");
    await expect(result).toContainText("TEST_PROVIDER");
    await expect(result.locator('[data-testid^="bootstrap-intent-reason-"]').first()).toContainText("museum, gallery");
    await result.locator('[data-testid^="bootstrap-save-"]').first().click();
    await expect(panel.getByTestId("bootstrap-shortlist")).toContainText("Saved 1 of 3");
    await result.locator('[data-testid^="bootstrap-save-"]').nth(1).click();
    await expect(panel.getByTestId("bootstrap-shortlist")).toContainText("Saved 2 of 3");
    const savedShortlistText = await panel.getByTestId("bootstrap-shortlist").innerText();
    expect(savedShortlistText).toContain("R97 Shanghai Museum");
    expect(savedShortlistText).toContain("R97 Shanghai Gallery");
    expect(readExploreOnlyCounts(journey.id, cityCode)).toEqual({
      place_count: 0,
      plan_count: 0,
      agent_run_count: 0,
      guardian_run_count: 0,
      booking_count: 0,
    });

    // Signed A/B reads are isolated at the real backend boundary. A separate
    // page gives each member an independent sessionStorage namespace, so the
    // privacy assertion cannot be satisfied by stale UI state.
    const collaboratorPage = await page.context().newPage();
    await collaboratorPage.addInitScript(({ token, journeyId }) => {
      sessionStorage.setItem("citynexus.traveler.bearer", token);
      localStorage.setItem("citynexus.v8.journey_id", journeyId);
    }, { token: collaborator.access_token, journeyId: journey.id });
    await collaboratorPage.goto("/v8/hub", { waitUntil: "domcontentloaded" });
    await collaboratorPage.evaluate((token) => {
      sessionStorage.setItem("citynexus.traveler.bearer", token);
      window.dispatchEvent(new CustomEvent("citynexus.traveler.bearer.changed"));
    }, collaborator.access_token);
    const collaboratorPanel = collaboratorPage.getByTestId("bootstrap-discovery");
    await expect(collaboratorPanel.getByTestId("bootstrap-shortlist")).toContainText("Saved 0 of 3");
    await expect(collaboratorPanel).not.toContainText(/R97 Shanghai (Museum|Gallery)/);
    await expect(collaboratorPanel.getByTestId("bootstrap-intent-required")).toBeVisible();
    await expect(collaboratorPanel).not.toContainText("museum/gallery");
    await collaboratorPage.close();

    const ownerPanel = page.getByTestId("bootstrap-discovery");
    const shortlistItems = ownerPanel.locator('[data-testid^="bootstrap-shortlist-item-"]');
    await expect(shortlistItems).toHaveCount(2);
    const shortlistIds = await shortlistItems.evaluateAll((elements) =>
      elements.map((element) => (element.getAttribute("data-testid") ?? "").replace("bootstrap-shortlist-item-", "")),
    );
    expect(shortlistIds).toHaveLength(2);
    const shortlistId = shortlistIds[0];
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
    expect(readExploreOnlyCounts(journey.id, cityCode)).toEqual({
      place_count: 0,
      plan_count: 0,
      agent_run_count: 0,
      guardian_run_count: 0,
      booking_count: 0,
    });

    await ownerPanel.getByTestId(`bootstrap-two-stop-first-${shortlistIds[0]}`).click();
    await ownerPanel.getByTestId(`bootstrap-two-stop-second-${shortlistIds[1]}`).click();
    await expect(ownerPanel.getByTestId("bootstrap-two-stop-state")).toContainText("Two distinct public stops");
    await ownerPanel.getByTestId("bootstrap-two-stop-consent-checkbox").check();
    const twoStopPopupPromise = page.waitForEvent("popup");
    await ownerPanel.getByTestId("bootstrap-two-stop-confirm").click();
    const twoStopPopup = await twoStopPopupPromise;
    await twoStopPopup.waitForURL(/google\.com\/maps\/dir/);
    const twoStopUrl = new URL(twoStopPopup.url());
    expect(twoStopUrl.hostname).toBe("www.google.com");
    expect(twoStopUrl.searchParams.get("travelmode")).toBe("walking");
    expect(twoStopUrl.searchParams.get("origin")).toBe("31.2304000,121.4737000");
    expect(twoStopUrl.searchParams.get("destination")).toBe("31.2310000,121.4740000");
    expect(twoStopPopup.url()).not.toContain("foreground_gps");
    expect(twoStopPopup.url()).not.toContain("receipt");
    await twoStopPopup.close();
    await expect(ownerPanel.getByTestId("bootstrap-two-stop-notice")).toContainText("Route time");
    await expect(ownerPanel.getByTestId("bootstrap-two-stop-notice")).toContainText("Journey was not started");
    expect(readExploreOnlyCounts(journey.id, cityCode)).toEqual({
      place_count: 0,
      plan_count: 0,
      agent_run_count: 0,
      guardian_run_count: 0,
      booking_count: 0,
    });
  } finally {
    await Promise.all([
      new Promise<void>((resolve) => provider.cityServer.close(() => resolve())),
      new Promise<void>((resolve) => provider.overpassServer.close(() => resolve())),
    ]);
  }
});
