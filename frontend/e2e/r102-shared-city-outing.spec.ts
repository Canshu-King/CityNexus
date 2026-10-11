import { execFileSync } from "node:child_process";
import { createServer, type IncomingMessage, type ServerResponse } from "node:http";
import { expect, test, type APIRequestContext } from "@playwright/test";

const API = `http://127.0.0.1:${Number(process.env.CITYNEXUS_BACKEND_PORT ?? 8000)}`;
const OVERPASS_FIXTURE_PORT = 8260;
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
  candidates: Array<{
    candidate_id: string;
    external_id: string;
    name: string;
    latitude: number;
    longitude: number;
    opening_observed_at: string;
    provider_provenance: string;
    public_access_state: string;
  }>;
};

function startOverpassFixture() {
  const requestBodies: string[] = [];
  const server = createServer((request: IncomingMessage, response: ServerResponse) => {
    const chunks: Buffer[] = [];
    request.on("data", (chunk: Buffer) => chunks.push(chunk));
    request.on("end", () => {
      const body = new URLSearchParams(Buffer.concat(chunks).toString("utf8")).get("data") ?? "";
      requestBodies.push(body);
      const memberLabel = requestBodies.length === 1 ? "owner" : "collaborator";
      const latitude = requestBodies.length === 1 ? 31.2304 : 31.2404;
      const longitude = requestBodies.length === 1 ? 121.4737 : 121.4837;
      response.writeHead(200, { "content-type": "application/json" });
      response.end(JSON.stringify({
        version: 0.6,
        generator: "R102 controlled TEST_PROVIDER exact union",
        elements: [
          {
            type: "node",
            id: 102001,
            lat: latitude,
            lon: longitude,
            tags: { name: `R102 ${memberLabel} museum`, tourism: "museum" },
          },
          {
            type: "way",
            id: 102002,
            center: { lat: latitude + 0.001, lon: longitude + 0.001 },
            tags: {
              name: `R102 ${memberLabel} indoor gallery`,
              tourism: "gallery",
              indoor: "only",
            },
          },
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

function addCollaboratorToJourney(journeyId: string, ownerId: string, collaboratorId: string) {
  const python = process.env.CITYNEXUS_PYTHON;
  if (!python) throw new Error("CITYNEXUS_PYTHON is required for the signed member fixture");
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

function readScopedEvidence(journeyId: string) {
  const python = process.env.CITYNEXUS_PYTHON;
  if (!python) throw new Error("CITYNEXUS_PYTHON is required for the evidence assertion");
  const script = [
    "import json",
    "import sys",
    "from sqlalchemy import select",
    "from app.db.session import SessionLocal",
    "from app.db.models import RealPlaceCandidate",
    "journey_id = sys.argv[1]",
    "with SessionLocal() as session:",
    "    rows = session.scalars(select(RealPlaceCandidate).where(RealPlaceCandidate.journey_id == journey_id).order_by(RealPlaceCandidate.external_id)).all()",
    "    print(json.dumps([{'external_id': row.external_id, 'evidence': json.loads(row.evidence_json or '{}')} for row in rows]))",
  ].join("\n");
  const directEnv = { ...process.env };
  delete directEnv.CITYNEXUS_E2E_RUN_ID;
  return JSON.parse(execFileSync(python, ["-c", script, journeyId], {
    cwd: "../backend",
    env: directEnv,
    encoding: "utf8",
    stdio: "pipe",
    timeout: 15_000,
  })) as Array<{ external_id: string; evidence: { bootstrap_scopes?: Array<Record<string, unknown>> } }>;
}

test("R102 keeps one shared OSM identity fresh and member-scoped", async ({ browser, request }) => {
  const fixture = startOverpassFixture();
  await fixture.ready;
  try {
    const owner = await post<Traveler>(request, "/api/v1/travelers", {
      display_name: `R102 owner ${Date.now()}`,
      locale: "en-GB",
      timezone: "Asia/Shanghai",
    });
    const collaborator = await post<Traveler>(request, "/api/v1/travelers", {
      display_name: `R102 collaborator ${Date.now()}`,
      locale: "en-GB",
      timezone: "Asia/Shanghai",
    });
    const cityCode = `CN-R102-SH-${Date.now()}`;
    const journey = await post<Journey>(request, "/api/v1/journeys", {
      traveler_id: owner.id,
      title: "R102 one shared city outing",
      city_code: cityCode,
      timezone: "Asia/Shanghai",
      start_at: "2026-10-20T10:00:00+08:00",
      end_at: "2026-10-21T18:00:00+08:00",
      budget: { amount_minor: 10000, currency: "CNY" },
    });
    addCollaboratorToJourney(journey.id, owner.id, collaborator.id);

    const objects = [
      { osm_type: "node" as const, osm_id: "102001", source_url: "https://www.openstreetmap.org/node/102001" },
      { osm_type: "way" as const, osm_id: "102002", source_url: "https://www.openstreetmap.org/way/102002" },
    ];
    const ownerLookup = await post<Lookup>(
      request,
      `/api/v1/journeys/${journey.id}/bootstrap-shared-walk/lookup`,
      { objects, provider_consent: true },
      owner.access_token,
    );
    expect(ownerLookup.verified_count).toBe(2);
    expect(ownerLookup.candidates.map((candidate) => candidate.name)).toEqual(expect.arrayContaining([
      "R102 owner museum",
      "R102 owner indoor gallery",
    ]));
    expect(ownerLookup.candidates.every((candidate) => candidate.provider_provenance === "TEST_PROVIDER")).toBeTruthy();
    const ownerIndoor = ownerLookup.candidates.find((candidate) => candidate.external_id.endsWith("/102002"));
    expect(ownerIndoor?.public_access_state).toBe("INDOOR_ACCESS_UNVERIFIED");
    const sourceByExternalId = new Map(objects.map((object) => [`overpass:${object.osm_type}/${object.osm_id}`, object.source_url]));
    const ownerShare = ownerLookup.candidates.map((candidate, index) => `${index + 1}. ${candidate.name}\n   OSM source: ${sourceByExternalId.get(candidate.external_id)}`).join("\n");
    const ownerObservedByExternalId = new Map(ownerLookup.candidates.map((candidate) => [candidate.external_id, candidate]));

    const page = await browser.newPage({ viewport: VIEWPORT });
    await page.addInitScript(({ journeyId, token }) => {
      localStorage.setItem("citynexus.v8.journey_id", journeyId);
      sessionStorage.setItem("citynexus.traveler.bearer", token);
    }, { journeyId: journey.id, token: collaborator.access_token });
    await page.goto("/v8/hub", { waitUntil: "domcontentloaded" });
    await page.evaluate((token) => {
      sessionStorage.setItem("citynexus.traveler.bearer", token);
      window.dispatchEvent(new CustomEvent("citynexus.traveler.bearer.changed"));
    }, collaborator.access_token);
    const importPanel = page.getByTestId("bootstrap-shared-walk-import");
    await expect(importPanel).toBeVisible();
    await importPanel.getByTestId("bootstrap-shared-walk-textarea").fill(ownerShare);
    await importPanel.getByTestId("bootstrap-shared-walk-preview-button").click();
    await expect(importPanel.locator('div[data-testid="bootstrap-shared-walk-preview"]')).toContainText("UNVERIFIED_SHARED_REFERENCE");
    expect(fixture.requestBodies).toHaveLength(1);

    await importPanel.getByTestId("bootstrap-shared-walk-lookup-consent").check();
    const lookupResponse = page.waitForResponse((response) =>
      response.url().includes(`/api/v1/journeys/${journey.id}/bootstrap-shared-walk/lookup`) && response.request().method() === "POST",
    );
    await importPanel.getByTestId("bootstrap-shared-walk-lookup").click();
    const collaboratorLookup = await (await lookupResponse).json() as Lookup;
    expect(collaboratorLookup.verified_count).toBe(2);
    expect(collaboratorLookup.candidates.map((candidate) => candidate.name)).toEqual(expect.arrayContaining([
      "R102 collaborator museum",
      "R102 collaborator indoor gallery",
    ]));
    expect(collaboratorLookup.candidates.every((candidate) => candidate.provider_provenance === "TEST_PROVIDER")).toBeTruthy();
    for (const candidate of collaboratorLookup.candidates) {
      const ownerCandidate = ownerObservedByExternalId.get(candidate.external_id);
      expect(ownerCandidate).toBeDefined();
      expect(candidate.latitude).not.toBe(ownerCandidate?.latitude);
      expect(candidate.longitude).not.toBe(ownerCandidate?.longitude);
    }
    expect(collaboratorLookup.candidates.find((candidate) => candidate.external_id.endsWith("/102002"))?.public_access_state).toBe("INDOOR_ACCESS_UNVERIFIED");
    await expect(importPanel.getByTestId("bootstrap-shared-walk-results")).toContainText("R102 collaborator museum");
    await expect(importPanel.getByTestId("bootstrap-shared-walk-results")).toContainText("indoor-only access");
    expect(fixture.requestBodies).toHaveLength(2);
    expect(fixture.requestBodies[1]).toMatch(/^\[out:json\]\[timeout:10\];\((?:node\(102001\);way\(102002\);|way\(102002\);node\(102001\);)\);out center tags;$/);
    expect(fixture.requestBodies[1]).not.toMatch(/journey|member|receipt|gps|bearer/i);

    for (const candidate of collaboratorLookup.candidates) {
      await importPanel.getByTestId(`bootstrap-shared-walk-save-${candidate.candidate_id}`).click();
    }
    await expect(page.getByTestId("bootstrap-shortlist")).toContainText("Saved 2 of 3");
    await expect(page.getByTestId("bootstrap-shortlist")).toContainText("public visitability unverified");

    const evidence = readScopedEvidence(journey.id);
    expect(evidence).toHaveLength(2);
    for (const row of evidence) {
      const scopes = row.evidence.bootstrap_scopes ?? [];
      expect(scopes).toHaveLength(2);
      expect(scopes.every((scope) => scope.provider_provenance === "TEST_PROVIDER")).toBeTruthy();
      expect(new Set(scopes.map((scope) => scope.member_id)).size).toBe(2);
      expect(new Set(scopes.map((scope) => scope.captured_at)).size).toBe(2);
      expect(new Set(scopes.map((scope) => `${scope.latitude},${scope.longitude}`)).size).toBe(2);
      expect(scopes.map((scope) => scope.observed_name)).toEqual(expect.arrayContaining([
        row.external_id.endsWith("/102001") ? "R102 owner museum" : "R102 owner indoor gallery",
        row.external_id.endsWith("/102001") ? "R102 collaborator museum" : "R102 collaborator indoor gallery",
      ]));
    }

    await importPanel.getByTestId("bootstrap-shared-walk-textarea").fill(
      "HTTPS://OPENSTREETMAP.ORG/node/102001%2Fextra\nhttps://www.openstreetmap.org/way/102002",
    );
    await importPanel.getByTestId("bootstrap-shared-walk-preview-button").click();
    await expect(importPanel.getByTestId("bootstrap-shared-walk-error")).toBeVisible();
    expect(fixture.requestBodies).toHaveLength(2);
    await page.close();
  } finally {
    await new Promise<void>((resolve) => fixture.server.close(() => resolve()));
  }
});
