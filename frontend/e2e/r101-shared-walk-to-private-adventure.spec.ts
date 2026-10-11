import { createServer, type IncomingMessage, type ServerResponse } from "node:http";
import { expect, test, type APIRequestContext } from "@playwright/test";

const API = `http://127.0.0.1:${Number(process.env.CITYNEXUS_BACKEND_PORT ?? 8000)}`;
const OVERPASS_FIXTURE_PORT = 8258;
const VIEWPORT = { width: 390, height: 844 };
test.use({ viewport: VIEWPORT, hasTouch: true });

async function post<T>(request: APIRequestContext, path: string, data: unknown, token?: string): Promise<T> {
  const response = await request.post(`${API}${path}`, {
    data,
    headers: token ? { Authorization: `Bearer ${token}` } : undefined,
  });
  if (!response.ok()) throw new Error(`${path} -> ${response.status()}: ${(await response.text()).slice(0, 280)}`);
  return response.json() as Promise<T>;
}

type Traveler = { id: string; access_token: string };
type Journey = { id: string };
type Lookup = {
  receipt_id: string;
  verified_count: number;
  candidates: Array<{ candidate_id: string; external_id: string; name: string }>;
};

function startOverpassFixture() {
  const requestBodies: string[] = [];
  const server = createServer((request: IncomingMessage, response: ServerResponse) => {
    const chunks: Buffer[] = [];
    request.on("data", (chunk: Buffer) => chunks.push(chunk));
    request.on("end", () => {
      const body = new URLSearchParams(Buffer.concat(chunks).toString("utf8")).get("data") ?? "";
      requestBodies.push(body);
      response.writeHead(200, { "content-type": "application/json" });
      response.end(JSON.stringify({
        version: 0.6,
        generator: "R101 controlled TEST_PROVIDER exact union",
        elements: [
          { type: "node", id: 101001, lat: 31.2304, lon: 121.4737, tags: { name: "R101 Public Museum", tourism: "museum" } },
          { type: "way", id: 101002, center: { lat: 31.231, lon: 121.474 }, tags: { name: "R101 Public Garden", leisure: "park" } },
        ],
      }));
    });
  });
  const ready = new Promise<void>((resolve, reject) => {
    server.once("error", reject);
    server.listen(OVERPASS_FIXTURE_PORT, "127.0.0.1", resolve);
  });
  return { server, ready, requestBodies };
}

