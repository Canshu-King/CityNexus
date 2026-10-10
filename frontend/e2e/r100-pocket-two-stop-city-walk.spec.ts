import { execFileSync } from "node:child_process";
import { createServer } from "node:http";
import { expect, test, type APIRequestContext, type Locator } from "@playwright/test";

const API = `http://127.0.0.1:${Number(process.env.CITYNEXUS_BACKEND_PORT ?? 8000)}`;
const CITY_SEARCH_FIXTURE_PORT = 8257;
const OVERPASS_FIXTURE_PORT = 8258;

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
      place_id: 100001,
      osm_type: "relation",
      osm_id: 100001,
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
        generator: "R100 controlled TEST_PROVIDER boundary",
        elements: [
          { type: "node", id: 100011, lat: 31.2304, lon: 121.4737, tags: { name: "R100 Shanghai Museum", tourism: "museum" } },
          { type: "node", id: 100012, lat: 31.231, lon: 121.474, tags: { name: "R100 Shanghai Gallery", tourism: "gallery" } },
          { type: "node", id: 100013, lat: 31.2315, lon: 121.4745, tags: { name: "R100 Shanghai Park", leisure: "park" } },
        ],
      }));
    });
  });
  await Promise.all([
    new Promise<void>((resolve, reject) => { cityServer.once("error", reject); cityServer.listen(CITY_SEARCH_FIXTURE_PORT, "127.0.0.1", resolve); }),
    new Promise<void>((resolve, reject) => { overpassServer.once("error", reject); overpassServer.listen(OVERPASS_FIXTURE_PORT, "127.0.0.1", resolve); }),
  ]);
  return { cityServer, overpassServer, cityCalls, overpassCalls };
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

