import { createServer, type IncomingMessage, type ServerResponse } from "node:http";
import { execFileSync } from "node:child_process";
import { expect, test, type APIRequestContext, type Locator } from "@playwright/test";

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
      place_id: 105001,
      osm_type: "relation",
      osm_id: 105001,
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
      const query = new URLSearchParams(Buffer.concat(chunks).toString("utf8")).get("data") ?? "";
      overpassCalls.push(query);
      const empty = query.includes('"amenity"="library"');
      response.writeHead(200, { "content-type": "application/json" });
      response.end(JSON.stringify({
        version: 0.6,
        generator: "R105 controlled TEST_PROVIDER readiness boundary",
        elements: empty ? [] : [
          { type: "node", id: 105001, lat: 31.2304, lon: 121.4737, tags: { name: "R105 Shanghai Museum", tourism: "museum" } },
          { type: "node", id: 105002, lat: 31.231, lon: 121.474, tags: { name: "R105 Shanghai Gallery", tourism: "gallery" } },
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

function readDiscoveryAuditRequests(journeyId: string): Array<Record<string, unknown>> {
  const python = process.env.CITYNEXUS_PYTHON;
  if (!python) throw new Error("CITYNEXUS_PYTHON is required for the privacy audit assertion");
  const script = [
    "import json",
    "import sys",
    "from sqlalchemy import select",
    "from app.db.models import ProviderCall",
    "from app.db.session import SessionLocal",
    "journey_id = sys.argv[1]",
    "with SessionLocal() as session:",
    "    rows = session.scalars(select(ProviderCall).where(ProviderCall.operation == 'bootstrap_city_discovery')).all()",
    "    print(json.dumps([json.loads(row.request_json) for row in rows if journey_id in row.request_json]))",
  ].join("\n");
  const directEnv = { ...process.env };
  delete directEnv.CITYNEXUS_E2E_RUN_ID;
  return JSON.parse(execFileSync(python, ["-c", script, journeyId], {
    cwd: "../backend",
    env: directEnv,
    encoding: "utf8",
    stdio: "pipe",
    timeout: 15_000,
  }));
}

async function chooseMapLink(panel: Locator) {
  await panel.getByTestId("bootstrap-source-manual").click();
  await panel.getByTestId("bootstrap-osm-map-link").fill("https://www.openstreetmap.org/#map=13/31.2304/121.4737");
  await panel.getByTestId("bootstrap-osm-map-link-apply").click();
  await panel.getByTestId("bootstrap-public-area-confirm").click();
  await expect(panel.getByTestId("bootstrap-selected-center")).toContainText("31.230400, 121.473700");
}

test("R105 signed A/B readiness gates public city discovery and preserves truthful fallback states", async ({ browser, request }) => {
  const provider = createProviderFixtures();
  await provider.ready;
  try {
    const sender = await post<{ id: string; access_token: string }>(request, "/api/v1/travelers", {
      display_name: `R105 sender ${Date.now()}`,
      locale: "en-GB",
      timezone: "Asia/Shanghai",
    });
    const recipient = await post<{ id: string; access_token: string }>(request, "/api/v1/travelers", {
      display_name: `R105 recipient ${Date.now()}`,
      locale: "en-GB",
      timezone: "Asia/Shanghai",
    });
    const journeyPayload = {
      city_code: "Shanghai",
      timezone: "Asia/Shanghai",
      start_at: "2026-10-20T10:00:00+08:00",
      end_at: "2026-10-21T18:00:00+08:00",
      budget: { amount_minor: 10000, currency: "CNY" },
    };
    const senderJourney = await post<{ id: string }>(request, "/api/v1/journeys", {
      ...journeyPayload, traveler_id: sender.id, title: "R105 readiness sender",
    });
    const recipientJourney = await post<{ id: string }>(request, "/api/v1/journeys", {
      ...journeyPayload, traveler_id: recipient.id, title: "R105 readiness recipient",
    });

    const senderPage = await browser.newPage({ viewport: VIEWPORT });
    await senderPage.addInitScript(({ journeyId, token }) => {
      localStorage.setItem("citynexus.v8.journey_id", journeyId);
      sessionStorage.setItem("citynexus.traveler.bearer", token);
    }, { journeyId: senderJourney.id, token: sender.access_token });
    await senderPage.goto("/v8/hub", { waitUntil: "domcontentloaded" });
    const senderPanel = senderPage.getByTestId("bootstrap-discovery");
    const readiness = senderPanel.getByTestId("bootstrap-discovery-readiness");
    await expect(readiness).toContainText("TEST_PROVIDER");
    expect(provider.overpassCalls).toHaveLength(0);
    await senderPanel.getByTestId("bootstrap-source-manual").click();
    await senderPanel.getByTestId("bootstrap-city-search-query").fill("Shanghai");
    expect(provider.overpassCalls).toHaveLength(0);
    await senderPanel.getByTestId("bootstrap-city-search-consent").check();
    await senderPanel.getByTestId("bootstrap-city-search-submit").click();
    await expect(senderPanel.getByTestId("bootstrap-city-search-results")).toContainText("Shanghai, China");
    expect(provider.cityCalls).toHaveLength(1);
    await senderPanel.getByTestId("bootstrap-city-result-0").click();
    await chooseMapLink(senderPanel);
    await senderPanel.getByTestId("bootstrap-city-label-confirm").check();
    await expect(readiness.getByTestId("bootstrap-discovery-readiness-reason")).toContainText("USER_CATEGORY_REQUIRED");
    await senderPanel.getByTestId("bootstrap-intent-ART_HISTORY").click();
    await expect(readiness.getByTestId("bootstrap-discovery-readiness-reason")).toContainText("CONSENT_REQUIRED");
    await senderPanel.getByTestId("bootstrap-latitude").fill("invalid");
    await expect(senderPanel.getByTestId("bootstrap-search")).toBeDisabled();
    expect(provider.overpassCalls).toHaveLength(0);
    await senderPanel.getByTestId("bootstrap-latitude").fill("31.2304");
    const cityLabel = senderPanel.getByTestId("bootstrap-city-label-confirm");
    // Editing an already selected public center revokes the previous city
    // confirmation and provider release consent, even after a valid repair.
    await expect(cityLabel).not.toBeChecked();
    await expect(senderPanel.getByTestId("bootstrap-provider-consent")).not.toBeChecked();
    await cityLabel.check();
    await expect(cityLabel).toBeChecked();
    await cityLabel.uncheck();
    await expect(readiness.getByTestId("bootstrap-discovery-readiness-reason")).toContainText("USER_PUBLIC_AREA_REQUIRED");
    await cityLabel.check();
    await senderPanel.getByTestId("bootstrap-provider-consent").check();
    await expect(readiness.getByTestId("bootstrap-discovery-readiness-reason")).toContainText("READY");
    await senderPanel.getByTestId("bootstrap-search").click();
    await expect(senderPanel.getByTestId("bootstrap-provider-consent")).not.toBeChecked();
    await expect(senderPanel.getByTestId("bootstrap-discovery-outcome")).toContainText("FOUND_2+");
    await expect(senderPanel.getByTestId("bootstrap-results")).toContainText("R105 Shanghai Museum");
    expect(provider.overpassCalls).toHaveLength(1);
    const senderAudit = readDiscoveryAuditRequests(senderJourney.id);
    expect(senderAudit).toHaveLength(1);
    expect(senderAudit[0]).not.toHaveProperty("center");
    expect(senderAudit[0]).not.toHaveProperty("accuracy_m");
    expect(senderAudit[0]).not.toHaveProperty("member_id");
    expect(senderAudit[0]).not.toHaveProperty("traveler_id");
    await senderPage.close();

    const recipientPage = await browser.newPage({ viewport: VIEWPORT });
    await recipientPage.addInitScript(({ journeyId, token }) => {
      localStorage.setItem("citynexus.v8.journey_id", journeyId);
      sessionStorage.setItem("citynexus.traveler.bearer", token);
    }, { journeyId: recipientJourney.id, token: recipient.access_token });
    await recipientPage.goto("/v8/hub", { waitUntil: "domcontentloaded" });
    const recipientPanel = recipientPage.getByTestId("bootstrap-discovery");
    await expect(recipientPanel.getByTestId("bootstrap-discovery-readiness")).toContainText("TEST_PROVIDER");
    expect(provider.overpassCalls).toHaveLength(1);
    await chooseMapLink(recipientPanel);
    await recipientPanel.getByTestId("bootstrap-city-label-confirm").check();
    await recipientPanel.getByTestId("bootstrap-intent-QUIET_BOOKS").click();
    await recipientPanel.getByTestId("bootstrap-provider-consent").check();
    await recipientPanel.getByTestId("bootstrap-search").click();
    await expect(recipientPanel.getByTestId("bootstrap-discovery-outcome")).toContainText("ZERO");
    expect(provider.overpassCalls).toHaveLength(2);
    const recipientAudit = readDiscoveryAuditRequests(recipientJourney.id);
    expect(recipientAudit).toHaveLength(1);
    expect(recipientAudit[0]).not.toHaveProperty("center");
    expect(recipientAudit[0]).not.toHaveProperty("member_id");
    expect(recipientAudit[0]).not.toHaveProperty("traveler_id");
    await recipientPage.close();
  } finally {
    await Promise.all([
      new Promise<void>((resolve) => provider.cityServer.close(() => resolve())),
      new Promise<void>((resolve) => provider.overpassServer.close(() => resolve())),
    ]);
  }
});
