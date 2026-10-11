import { execFileSync } from "node:child_process";
import { createServer, type IncomingMessage, type ServerResponse } from "node:http";
import { expect, test, type APIRequestContext } from "@playwright/test";

const API = `http://127.0.0.1:${Number(process.env.CITYNEXUS_BACKEND_PORT ?? 8000)}`;
const CITY_SEARCH_FIXTURE_PORT = 8261;
const OVERPASS_FIXTURE_PORT = 8262;
const VIEWPORT = { width: 390, height: 844 };
test.use({ viewport: VIEWPORT, hasTouch: true });

async function post<T>(request: APIRequestContext, path: string, data: unknown, token?: string): Promise<T> {
  const response = await request.post(`${API}${path}`, {
    data,
    headers: token ? { Authorization: `Bearer ${token}` } : undefined,
  });
  if (!response.ok()) throw new Error(`${path} -> ${response.status()}: ${(await response.text()).slice(0, 300)}`);
  return response.json() as Promise<T>;
}

function createProviderFixtures() {
  const cityCalls: string[] = [];
  const overpassCalls: string[] = [];
  const cityServer = createServer((_request, response) => {
    cityCalls.push("Shanghai");
    response.writeHead(200, { "content-type": "application/json" });
    response.end(JSON.stringify([{
      place_id: 103001,
      osm_type: "relation",
      osm_id: 103001,
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
        generator: "R103 controlled TEST_PROVIDER one-shot city discovery",
        elements: [
          { type: "node", id: 103001, lat: 31.2304, lon: 121.4737, tags: { name: "R103 Shanghai Museum", tourism: "museum" } },
          { type: "node", id: 103002, lat: 31.231, lon: 121.474, tags: { name: "R103 Shanghai Gallery", tourism: "gallery" } },
          { type: "node", id: 103003, lat: 31.2315, lon: 121.4745, tags: { name: "R103 Shanghai Park", leisure: "park" } },
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

test("R103 ordinary travelers discover, share, verify, and save two public city places", async ({ browser, request }) => {
  const provider = createProviderFixtures();
  await provider.ready;
  try {
    const sender = await post<{ id: string; access_token: string }>(request, "/api/v1/travelers", {
      display_name: `R103 sender ${Date.now()}`,
      locale: "en-GB",
      timezone: "Asia/Shanghai",
    });
    const recipient = await post<{ id: string; access_token: string }>(request, "/api/v1/travelers", {
      display_name: `R103 recipient ${Date.now()}`,
      locale: "en-GB",
      timezone: "Asia/Shanghai",
    });
    const senderJourney = await post<{ id: string }>(request, "/api/v1/journeys", {
      traveler_id: sender.id,
      title: "Shanghai shared discovery sender",
      city_code: "Shanghai",
      timezone: "Asia/Shanghai",
      start_at: "2026-10-20T10:00:00+08:00",
      end_at: "2026-10-21T18:00:00+08:00",
      budget: { amount_minor: 10000, currency: "CNY" },
    });
    const recipientJourney = await post<{ id: string }>(request, "/api/v1/journeys", {
      traveler_id: recipient.id,
      title: "Shanghai shared discovery recipient",
      city_code: "Shanghai",
      timezone: "Asia/Shanghai",
      start_at: "2026-10-20T10:00:00+08:00",
      end_at: "2026-10-21T18:00:00+08:00",
      budget: { amount_minor: 10000, currency: "CNY" },
    });

    const senderPage = await browser.newPage({ viewport: VIEWPORT });
    await senderPage.addInitScript(({ journeyId, token }) => {
      localStorage.setItem("citynexus.v8.journey_id", journeyId);
      sessionStorage.setItem("citynexus.traveler.bearer", token);
      Object.defineProperty(navigator, "share", {
        configurable: true,
        value: async (payload: { title?: string; text?: string }) => {
          const target = window as Window & { __r103SharePayloads?: Array<{ title?: string; text?: string }> };
          target.__r103SharePayloads = [...(target.__r103SharePayloads ?? []), payload];
        },
      });
    }, { journeyId: senderJourney.id, token: sender.access_token });
    await senderPage.goto("/v8/hub", { waitUntil: "domcontentloaded" });
    const senderPanel = senderPage.getByTestId("bootstrap-discovery");
    await senderPanel.getByTestId("bootstrap-source-manual").click();
    await senderPanel.getByTestId("bootstrap-city-search-query").fill("Shanghai");
    expect(provider.cityCalls).toHaveLength(0);
    await senderPanel.getByTestId("bootstrap-city-search-consent").check();
    await senderPanel.getByTestId("bootstrap-city-search-submit").click();
    await expect(senderPanel.getByTestId("bootstrap-city-search-results")).toContainText("Shanghai, China");
    expect(provider.cityCalls).toHaveLength(1);
    await senderPanel.getByTestId("bootstrap-city-result-0").click();
    await senderPanel.getByTestId("bootstrap-map-tile-consent").check();
    await expect(senderPanel.getByTestId("bootstrap-public-map-canvas")).toBeVisible();
    await expect.poll(() => senderPanel.getByTestId("bootstrap-public-map-canvas").evaluate((element) =>
      Boolean((element as HTMLDivElement & { citynexusMap?: unknown }).citynexusMap),
    )).toBeTruthy();
    await senderPanel.getByTestId("bootstrap-public-map-canvas").evaluate((element) => {
      const map = (element as HTMLDivElement & { citynexusMap?: { fire: (name: string, event: unknown) => void } }).citynexusMap;
      map?.fire("click", { point: { x: 100, y: 100 }, lngLat: { lat: 31.2304, lng: 121.4737 } });
    });
    await senderPanel.getByTestId("bootstrap-public-area-confirm").click();
    await expect(senderPanel.getByTestId("bootstrap-selected-center")).toContainText("31.230400, 121.473700");
    await senderPanel.getByTestId("bootstrap-intent-ART_HISTORY").click();
    await senderPanel.getByTestId("bootstrap-provider-consent").check();
    await senderPanel.getByTestId("bootstrap-search").click();
    const senderResults = senderPanel.getByTestId("bootstrap-results");
    await expect(senderResults).toContainText("R103 Shanghai Museum");
    await expect(senderResults).toContainText("TEST_PROVIDER");
    expect(provider.overpassCalls).toHaveLength(1);

    const senderCandidates = await senderResults.locator('[data-testid^="bootstrap-candidate-"]').evaluateAll((elements) =>
      elements.map((element) => ({
        id: (element.getAttribute("data-testid") ?? "").replace("bootstrap-candidate-", ""),
        text: element.textContent ?? "",
      })),
    );
    const museumId = senderCandidates.find((candidate) => candidate.text.includes("R103 Shanghai Museum"))?.id;
    const galleryId = senderCandidates.find((candidate) => candidate.text.includes("R103 Shanghai Gallery"))?.id;
    expect(museumId && galleryId).toBeTruthy();
    await senderPanel.getByTestId(`bootstrap-share-first-${museumId!}`).click();
    await senderPanel.getByTestId(`bootstrap-share-second-${galleryId!}`).click();
    const senderSharePreview = senderPanel.getByTestId("bootstrap-discovery-share-preview");
    await expect(senderSharePreview).toContainText("R103 Shanghai Museum");
    await expect(senderSharePreview).toContainText("https://www.openstreetmap.org/node/103001");
    await senderPanel.getByTestId("bootstrap-discovery-share-consent").check();
    await senderPanel.getByRole("button", { name: "Share these two public places" }).click();
    await expect(senderPanel.getByTestId("bootstrap-discovery-share-message")).toContainText("Public-only two-place share sent");
    const shared = await senderPage.evaluate(() => (window as Window & { __r103SharePayloads?: Array<{ text?: string }> }).__r103SharePayloads ?? []);
    expect(shared).toHaveLength(1);
    const shareText = shared[0].text ?? "";
    expect(shareText).toContain("sample/unverified location");
    expect(shareText).toContain("R103 Shanghai Museum");
    expect(shareText).toContain("R103 Shanghai Gallery");
    for (const privateValue of [senderJourney.id, sender.id, sender.access_token]) expect(shareText).not.toContain(privateValue);
    expect(readExploreOnlyCounts(senderJourney.id, "Shanghai")).toEqual({ place_count: 0, plan_count: 0, agent_run_count: 0, guardian_run_count: 0, booking_count: 0 });
    await senderPage.close();

    const recipientPage = await browser.newPage({ viewport: VIEWPORT });
    await recipientPage.route("https://www.google.com/maps/dir/**", async (route) => {
      await route.fulfill({ status: 200, contentType: "text/html", body: "R103 controlled public map handoff" });
    });
    await recipientPage.addInitScript(({ journeyId, token }) => {
      localStorage.setItem("citynexus.v8.journey_id", journeyId);
      sessionStorage.setItem("citynexus.traveler.bearer", token);
    }, { journeyId: recipientJourney.id, token: recipient.access_token });
    await recipientPage.goto("/v8/hub", { waitUntil: "domcontentloaded" });
    const recipientPanel = recipientPage.getByTestId("bootstrap-discovery");
    const importPanel = recipientPanel.getByTestId("bootstrap-shared-walk-import");
    await importPanel.getByTestId("bootstrap-shared-walk-textarea").fill(shareText);
    await importPanel.getByTestId("bootstrap-shared-walk-preview-button").click();
    await expect(importPanel.getByTestId("bootstrap-shared-walk-preview")).toContainText("UNVERIFIED_SHARED_REFERENCE");
    expect(provider.overpassCalls).toHaveLength(1);
    await importPanel.getByTestId("bootstrap-shared-walk-lookup-consent").check();
    await importPanel.getByTestId("bootstrap-shared-walk-lookup").click();
    await expect(importPanel.getByTestId("bootstrap-shared-walk-results")).toContainText("R103 Shanghai Museum");
    expect(provider.overpassCalls).toHaveLength(2);
    const exactQuery = provider.overpassCalls.at(-1) ?? "";
    expect(exactQuery).toMatch(/^\[out:json\]\[timeout:10\];\((?:node\(103001\);node\(103002\);|node\(103002\);node\(103001\);)\);out center tags;$/);
    expect(exactQuery).not.toMatch(/journey|member|receipt|bearer|gps/i);

    const recipientCandidates = await importPanel.locator('[data-testid^="bootstrap-shared-walk-candidate-"]').evaluateAll((elements) =>
      elements.map((element) => ({
        id: (element.getAttribute("data-testid") ?? "").replace("bootstrap-shared-walk-candidate-", ""),
        text: element.textContent ?? "",
      })),
    );
    const recipientMuseumId = recipientCandidates.find((candidate) => candidate.text.includes("R103 Shanghai Museum"))?.id;
    const recipientGalleryId = recipientCandidates.find((candidate) => candidate.text.includes("R103 Shanghai Gallery"))?.id;
    expect(recipientMuseumId && recipientGalleryId).toBeTruthy();
    await importPanel.getByTestId(`bootstrap-shared-walk-first-${recipientMuseumId!}`).click();
    await importPanel.getByTestId(`bootstrap-shared-walk-second-${recipientGalleryId!}`).click();
    await importPanel.getByTestId("bootstrap-shared-walk-pocket-budget").selectOption("20");
    await importPanel.getByTestId("bootstrap-shared-walk-save-consent").check();
    await importPanel.getByTestId("bootstrap-shared-walk-save-pocket").click();
    await expect(recipientPanel.getByTestId("bootstrap-pocket-walk-card")).toBeVisible();
    await expect(recipientPanel.getByTestId("bootstrap-pocket-walk-stops")).toContainText("R103 Shanghai Museum");
    await expect(recipientPanel.getByTestId("bootstrap-pocket-walk-stops")).toContainText("R103 Shanghai Gallery");
    await expect(recipientPanel.getByTestId("bootstrap-shortlist")).toContainText("Saved 2 of 3");
    expect(readExploreOnlyCounts(recipientJourney.id, "Shanghai")).toEqual({ place_count: 0, plan_count: 0, agent_run_count: 0, guardian_run_count: 0, booking_count: 0 });

    await recipientPage.reload({ waitUntil: "domcontentloaded" });
    const reloadedRecipient = recipientPage.getByTestId("bootstrap-discovery");
    await expect(reloadedRecipient.getByTestId("bootstrap-pocket-walk-card")).toBeVisible();
    await expect(reloadedRecipient.getByTestId("bootstrap-pocket-walk-stops")).toContainText("R103 Shanghai Museum");
    await expect(reloadedRecipient.getByTestId("bootstrap-pocket-walk-stops")).toContainText("R103 Shanghai Gallery");
    await expect(reloadedRecipient.getByTestId("bootstrap-pocket-walk-budget")).toHaveValue("20");

    const shortlistItems = await reloadedRecipient.locator('[data-testid^="bootstrap-shortlist-item-"]').evaluateAll((elements) =>
      elements.map((element) => ({
        id: (element.getAttribute("data-testid") ?? "").replace("bootstrap-shortlist-item-", ""),
        text: element.textContent ?? "",
      })),
    );
    const savedMuseumId = shortlistItems.find((item) => item.text.includes("R103 Shanghai Museum"))?.id;
    expect(savedMuseumId).toBeTruthy();
    await reloadedRecipient.getByTestId("bootstrap-pocket-navigate-first").click();
    await reloadedRecipient.getByTestId("bootstrap-shortlist-navigation-consent-checkbox").check();
    const stopPopupPromise = recipientPage.waitForEvent("popup");
    await reloadedRecipient.getByTestId("bootstrap-shortlist-navigation-confirm").click();
    const stopPopup = await stopPopupPromise;
    await stopPopup.waitForURL(/google\.com\/maps\/dir/);
    expect(stopPopup.url()).not.toContain("origin=");
    await stopPopup.close();

    await reloadedRecipient.getByTestId("bootstrap-pocket-open-walk").click();
    await reloadedRecipient.getByTestId("bootstrap-two-stop-consent-checkbox").check();
    const walkPopupPromise = recipientPage.waitForEvent("popup");
    await reloadedRecipient.getByTestId("bootstrap-two-stop-confirm").click();
    const walkPopup = await walkPopupPromise;
    await walkPopup.waitForURL(/google\.com\/maps\/dir/);
    expect(new URL(walkPopup.url()).searchParams.get("travelmode")).toBe("walking");
    expect(new URL(walkPopup.url()).searchParams.get("origin")).toBe("31.2304000,121.4737000");
    await walkPopup.close();

    await importPanel.getByTestId("bootstrap-shared-walk-textarea").fill(
      "https://www.openstreetmap.org/node/103001?access_token=secret\nhttps://www.openstreetmap.org/node/103002",
    );
    await importPanel.getByTestId("bootstrap-shared-walk-preview-button").click();
    await expect(importPanel.getByTestId("bootstrap-shared-walk-error")).toBeVisible();
    expect(provider.overpassCalls).toHaveLength(2);
    expect(savedMuseumId).toBeTruthy();
  } finally {
    await Promise.all([
      new Promise<void>((resolve) => provider.cityServer.close(() => resolve())),
      new Promise<void>((resolve) => provider.overpassServer.close(() => resolve())),
    ]);
  }
});