test("R100 Pocket Walk persists two public stops, authorizes each map separately, and shares only public evidence", async ({ page, request }) => {
  const provider = await createProviderFixtures();
  try {
    const owner = await post<{ id: string; access_token: string }>(request, "/api/v1/travelers", {
      display_name: `R100 owner ${Date.now()}`,
      locale: "en-GB",
      timezone: "Asia/Shanghai",
    });
    const collaborator = await post<{ id: string; access_token: string }>(request, "/api/v1/travelers", {
      display_name: `R100 collaborator ${Date.now()}`,
      locale: "en-GB",
      timezone: "Asia/Shanghai",
    });
    const cityCode = `CN-R100-SH-${Date.now()}`;
    const journey = await post<{ id: string }>(request, "/api/v1/journeys", {
      traveler_id: owner.id,
      title: "R100 Pocket Walk draft",
      city_code: cityCode,
      timezone: "Asia/Shanghai",
      start_at: "2026-10-18T10:00:00+08:00",
      end_at: "2026-10-19T18:00:00+08:00",
      budget: { amount_minor: 10000, currency: "CNY" },
    });
    addCollaboratorToIsolatedJourney(journey.id, owner.id, collaborator.id);

    await page.context().route("https://www.google.com/maps/dir/**", async (route) => {
      await route.fulfill({ status: 200, contentType: "text/html", body: "R100 destination-only public map handoff" });
    });
    await page.addInitScript(({ journeyId, token }) => {
      localStorage.setItem("citynexus.v8.journey_id", journeyId);
      sessionStorage.setItem("citynexus.traveler.bearer", token);
      Object.defineProperty(navigator, "share", {
        configurable: true,
        value: async (payload: { title?: string; text?: string }) => {
          const target = window as Window & { __r100SharePayloads?: Array<{ title?: string; text?: string }> };
          target.__r100SharePayloads = [...(target.__r100SharePayloads ?? []), payload];
        },
      });
    }, { journeyId: journey.id, token: owner.access_token });
    await page.goto("/v8/hub", { waitUntil: "domcontentloaded" });
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
    await panel.getByTestId("bootstrap-city-result-0").click();
    await panel.getByTestId("bootstrap-map-tile-consent").check();
    await expect(panel.getByTestId("bootstrap-public-map-canvas")).toBeVisible();
    await expect.poll(() => panel.getByTestId("bootstrap-public-map-canvas").evaluate((element) =>
      Boolean((element as HTMLDivElement & { citynexusMap?: unknown }).citynexusMap),
    )).toBeTruthy();
    await panel.getByTestId("bootstrap-public-map-canvas").evaluate((element) => {
      const map = (element as HTMLDivElement & { citynexusMap?: { fire: (name: string, event: unknown) => void } }).citynexusMap;
      map?.fire("click", { point: { x: 100, y: 100 }, lngLat: { lat: 31.2304, lng: 121.4737 } });
    });
    await expect(panel.getByTestId("bootstrap-public-area-pending")).toContainText("31.230400, 121.473700");
    await panel.getByTestId("bootstrap-public-area-confirm").click();
    await expect(panel.getByTestId("bootstrap-selected-center")).toContainText("31.230400, 121.473700");

    await panel.getByTestId("bootstrap-intent-ART_HISTORY").click();
    await panel.getByTestId("bootstrap-provider-consent").check();
    await panel.getByTestId("bootstrap-search").click();
    const result = panel.getByTestId("bootstrap-results");
    await expect(result).toContainText("R100 Shanghai Museum");
    await expect(result).toContainText("TEST_PROVIDER");
    expect(provider.overpassCalls).toHaveLength(1);
    for (const candidate of [0, 1, 2]) {
      await result.locator('[data-testid^="bootstrap-save-"]').nth(candidate).click();
    }
    await expect(panel.getByTestId("bootstrap-shortlist")).toContainText("Saved 3 of 3");
    await expect(panel.getByTestId("bootstrap-shortlist")).toContainText("R100 Shanghai Park");
    expect(readExploreOnlyCounts(journey.id, cityCode)).toEqual({ place_count: 0, plan_count: 0, agent_run_count: 0, guardian_run_count: 0, booking_count: 0 });

    const shortlistItems = panel.locator('[data-testid^="bootstrap-shortlist-item-"]');
    const records = await shortlistItems.evaluateAll((elements) => elements.map((element) => ({
      id: (element.getAttribute("data-testid") ?? "").replace("bootstrap-shortlist-item-", ""),
      text: element.textContent ?? "",
    })));
    const museumId = records.find((item) => item.text.includes("R100 Shanghai Museum"))?.id;
    const galleryId = records.find((item) => item.text.includes("R100 Shanghai Gallery"))?.id;
    const parkId = records.find((item) => item.text.includes("R100 Shanghai Park"))?.id;
    expect(museumId && galleryId && parkId).toBeTruthy();
    await panel.getByTestId(`bootstrap-two-stop-first-${museumId!}`).click();
    await panel.getByTestId(`bootstrap-two-stop-second-${galleryId!}`).click();
    await panel.getByTestId("bootstrap-pocket-walk-budget").selectOption("20");
    await panel.getByTestId("bootstrap-pocket-walk-save").click();
    const pocketCard = panel.getByTestId("bootstrap-pocket-walk-card");
    await expect(pocketCard).toBeVisible();
    await expect(pocketCard.getByTestId("bootstrap-pocket-walk-stops")).toContainText("1. R100 Shanghai Museum");
    await expect(pocketCard.getByTestId("bootstrap-pocket-walk-stops")).toContainText("2. R100 Shanghai Gallery");
    await expect(panel.getByTestId("bootstrap-pocket-share-preview")).toContainText("TEST_PROVIDER");
    const initialPreview = await panel.getByTestId("bootstrap-pocket-share-preview").innerText();
    expect(initialPreview).toContain("sample/unverified location");
    for (const privateValue of [journey.id, owner.id, owner.access_token]) expect(initialPreview).not.toContain(privateValue);

    // Stop 1 navigation is a destination-only release with its own consent.
    await pocketCard.getByTestId("bootstrap-pocket-navigate-first").click();
    await expect(panel.getByTestId(`bootstrap-shortlist-navigation-consent-${museumId!}`)).toBeVisible();
    await panel.getByTestId("bootstrap-shortlist-navigation-consent-checkbox").check();
    const stopOnePopupPromise = page.waitForEvent("popup");
    await panel.getByTestId("bootstrap-shortlist-navigation-confirm").click();
    const stopOnePopup = await stopOnePopupPromise;
    await stopOnePopup.waitForURL(/google\.com\/maps\/dir/);
    expect(stopOnePopup.url()).toContain("destination=31.2304000%2C121.4737000");
    expect(stopOnePopup.url()).not.toContain("origin=");
    expect(stopOnePopup.url()).not.toContain("receipt");
    await stopOnePopup.close();

    // The public-to-public walk has a distinct consent boundary.
    await pocketCard.getByTestId("bootstrap-pocket-open-walk").click();
    await expect(panel.getByTestId("bootstrap-two-stop-consent")).toBeVisible();
    await panel.getByTestId("bootstrap-two-stop-consent-checkbox").check();
    const walkPopupPromise = page.waitForEvent("popup");
    await panel.getByTestId("bootstrap-two-stop-confirm").click();
    const walkPopup = await walkPopupPromise;
    await walkPopup.waitForURL(/google\.com\/maps\/dir/);
    const walkUrl = new URL(walkPopup.url());
    expect(walkUrl.searchParams.get("travelmode")).toBe("walking");
    expect(walkUrl.searchParams.get("origin")).toBe("31.2304000,121.4737000");
    expect(walkUrl.searchParams.get("destination")).toBe("31.2310000,121.4740000");
    expect(walkPopup.url()).not.toContain("receipt");
    await walkPopup.close();

    // A refresh restores the private ordered pair from the backend.
    await page.reload({ waitUntil: "domcontentloaded" });
    await page.evaluate((token) => {
      sessionStorage.setItem("citynexus.traveler.bearer", token);
      window.dispatchEvent(new CustomEvent("citynexus.traveler.bearer.changed"));
    }, owner.access_token);
    const reloadedPanel = page.getByTestId("bootstrap-discovery");
    await expect(reloadedPanel.getByTestId("bootstrap-pocket-walk-card")).toBeVisible();
    await expect(reloadedPanel.getByTestId("bootstrap-pocket-walk-stops")).toContainText("1. R100 Shanghai Museum");
    await expect(reloadedPanel.getByTestId("bootstrap-pocket-walk-stops")).toContainText("2. R100 Shanghai Gallery");
    await expect(reloadedPanel.getByTestId("bootstrap-pocket-walk-budget")).toHaveValue("20");

    // Explicit public-only share uses the reviewed preview and never includes
    // signed-member or Journey identifiers.
    await reloadedPanel.getByTestId("bootstrap-pocket-share-consent-checkbox").check();
    await reloadedPanel.getByTestId("bootstrap-pocket-share").click();
    await expect(reloadedPanel.getByTestId("bootstrap-pocket-walk-message")).toContainText("Public-only Pocket Walk shared");
    const shared = await page.evaluate(() => (window as Window & { __r100SharePayloads?: Array<{ text?: string }> }).__r100SharePayloads ?? []);
    expect(shared).toHaveLength(1);
    expect(shared[0].text).toContain("R100 Shanghai Museum");
    expect(shared[0].text).toContain("https://www.openstreetmap.org/node/");
    for (const privateValue of [journey.id, owner.id, owner.access_token]) expect(shared[0].text).not.toContain(privateValue);

    const collaboratorPage = await page.context().newPage();
    await collaboratorPage.addInitScript(({ journeyId, token }) => {
      localStorage.setItem("citynexus.v8.journey_id", journeyId);
      sessionStorage.setItem("citynexus.traveler.bearer", token);
    }, { journeyId: journey.id, token: collaborator.access_token });
    await collaboratorPage.goto("/v8/hub", { waitUntil: "domcontentloaded" });
    await collaboratorPage.evaluate((token) => {
      sessionStorage.setItem("citynexus.traveler.bearer", token);
      window.dispatchEvent(new CustomEvent("citynexus.traveler.bearer.changed"));
    }, collaborator.access_token);
    const collaboratorPanel = collaboratorPage.getByTestId("bootstrap-discovery");
    await expect(collaboratorPanel.getByTestId("bootstrap-pocket-walk-empty")).toBeVisible();
    await expect(collaboratorPanel).not.toContainText(/R100 Shanghai (Museum|Gallery|Park)/);
    await collaboratorPage.close();

    // Race regression: the backend completes an authorized A save, but the
    // browser response is deliberately delayed until this SAME tab switches
    // to B. The old A card must never repopulate B's private React state.
    let releaseOwnerResponse: (() => void) | null = null;
    const heldOwnerResponse = new Promise<void>((resolve) => {
      releaseOwnerResponse = resolve;
    });
    let ownerSaveCaptured = 0;
    await page.route(`**/api/v1/journeys/${journey.id}/bootstrap-shortlist/pocket-walk`, async (route) => {
      if (route.request().method() !== "POST") {
        await route.continue();
        return;
      }
      const realBackendResponse = await route.fetch();
      ownerSaveCaptured += 1;
      await heldOwnerResponse;
      await route.fulfill({ response: realBackendResponse });
    });
    await reloadedPanel.getByTestId("bootstrap-pocket-walk-save").click();
    await expect.poll(() => ownerSaveCaptured).toBe(1);
    await page.evaluate((token) => {
      sessionStorage.setItem("citynexus.traveler.bearer", token);
      window.dispatchEvent(new CustomEvent("citynexus.traveler.bearer.changed"));
    }, collaborator.access_token);
    await expect(reloadedPanel.getByTestId("bootstrap-pocket-walk-empty")).toBeVisible();
    await expect(reloadedPanel.getByTestId("bootstrap-shortlist")).toContainText("Saved 0 of 3");
    releaseOwnerResponse?.();
    await expect(reloadedPanel.getByTestId("bootstrap-pocket-walk-card")).toHaveCount(0);
    await expect(reloadedPanel).not.toContainText(/R100 Shanghai (Museum|Gallery|Park)/);
    await page.unroute(`**/api/v1/journeys/${journey.id}/bootstrap-shortlist/pocket-walk`);

    // Restore A by a fresh signed read, not by accepting A's late POST.
    await page.evaluate((token) => {
      sessionStorage.setItem("citynexus.traveler.bearer", token);
      window.dispatchEvent(new CustomEvent("citynexus.traveler.bearer.changed"));
    }, owner.access_token);
    await expect(reloadedPanel.getByTestId("bootstrap-pocket-walk-stops")).toContainText("R100 Shanghai Museum");
    await expect(reloadedPanel.getByTestId("bootstrap-pocket-walk-stops")).toContainText("R100 Shanghai Gallery");

    // Deleting either saved stop invalidates and deletes the private pair.
    await reloadedPanel.getByTestId(`bootstrap-shortlist-remove-${museumId!}`).click();
    await expect(reloadedPanel.getByTestId("bootstrap-pocket-walk-empty")).toBeVisible();
    const cleared = await request.get(`${API}/api/v1/journeys/${journey.id}/bootstrap-shortlist`, {
      headers: { Authorization: `Bearer ${owner.access_token}` },
    });
    expect(cleared.ok()).toBeTruthy();
    expect((await cleared.json()).pocket_walk).toBeNull();
    expect(readExploreOnlyCounts(journey.id, cityCode)).toEqual({ place_count: 0, plan_count: 0, agent_run_count: 0, guardian_run_count: 0, booking_count: 0 });
  } finally {
    await Promise.all([
      new Promise<void>((resolve) => provider.cityServer.close(() => resolve())),
      new Promise<void>((resolve) => provider.overpassServer.close(() => resolve())),
    ]);
  }
});
