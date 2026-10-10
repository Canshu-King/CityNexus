import { execFileSync } from "node:child_process";
import { createServer } from "node:http";
import { expect, test, type APIRequestContext, type Locator } from "@playwright/test";

const API = `http://127.0.0.1:${Number(process.env.CITYNEXUS_BACKEND_PORT ?? 8000)}`;
const CITY_SEARCH_FIXTURE_PORT = 8241;
const OVERPASS_FIXTURE_PORT = 8242;
const ROUTER_FIXTURE_PORT = 8243;

test.use({ viewport: { width: 390, height: 844 } });

async function post<T>(request: APIRequestContext, path: string, data: unknown): Promise<T> {
  const response = await request.post(`${API}${path}`, { data });
  if (!response.ok()) throw new Error(`${path} -> ${response.status()}: ${(await response.text()).slice(0, 240)}`);
  return response.json() as Promise<T>;
}

async function createProviderFixtures() {
  const cityCalls: string[] = [];
  const overpassCalls: string[] = [];
  const routeCalls: Array<Record<string, unknown>> = [];
  const routeState = { available: true };
  const cityServer = createServer((request, response) => {
    cityCalls.push(request.url ?? "");
    response.writeHead(200, { "content-type": "application/json" });
    response.end(JSON.stringify([{
      place_id: 98001,
      osm_type: "relation",
      osm_id: 98001,
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
      generator: "R99 controlled TEST_PROVIDER boundary",
        elements: [{
          type: "node",
          id: 99011,
          lat: 31.2304,
          lon: 121.4737,
          tags: { name: "R99 Shanghai Museum", tourism: "museum" },
        }, {
          type: "node",
          id: 99012,
          lat: 31.231,
          lon: 121.474,
          tags: { name: "R99 Shanghai Gallery", tourism: "gallery" },
        }, {
          type: "node",
          id: 99013,
          lat: 31.2315,
          lon: 121.4745,
          tags: { name: "R99 Shanghai Park", leisure: "park" },
        }],
      }));
    });
  });
  const routeServer = createServer((request, response) => {
    const chunks: Buffer[] = [];
    request.on("data", (chunk: Buffer) => chunks.push(chunk));
    request.on("end", () => {
      const raw = Buffer.concat(chunks).toString("utf8");
      const body = JSON.parse(raw || "{}") as Record<string, unknown>;
      routeCalls.push(body);
      if (!routeState.available) {
        response.writeHead(503, { "content-type": "application/json" });
        response.end(JSON.stringify({ error: "controlled unavailable" }));
        return;
      }
      response.writeHead(200, { "content-type": "application/json" });
      response.end(JSON.stringify({
        trip: {
          summary: {
            time: body.locations && Array.isArray(body.locations) &&
              (body.locations as Array<{ lon?: number }>)[1]?.lon === 121.474
              ? 2520
              : 780,
            length: body.locations && Array.isArray(body.locations) &&
              (body.locations as Array<{ lon?: number }>)[1]?.lon === 121.474
              ? 3.1
              : 0.9,
          },
          legs: [{}],
        },
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
    new Promise<void>((resolve, reject) => {
      routeServer.once("error", reject);
      routeServer.listen(ROUTER_FIXTURE_PORT, "127.0.0.1", resolve);
    }),
  ]);
  return {
    cityServer,
    overpassServer,
    routeServer,
    cityCalls,
    overpassCalls,
    routeCalls,
    routeState,
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

test("R99 adaptive short walk compares, chooses, and fails closed", async ({ page, request }) => {
  const provider = await createProviderFixtures();
  try {
    const owner = await post<{ id: string; access_token: string }>(request, "/api/v1/travelers", {
      display_name: `R99 owner ${Date.now()}`,
      locale: "en-GB",
      timezone: "Asia/Shanghai",
    });
    const collaborator = await post<{ id: string; access_token: string }>(request, "/api/v1/travelers", {
      display_name: `R99 collaborator ${Date.now()}`,
      locale: "en-GB",
      timezone: "Asia/Shanghai",
    });
    const cityCode = `CN-R99-SH-${Date.now()}`;
    const journey = await post<{ id: string }>(request, "/api/v1/journeys", {
      traveler_id: owner.id,
      title: "R99 first outing",
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
      await route.fulfill({ status: 200, contentType: "text/html", body: "R99 destination-only walking handoff" });
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
    await expect(panel.getByTestId("bootstrap-results")).toContainText("R99 Shanghai Museum");
    expect(provider.overpassCalls).toHaveLength(1);
    expect(provider.overpassCalls[0]).toContain('"tourism"~"museum|gallery"');
    const result = panel.getByTestId("bootstrap-results");
    await expect(result).toContainText("TEST_PROVIDER");
    await expect(result.locator('[data-testid^="bootstrap-intent-reason-"]').first()).toContainText("museum, gallery");
    await result.locator('[data-testid^="bootstrap-save-"]').first().click();
    await expect(panel.getByTestId("bootstrap-shortlist")).toContainText("Saved 1 of 3");
    await result.locator('[data-testid^="bootstrap-save-"]').nth(1).click();
    await expect(panel.getByTestId("bootstrap-shortlist")).toContainText("Saved 2 of 3");
    await result.locator('[data-testid^="bootstrap-save-"]').nth(2).click();
    await expect(panel.getByTestId("bootstrap-shortlist")).toContainText("Saved 3 of 3");
    const savedShortlistText = await panel.getByTestId("bootstrap-shortlist").innerText();
    expect(savedShortlistText).toContain("R99 Shanghai Museum");
    expect(savedShortlistText).toContain("R99 Shanghai Gallery");
    expect(savedShortlistText).toContain("R99 Shanghai Park");
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
    await expect(collaboratorPanel).not.toContainText(/R99 Shanghai (Museum|Gallery|Park)/);
    await expect(collaboratorPanel.getByTestId("bootstrap-intent-required")).toBeVisible();
    await expect(collaboratorPanel).not.toContainText("museum/gallery");
    await collaboratorPage.close();

    const ownerPanel = page.getByTestId("bootstrap-discovery");
    const shortlistItems = ownerPanel.locator('[data-testid^="bootstrap-shortlist-item-"]');
    await expect(shortlistItems).toHaveCount(3);
    const shortlistIds = await shortlistItems.evaluateAll((elements) =>
      elements.map((element) => (element.getAttribute("data-testid") ?? "").replace("bootstrap-shortlist-item-", "")),
    );
    expect(shortlistIds).toHaveLength(3);
    const shortlistRecords = await shortlistItems.evaluateAll((elements) => elements.map((element) => ({
      id: (element.getAttribute("data-testid") ?? "").replace("bootstrap-shortlist-item-", ""),
      text: element.textContent ?? "",
    })));
    const museumId = shortlistRecords.find((item) => item.text.includes("R99 Shanghai Museum"))?.id;
    const galleryId = shortlistRecords.find((item) => item.text.includes("R99 Shanghai Gallery"))?.id;
    const parkId = shortlistRecords.find((item) => item.text.includes("R99 Shanghai Park"))?.id;
    expect(museumId).toBeTruthy();
    expect(galleryId).toBeTruthy();
    expect(parkId).toBeTruthy();
    expect(museumId).not.toBe(galleryId);
    expect(museumId).not.toBe(parkId);
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

    await ownerPanel.getByTestId(`bootstrap-two-stop-first-${museumId!}`).click();
    await ownerPanel.getByTestId(`bootstrap-two-stop-second-${galleryId!}`).click();
    await expect(ownerPanel.getByTestId("bootstrap-two-stop-state")).toContainText("Two distinct public stops");

    // R99 compares the current second stop with one saved alternative. The
    // controlled Valhalla boundary returns 42 minutes for the current stop and
    // 13 minutes for the alternative, with exactly two public-to-public calls.
    await ownerPanel.getByTestId("bootstrap-adaptive-walk-budget").selectOption("20");
    await ownerPanel.getByTestId("bootstrap-adaptive-walk-consent-checkbox").check();
    await ownerPanel.getByTestId("bootstrap-adaptive-walk-check").click();
    const adaptiveResult = ownerPanel.getByTestId("bootstrap-adaptive-walk-result");
    await expect(adaptiveResult).toContainText("42 min estimated");
    await expect(adaptiveResult).toContainText("13 min estimated");
    await expect(adaptiveResult).toContainText("WITHIN_MY_LEG_BUDGET");
    await expect(adaptiveResult).toContainText("TEST_PROVIDER_EMULATOR");
    await expect(adaptiveResult).toContainText("observed");
    await expect(ownerPanel.getByTestId("bootstrap-adaptive-choose-alternative")).toBeVisible();
    expect(provider.routeCalls).toHaveLength(2);
    for (const routeCall of provider.routeCalls) {
      expect(routeCall.costing).toBe("pedestrian");
      expect(routeCall.locations).toHaveLength(2);
      const routeRequestText = JSON.stringify(routeCall).toLowerCase();
      for (const withheld of ["journey", "member", "traveler", "gps", "receipt", "private", "query_center"]) {
        expect(routeRequestText).not.toContain(withheld);
      }
    }
    expect(provider.routeCalls[0].locations).toEqual([
      { lat: 31.2304, lon: 121.4737 },
      { lat: 31.231, lon: 121.474 },
    ]);
    expect(provider.routeCalls[1].locations).toEqual([
      { lat: 31.2304, lon: 121.4737 },
      { lat: 31.2315, lon: 121.4745 },
    ]);
    expect(readExploreOnlyCounts(journey.id, cityCode)).toEqual({
      place_count: 0,
      plan_count: 0,
      agent_run_count: 0,
      guardian_run_count: 0,
      booking_count: 0,
    });

    // Choosing the suggestion mutates only the private draft ordering and
    // invalidates the comparison and all prior map/route consent.
    await ownerPanel.getByTestId("bootstrap-adaptive-choose-alternative").click();
    await expect(ownerPanel.getByTestId("bootstrap-two-stop-order")).toContainText("R99 Shanghai Museum");
    await expect(ownerPanel.getByTestId("bootstrap-two-stop-order")).toContainText("R99 Shanghai Park");
    await expect(ownerPanel.getByTestId("bootstrap-adaptive-walk-result")).toHaveCount(0);
    await expect(ownerPanel.getByTestId("bootstrap-two-stop-consent-checkbox")).toBeVisible();
    await ownerPanel.getByTestId("bootstrap-two-stop-consent-checkbox").check();
    const twoStopPopupPromise = page.waitForEvent("popup");
    await ownerPanel.getByTestId("bootstrap-two-stop-confirm").click();
    const twoStopPopup = await twoStopPopupPromise;
    await twoStopPopup.waitForURL(/google\.com\/maps\/dir/);
    const twoStopUrl = new URL(twoStopPopup.url());
    expect(twoStopUrl.hostname).toBe("www.google.com");
    expect(twoStopUrl.searchParams.get("travelmode")).toBe("walking");
    expect(twoStopUrl.searchParams.get("origin")).toBe("31.2304000,121.4737000");
    expect(twoStopUrl.searchParams.get("destination")).toBe("31.2315000,121.4745000");
    expect(twoStopPopup.url()).not.toContain("foreground_gps");
    expect(twoStopPopup.url()).not.toContain("receipt");
    await twoStopPopup.close();
    await expect(ownerPanel.getByTestId("bootstrap-two-stop-notice")).toContainText("Route time");
    await expect(ownerPanel.getByTestId("bootstrap-two-stop-notice")).toContainText("Journey was not started");

    // A controlled 503 on a fresh comparison is rendered as ROUTE_UNVERIFIED;
    // the UI must never fabricate either duration or the suggestion.
    await ownerPanel.getByTestId(`bootstrap-two-stop-second-${galleryId!}`).click();
    await ownerPanel.getByTestId("bootstrap-adaptive-walk-budget").selectOption("20");
    await ownerPanel.getByTestId("bootstrap-adaptive-walk-consent-checkbox").check();
    provider.routeState.available = false;
    await ownerPanel.getByTestId("bootstrap-adaptive-walk-check").click();
    const unavailableResult = ownerPanel.getByTestId("bootstrap-adaptive-walk-result");
    await expect(unavailableResult).toContainText("ROUTE_UNVERIFIED");
    await expect(unavailableResult).toContainText("ROUTE_PROVIDER_UNAVAILABLE");
    await expect(unavailableResult).not.toContainText("42 min");
    await expect(unavailableResult).not.toContainText("13 min");
    await expect(ownerPanel.getByTestId("bootstrap-adaptive-choose-alternative")).toHaveCount(0);
    // The ROUTE_UNVERIFIED branch must not smuggle coordinates to Google:
    // consent to Valhalla did not authorize a second external recipient.
    const keepCurrent = ownerPanel.getByTestId("bootstrap-adaptive-current-fallback");
    const chooseAlternate = ownerPanel.getByTestId("bootstrap-adaptive-alternative-fallback");
    await expect(keepCurrent).toHaveAttribute("type", "button");
    await expect(chooseAlternate).toHaveAttribute("type", "button");
    await expect(ownerPanel.getByTestId("bootstrap-two-stop-fallback")).toHaveCount(0);
    await expect(ownerPanel.getByTestId("bootstrap-two-stop-consent-checkbox")).not.toBeChecked();
    expect(provider.routeCalls).toHaveLength(4);

    // Changing a walking budget revokes the old comparison until a new
    // deliberate provider authorization; no stale 42/13 suggestion persists.
    await ownerPanel.getByTestId("bootstrap-adaptive-walk-budget").selectOption("30");
    await expect(unavailableResult).toHaveCount(0);
    await expect(ownerPanel.getByTestId("bootstrap-adaptive-walk-consent-checkbox")).not.toBeChecked();
    await ownerPanel.getByTestId("bootstrap-adaptive-walk-consent-checkbox").check();
    await ownerPanel.getByTestId("bootstrap-adaptive-walk-check").click();
    await expect(ownerPanel.getByTestId("bootstrap-adaptive-current-fallback")).toBeVisible();
    await ownerPanel.getByTestId("bootstrap-adaptive-alternative-fallback").click();
    await expect(ownerPanel.getByTestId("bootstrap-two-stop-order")).toContainText("R99 Shanghai Park");
    await expect(ownerPanel.getByTestId("bootstrap-adaptive-walk-result")).toHaveCount(0);
    await expect(ownerPanel.getByTestId("bootstrap-two-stop-consent-checkbox")).not.toBeChecked();
    expect(provider.routeCalls).toHaveLength(6);
    expect(readExploreOnlyCounts(journey.id, cityCode)).toEqual({
      place_count: 0,
      plan_count: 0,
      agent_run_count: 0,
      guardian_run_count: 0,
      booking_count: 0,
    });
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
      new Promise<void>((resolve) => provider.routeServer.close(() => resolve())),
    ]);
  }
});