test("R101 recipient imports a public walk into an independent private adventure", async ({ browser, request }) => {
  const fixture = startOverpassFixture();
  await fixture.ready;
  try {
    const sender = await post<Traveler>(request, "/api/v1/travelers", {
      display_name: `R101 sender ${Date.now()}`,
      locale: "en-GB",
      timezone: "Asia/Shanghai",
    });
    const recipient = await post<Traveler>(request, "/api/v1/travelers", {
      display_name: `R101 recipient ${Date.now()}`,
      locale: "en-GB",
      timezone: "Asia/Shanghai",
    });
    const senderJourney = await post<Journey>(request, "/api/v1/journeys", {
      traveler_id: sender.id,
      title: "R101 sender draft",
      city_code: `CN-R101-A-${Date.now()}`,
      timezone: "Asia/Shanghai",
      start_at: "2026-10-20T10:00:00+08:00",
      end_at: "2026-10-21T18:00:00+08:00",
      budget: { amount_minor: 10000, currency: "CNY" },
    });
    const recipientJourney = await post<Journey>(request, "/api/v1/journeys", {
      traveler_id: recipient.id,
      title: "R101 recipient draft",
      city_code: `CN-R101-B-${Date.now()}`,
      timezone: "Asia/Shanghai",
      start_at: "2026-10-20T10:00:00+08:00",
      end_at: "2026-10-21T18:00:00+08:00",
      budget: { amount_minor: 10000, currency: "CNY" },
    });

    const objects = [
      { osm_type: "node" as const, osm_id: "101001", source_url: "https://www.openstreetmap.org/node/101001" },
      { osm_type: "way" as const, osm_id: "101002", source_url: "https://www.openstreetmap.org/way/101002" },
    ];
    const senderLookup = await post<Lookup>(
      request,
      `/api/v1/journeys/${senderJourney.id}/bootstrap-shared-walk/lookup`,
      { objects, provider_consent: true },
      sender.access_token,
    );
    expect(senderLookup.verified_count).toBe(2);
    const senderSaved = [] as Array<{ shortlist_id: string; name: string; source_url: string; source_provenance: string; captured_at: string }>;
    for (const candidate of senderLookup.candidates) {
      senderSaved.push(await post(request, `/api/v1/journeys/${senderJourney.id}/bootstrap-shortlist`, {
        receipt_id: senderLookup.receipt_id,
        candidate_id: candidate.candidate_id,
      }, sender.access_token));
    }
    await post(request, `/api/v1/journeys/${senderJourney.id}/bootstrap-shortlist/pocket-walk`, {
      first_shortlist_id: senderSaved[0].shortlist_id,
      second_shortlist_id: senderSaved[1].shortlist_id,
      max_walk_minutes: 20,
    }, sender.access_token);
    const senderShare = [
      "CityNexus public Pocket Walk",
      "sample/unverified location - not real-world verified",
      `1. ${senderSaved[0].name}`,
      `   OSM source: ${senderSaved[0].source_url}`,
      `   Source: ${senderSaved[0].source_provenance}; captured ${senderSaved[0].captured_at}`,
      `2. ${senderSaved[1].name}`,
      `   OSM source: ${senderSaved[1].source_url}`,
      `   Source: ${senderSaved[1].source_provenance}; captured ${senderSaved[1].captured_at}`,
      "Walking budget: 20 minutes (human-declared)",
      "Opening, cost, accessibility, arrival, and guaranteed ETA remain unknown.",
    ].join("\n");
    expect(senderShare).not.toContain(senderJourney.id);
    expect(senderShare).not.toContain(sender.access_token);
    const providerBeforeRecipient = fixture.requestBodies.length;
    expect(providerBeforeRecipient).toBe(1);

    const senderPage = await browser.newPage({ viewport: VIEWPORT });
    await senderPage.addInitScript(({ journeyId, token }) => {
      localStorage.setItem("citynexus.v8.journey_id", journeyId);
      sessionStorage.setItem("citynexus.traveler.bearer", token);
    }, { journeyId: senderJourney.id, token: sender.access_token });
    await senderPage.goto("/v8/hub", { waitUntil: "domcontentloaded" });
    await expect(senderPage.getByTestId("bootstrap-pocket-share-preview")).toContainText("R101 Public");
    const displayedSenderShare = await senderPage.getByTestId("bootstrap-pocket-share-preview").innerText();
    expect(displayedSenderShare).toContain("sample/unverified location");
    expect(displayedSenderShare).not.toContain(senderJourney.id);
    await senderPage.close();

    const recipientPage = await browser.newPage({ viewport: VIEWPORT });
    await recipientPage.route("https://www.google.com/maps/dir/**", async (route) => {
      await route.fulfill({ status: 200, contentType: "text/html", body: "R101 controlled public map handoff" });
    });
    await recipientPage.addInitScript(({ journeyId, token }) => {
      localStorage.setItem("citynexus.v8.journey_id", journeyId);
      sessionStorage.setItem("citynexus.traveler.bearer", token);
    }, { journeyId: recipientJourney.id, token: recipient.access_token });
    await recipientPage.goto("/v8/hub", { waitUntil: "domcontentloaded" });
    const importPanel = recipientPage.getByTestId("bootstrap-shared-walk-import");
    await expect(importPanel).toBeVisible();
    await expect(recipientPage.getByTestId("bootstrap-shortlist")).toContainText("Saved 0 of 3");
    await importPanel.getByTestId("bootstrap-shared-walk-textarea").fill(displayedSenderShare);
    await importPanel.getByTestId("bootstrap-shared-walk-preview-button").click();
    await expect(importPanel.locator('div[data-testid="bootstrap-shared-walk-preview"]')).toContainText("UNVERIFIED_SHARED_REFERENCE");
    expect(fixture.requestBodies).toHaveLength(providerBeforeRecipient);
    await recipientPage.reload({ waitUntil: "domcontentloaded" });
    expect(fixture.requestBodies).toHaveLength(providerBeforeRecipient);
    await importPanel.getByTestId("bootstrap-shared-walk-textarea").fill(displayedSenderShare);
    await importPanel.getByTestId("bootstrap-shared-walk-preview-button").click();
    await expect(importPanel.locator('div[data-testid="bootstrap-shared-walk-preview"]')).toContainText("UNVERIFIED_SHARED_REFERENCE");
    await importPanel.getByTestId("bootstrap-shared-walk-lookup-consent").check();
    await importPanel.getByTestId("bootstrap-shared-walk-lookup").click();
    await expect(importPanel.getByTestId("bootstrap-shared-walk-results")).toContainText("R101 Public Museum");
    expect(fixture.requestBodies).toHaveLength(providerBeforeRecipient + 1);
    const exactQuery = fixture.requestBodies.at(-1) ?? "";
    expect(exactQuery).toMatch(/^\[out:json\]\[timeout:10\];\((?:node\(101001\);way\(101002\);|way\(101002\);node\(101001\);)\);out center tags;$/);
    expect(fixture.requestBodies.at(-1)).not.toMatch(/bearer|journey|member|receipt|gps/i);

    const sharedCandidateIds = await importPanel.locator('[data-testid^="bootstrap-shared-walk-candidate-"]').evaluateAll((elements) =>
      elements.map((element) => (element.getAttribute("data-testid") ?? "").replace("bootstrap-shared-walk-candidate-", "")),
    );
    expect(sharedCandidateIds).toHaveLength(2);
    for (const candidateId of sharedCandidateIds) {
      await importPanel.getByTestId(`bootstrap-shared-walk-save-${candidateId}`).click();
    }
    await expect(recipientPage.getByTestId("bootstrap-shortlist")).toContainText("Saved 2 of 3");
    const recipientShortlistIds = await recipientPage.locator('[data-testid^="bootstrap-shortlist-item-"]').evaluateAll((elements) =>
      elements.map((element) => (element.getAttribute("data-testid") ?? "").replace("bootstrap-shortlist-item-", "")),
    );
    expect(recipientShortlistIds).toHaveLength(2);
    expect(recipientShortlistIds).not.toEqual(senderSaved.map((item) => item.shortlist_id));
    await recipientPage.getByTestId(`bootstrap-two-stop-first-${recipientShortlistIds[0]}`).click();
    await recipientPage.getByTestId(`bootstrap-two-stop-second-${recipientShortlistIds[1]}`).click();
    await recipientPage.getByTestId("bootstrap-pocket-walk-budget").selectOption("20");
    await recipientPage.getByTestId("bootstrap-pocket-walk-save").click();
    await expect(recipientPage.getByTestId("bootstrap-pocket-walk-card")).toBeVisible();
    await expect(recipientPage.getByTestId("bootstrap-pocket-walk-stops")).toContainText("R101 Public Museum");
    await recipientPage.reload({ waitUntil: "domcontentloaded" });
    await expect(recipientPage.getByTestId("bootstrap-pocket-walk-card")).toBeVisible();
    await expect(recipientPage.getByTestId("bootstrap-pocket-walk-budget")).toHaveValue("20");

    await recipientPage.getByTestId("bootstrap-pocket-navigate-first").click();
    await recipientPage.getByTestId("bootstrap-shortlist-navigation-consent-checkbox").check();
    const firstPopupPromise = recipientPage.waitForEvent("popup");
    await recipientPage.getByTestId("bootstrap-shortlist-navigation-confirm").click();
    const firstPopup = await firstPopupPromise;
    await firstPopup.waitForURL(/google\.com\/maps\/dir/);
    expect(firstPopup.url()).not.toContain("origin=");
    await firstPopup.close();
    await recipientPage.getByTestId("bootstrap-pocket-open-walk").click();
    await recipientPage.getByTestId("bootstrap-two-stop-consent-checkbox").check();
    const walkPopupPromise = recipientPage.waitForEvent("popup");
    await recipientPage.getByTestId("bootstrap-two-stop-confirm").click();
    const walkPopup = await walkPopupPromise;
    await walkPopup.waitForURL(/google\.com\/maps\/dir/);
    expect(new URL(walkPopup.url()).searchParams.get("travelmode")).toBe("walking");
    await walkPopup.close();

    for (const malicious of [
      `LIVE_PROVIDER\nhttps://www.openstreetmap.org/node/101001\nhttps://www.openstreetmap.org/way/101002\nhttps://www.openstreetmap.org/relation/999`,
      `https://user:pw@www.openstreetmap.org/node/101001\nhttps://www.openstreetmap.org/way/101002`,
      `https://www.openstreetmap.org/node/101001?access_token=secret\nhttps://www.openstreetmap.org/way/101002`,
      `<div>\nhttps://www.openstreetmap.org/node/101001\nhttps://www.openstreetmap.org/way/101002`,
    ]) {
      await importPanel.getByTestId("bootstrap-shared-walk-textarea").fill(malicious);
      await importPanel.getByTestId("bootstrap-shared-walk-preview-button").click();
      await expect(importPanel.getByTestId("bootstrap-shared-walk-error")).toBeVisible();
      expect(fixture.requestBodies).toHaveLength(providerBeforeRecipient + 1);
    }
  } finally {
    await new Promise<void>((resolve) => fixture.server.close(() => resolve()));
  }
});
