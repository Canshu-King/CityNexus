import { execFileSync } from "node:child_process";
import { createServer } from "node:http";
import { expect, test, type APIRequestContext, type Locator, type Route } from "@playwright/test";

const API = `http://127.0.0.1:${Number(process.env.CITYNEXUS_BACKEND_PORT ?? 8000)}`;
const OVERPASS_FIXTURE_PORT = 8211;

test.use({ viewport: { width: 390, height: 844 } });

async function post<T>(request: APIRequestContext, path: string, data: unknown): Promise<T> {
  const response = await request.post(`${API}${path}`, { data });
  if (!response.ok()) throw new Error(`${path} -> ${response.status()}: ${(await response.text()).slice(0, 240)}`);
  return response.json() as Promise<T>;
}

async function createOverpassFixture() {
  const calls: string[] = [];
  let releaseDelayedQuery: (() => void) | undefined;
  let delayedQuerySeen: (() => void) | undefined;
  const delayedQueryGate = new Promise<void>((resolve) => { delayedQuerySeen = resolve; });
  const delayedQueryRelease = new Promise<void>((resolve) => { releaseDelayedQuery = resolve; });
  const server = createServer((request, response) => {
    const chunks: Buffer[] = [];
    request.on("data", (chunk: Buffer) => chunks.push(chunk));
    request.on("end", async () => {
      const form = new URLSearchParams(Buffer.concat(chunks).toString("utf8"));
      const query = form.get("data") ?? "";
      calls.push(query);
      const isSecondMemberRace = query.includes("around:2500,31.231,121.474");
      if (isSecondMemberRace) {
        delayedQuerySeen?.();
        await delayedQueryRelease;
      }
      response.writeHead(200, { "content-type": "application/json" });
      response.end(JSON.stringify({
        version: 0.6,
        generator: "R94 controlled TEST_PROVIDER boundary",
        elements: [{
          type: "node",
          id: 94001,
          lat: 31.2304,
          lon: 121.4737,
          tags: { name: "R94 Shanghai Gallery", tourism: "gallery" },
        }],
      }));
    });
  });
  await new Promise<void>((resolve, reject) => {
    server.once("error", reject);
    server.listen(OVERPASS_FIXTURE_PORT, "127.0.0.1", resolve);
  });
  return {
    server,
    calls,
    delayedQueryGate,
    releaseDelayedQuery: () => releaseDelayedQuery?.(),
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

async function chooseCenterFromOsmLink(
  panel: Locator,
  url: string,
) {
  await panel.getByTestId("bootstrap-source-manual").click();
  await panel.getByTestId("bootstrap-osm-map-link").fill(url);
  await panel.getByTestId("bootstrap-osm-map-link-apply").click();
  await expect(panel.getByTestId("bootstrap-public-area-pending")).toBeVisible();
  await panel.getByTestId("bootstrap-public-area-confirm").click();
}

test("R94 tap-to-pick, real signed outing resume, and stale GPS/discovery fences", async ({ page, request }) => {
  const provider = await createOverpassFixture();
  let releaseOwnerSave: (() => void) | undefined;
  let ownerSaveReachedBackend: (() => void) | undefined;
  const ownerSaveGate = new Promise<void>((resolve) => { ownerSaveReachedBackend = resolve; });
  const ownerSaveRelease = new Promise<void>((resolve) => { releaseOwnerSave = resolve; });
  try {
    const owner = await post<{ id: string; access_token: string }>(request, "/api/v1/travelers", {
      display_name: `R94 owner ${Date.now()}`,
      locale: "en-GB",
      timezone: "Asia/Shanghai",
    });
    const collaborator = await post<{ id: string; access_token: string }>(request, "/api/v1/travelers", {
      display_name: `R94 collaborator ${Date.now()}`,
      locale: "en-GB",
      timezone: "Asia/Shanghai",
    });
    const journey = await post<{ id: string }>(request, "/api/v1/journeys", {
      traveler_id: owner.id,
      title: "R94 pick and continue",
      city_code: `CN-R94-SH-${Date.now()}`,
      timezone: "Asia/Shanghai",
      start_at: "2026-10-15T10:00:00+08:00",
      end_at: "2026-10-16T18:00:00+08:00",
      budget: { amount_minor: 10000, currency: "CNY" },
    });
    addCollaboratorToIsolatedJourney(journey.id, owner.id, collaborator.id);

    // This forwards the real signed shortlist save to the backend and delays only
    // the HTTP response so the bearer switch can race the UI continuation.
    await page.route(`**/api/v1/journeys/${journey.id}/bootstrap-shortlist`, async (route: Route) => {
      if (route.request().method() !== "POST") {
        await route.continue();
        return;
      }
      const upstream = await route.fetch();
      ownerSaveReachedBackend?.();
      await ownerSaveRelease;
      await route.fulfill({ response: upstream });
    });
    await page.route("https://tile.openstreetmap.org/**", async (route) => route.abort());
    await page.route("https://www.google.com/maps/dir/**", async (route) => {
      await route.fulfill({ status: 200, contentType: "text/html", body: "R94 destination-only walking handoff" });
    });

    const tileRequests: string[] = [];
    page.on("request", (incoming) => {
      if (incoming.url().startsWith("https://tile.openstreetmap.org/")) tileRequests.push(incoming.url());
    });
    await page.addInitScript(({ journeyId, token }) => {
      localStorage.setItem("citynexus.v8.journey_id", journeyId);
      sessionStorage.setItem("citynexus.traveler.bearer", token);
      const callbacks: Array<(position: GeolocationPosition) => void> = [];
      Object.defineProperty(navigator, "geolocation", {
        configurable: true,
        value: {
          getCurrentPosition(success: (position: GeolocationPosition) => void) {
            callbacks.push(success);
            (window as Window & { __r94GpsCallbacks?: typeof callbacks }).__r94GpsCallbacks = callbacks;
          },
        },
      });
    }, { journeyId: journey.id, token: owner.access_token });
    await page.goto("/v8/hub", { waitUntil: "domcontentloaded" });
    const panel = page.getByTestId("bootstrap-discovery");
    await expect(panel.getByTestId("bootstrap-center-required")).toContainText("No provider request will be made yet");
    await expect(panel.getByTestId("bootstrap-search")).toBeDisabled();

    // Opening the map does not fetch tiles. They begin only after their own disclosure.
    await panel.getByTestId("bootstrap-source-manual").click();
    // A blank URL parameter is not a user-selected coordinate: Number("") is 0.
    await panel.getByTestId("bootstrap-osm-map-link").fill("https://www.openstreetmap.org/?mlat=&mlon=");
    await panel.getByTestId("bootstrap-osm-map-link-apply").click();
    await expect(panel.getByTestId("bootstrap-public-area-confirm")).toBeDisabled();
    await expect(panel.getByTestId("bootstrap-osm-map-link-message")).toContainText("Paste an exact");
    await panel.getByTestId("bootstrap-osm-map-link").fill("");
    await expect(panel.getByTestId("bootstrap-map-tile-not-loaded")).toBeVisible();
    expect(tileRequests).toHaveLength(0);
    await panel.getByTestId("bootstrap-map-tile-consent").check();
    await expect(panel.getByTestId("bootstrap-public-map-canvas")).toBeVisible();
    await expect.poll(() => tileRequests.length).toBeGreaterThan(0);
    await panel.getByTestId("bootstrap-public-map-canvas").evaluate((element) => {
      const map = (element as HTMLDivElement & { citynexusMap?: { fire: (name: string, event: unknown) => void } }).citynexusMap;
      map?.fire("click", { lngLat: { lat: 31.2304, lng: 121.4737 } });
    });
    await expect(panel.getByTestId("bootstrap-public-area-pending")).toContainText("31.230400, 121.473700");
    await panel.getByTestId("bootstrap-public-area-confirm").click();
    await expect(panel.getByTestId("bootstrap-selected-center")).toContainText("31.230400, 121.473700");
    expect(provider.calls).toHaveLength(0);

    // A deliberately delayed GPS callback cannot replace the user's map selection.
    await panel.getByTestId("bootstrap-source-gps").click();
    await chooseCenterFromOsmLink(panel, "https://www.openstreetmap.org/#map=13/31.2304/121.4737");
    await page.evaluate(() => {
      const position = { coords: { latitude: 39.12, longitude: 117.2, accuracy: 4 } } as GeolocationPosition;
      (window as Window & { __r94GpsCallbacks?: Array<(value: GeolocationPosition) => void> }).__r94GpsCallbacks?.[0]?.(position);
    });
    await expect(panel.getByTestId("bootstrap-selected-center")).toContainText("31.230400, 121.473700");

    // One controlled Overpass request returns a named public POI. Journey auth,
    // discovery receipt and the complete shortlist surface remain real backend calls.
    await panel.getByTestId("bootstrap-provider-consent").check();
    expect(provider.calls).toHaveLength(0);
    await panel.getByTestId("bootstrap-search").click();
    await expect(panel.getByTestId("bootstrap-results")).toContainText("R94 Shanghai Gallery");
    expect(provider.calls).toHaveLength(1);
    expect(provider.calls[0]).toContain("around:2500,31.2304,121.4737");
    await panel.locator('[data-testid^="bootstrap-save-"]').first().click();
    await ownerSaveGate;

    // The real backend has committed A's save. B's signed member read remains empty
    // while A's unchanged backend response is still held at the browser boundary.
    await page.evaluate((token) => sessionStorage.setItem("citynexus.traveler.bearer", token), collaborator.access_token);
    await expect(panel.getByTestId("bootstrap-shortlist")).toContainText("Saved 0 of 3");
    await expect(panel).not.toContainText("R94 Shanghai Gallery");
    releaseOwnerSave?.();
    await expect(panel).not.toContainText("R94 Shanghai Gallery");

    await page.evaluate((token) => sessionStorage.setItem("citynexus.traveler.bearer", token), owner.access_token);
    await expect(panel.getByTestId("bootstrap-shortlist")).toContainText("R94 Shanghai Gallery");
    const shortlistItem = await panel.locator('[data-testid^="bootstrap-shortlist-item-"]').getAttribute("data-testid");
    expect(shortlistItem).toBeTruthy();
    const shortlistId = shortlistItem!.replace("bootstrap-shortlist-item-", "");
    await expect(panel.getByTestId(`bootstrap-shortlist-item-${shortlistId}`)).toContainText("route ETA UNKNOWN");
    await panel.getByTestId(`bootstrap-shortlist-go-${shortlistId}`).click();
    await expect(panel.getByTestId(`bootstrap-shortlist-navigation-consent-${shortlistId}`)).toContainText("destination");
    await panel.getByTestId("bootstrap-shortlist-navigation-consent-checkbox").check();
    const popupPromise = page.waitForEvent("popup");
    await panel.getByTestId("bootstrap-shortlist-navigation-confirm").click();
    const popup = await popupPromise;
    await popup.waitForURL(/google\.com\/maps\/dir/);
    expect(popup.url()).toMatch(/destination=31\.2304000?%2C121\.4737000?/);
    expect(popup.url()).toContain("travelmode=walking");
    expect(popup.url()).not.toContain("origin=");
    expect(popup.url()).not.toContain("receipt");
    await expect(panel.getByTestId("bootstrap-explore-state")).toContainText("no Place, PlanVersion");
    await popup.close();
    await page.reload({ waitUntil: "domcontentloaded" });
    await expect(page.getByTestId("bootstrap-resume")).toContainText("R94 Shanghai Gallery");

    // A second signed member request is held at the external Overpass boundary.
    // Changing the selected area before it returns must suppress the old response.
    const collaboratorPanel = page.getByTestId("bootstrap-discovery");
    await page.evaluate((token) => sessionStorage.setItem("citynexus.traveler.bearer", token), collaborator.access_token);
    await expect(collaboratorPanel.getByTestId("bootstrap-shortlist")).toContainText("Saved 0 of 3");
    await chooseCenterFromOsmLink(collaboratorPanel, "https://www.openstreetmap.org/#map=13/31.231/121.474");
    await collaboratorPanel.getByTestId("bootstrap-provider-consent").check();
    await collaboratorPanel.getByTestId("bootstrap-search").click();
    await provider.delayedQueryGate;
    await collaboratorPanel.getByTestId("bootstrap-latitude").fill("31.232");
    await collaboratorPanel.getByTestId("bootstrap-longitude").fill("121.475");
    provider.releaseDelayedQuery();
    await expect(collaboratorPanel.getByTestId("bootstrap-results")).toHaveCount(0);
    expect(provider.calls).toHaveLength(2);
  } finally {
    provider.releaseDelayedQuery();
    await new Promise<void>((resolve) => provider.server.close(() => resolve()));
  }
});
