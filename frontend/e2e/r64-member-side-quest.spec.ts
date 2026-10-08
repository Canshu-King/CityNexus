import { createHmac } from "node:crypto";
import { expect, test, type APIRequestContext, type Browser, type Page } from "@playwright/test";

const API = `http://127.0.0.1:${Number(process.env.CITYNEXUS_BACKEND_PORT ?? 8000)}`;

type Traveler = { id: string; display_name: string };
type Place = { id: string; name: string; city_code: string };

function travelerToken(travelerId: string): string {
  const secret = process.env.CITYNEXUS_TRAVELER_AUTH_SECRET;
  if (!secret || Buffer.byteLength(secret, "utf8") < 32) {
    throw new Error("R64 E2E requires a test-only CITYNEXUS_TRAVELER_AUTH_SECRET of at least 32 bytes");
  }
  const issuedAt = Math.floor(Date.now() / 1000);
  const body = Buffer.from(JSON.stringify({
    aud: "citynexus-traveler",
    exp: issuedAt + 3600,
    iat: issuedAt,
    sub: travelerId,
    v: 1,
  })).toString("base64url");
  const signature = createHmac("sha256", secret).update(body, "ascii").digest("base64url");
  return `${body}.${signature}`;
}

async function api<T>(request: APIRequestContext, path: string, options: {
  method?: "GET" | "POST";
  data?: unknown;
  token?: string;
  headers?: Record<string, string>;
} = {}): Promise<T> {
  const response = options.method === "POST"
    ? await request.post(`${API}${path}`, {
        data: options.data,
        headers: { ...(options.token ? { Authorization: `Bearer ${options.token}` } : {}), ...options.headers },
      })
    : await request.get(`${API}${path}`, {
        headers: { ...(options.token ? { Authorization: `Bearer ${options.token}` } : {}), ...options.headers },
      });
  const text = await response.text();
  if (!response.ok()) throw new Error(`${options.method ?? "GET"} ${path} -> ${response.status()}: ${text.slice(0, 240)}`);
  return JSON.parse(text) as T;
}

async function openJourneyPage(browser: Browser, journeyId: string, token: string): Promise<{ page: Page; close: () => Promise<void> }> {
  const context = await browser.newContext();
  const page = await context.newPage();
  await page.addInitScript(({ id, bearer }) => {
    localStorage.setItem("citynexus.v8.journey_id", id);
    localStorage.setItem("citynexus.locale", "en-US");
    sessionStorage.setItem("citynexus.traveler.bearer", bearer);
  }, { id: journeyId, bearer: token });
  await page.goto("/v8/live", { waitUntil: "domcontentloaded" });
  await expect(page.getByTestId("journey-group-presence")).toBeVisible();
  return { page, close: () => context.close() };
}

test("R64 executes a private stop through real writes and keeps the collaborator projection coarse", async ({ browser, request }) => {
  const resetToken = process.env.CITYNEXUS_DEMO_RESET_TOKEN;
  if (!resetToken) throw new Error("R64 E2E requires CITYNEXUS_DEMO_RESET_TOKEN for its isolated demo database");
  const reset = await api<{ journey_id: string; traveler_id: string; city_code: string }>(request, "/api/v1/demo/reset", {
    method: "POST",
    headers: { "X-Demo-Reset-Token": resetToken },
  });
  const journeyId = reset.journey_id;
  const ownerId = reset.traveler_id;
  const ownerToken = travelerToken(ownerId);

  const candidates = await api<Array<{ id: string }>>(request, `/api/v1/journeys/${journeyId}/plans/generate`, {
    method: "POST",
    data: { candidate_count: 1 },
  });
  expect(candidates.length).toBeGreaterThan(0);
  const planId = candidates[0].id;
  await api(request, `/api/v1/journeys/${journeyId}/plans/${planId}/select`, { method: "POST" });
  await api(request, `/api/v1/journeys/${journeyId}/start`, { method: "POST" });

  const collaborator = await api<Traveler>(request, "/api/v1/travelers", {
    method: "POST",
    data: { display_name: "R64 Collaborator", locale: "en-US", timezone: "Asia/Tokyo" },
  });
  await api(request, `/api/v1/journeys/${journeyId}/members`, {
    method: "POST",
    data: { traveler_id: collaborator.id, role: "COLLABORATOR", invited_by: ownerId },
  });
  const collaboratorToken = travelerToken(collaborator.id);
  await api(request, `/api/v1/journeys/${journeyId}/operator/start`, {
    method: "POST",
    token: ownerToken,
    data: { interval_seconds: 3600 },
  });

  const experience = await api<{
    journey: { city_code: string };
    active_plan: { id: string; activities: Array<{ place_id: string | null }> };
  }>(request, `/api/v1/journeys/${journeyId}/experience`);
  const places = await api<Place[]>(request, `/api/v1/places?city_code=${encodeURIComponent(experience.journey.city_code)}`);
  const usedPlaceIds = new Set(experience.active_plan.activities.map((activity) => activity.place_id).filter(Boolean));
  const privatePlace = places.find((place) => !usedPlaceIds.has(place.id));
  if (!privatePlace) throw new Error("the demo city needs a known Place outside the active shared plan");

  const split = await api<{ planned_separation_result: { outcome: string } }>(request, `/api/v1/journeys/${journeyId}/agent/commands`, {
    method: "POST",
    token: ownerToken,
    data: {
      command: "I want to go alone for a while and meet at the next shared stop.",
      requested_autonomy: "PLAN_ONLY",
    },
  });
  expect(split.planned_separation_result.outcome).toBe("PLANNED_SPLIT_CREATED");
  const planRowsBefore = await api<Array<{ id: string }>>(request, `/api/v1/journeys/${journeyId}/plans`);
  const activePlanIdBefore = experience.active_plan.id;

  const owner = await openJourneyPage(browser, journeyId, ownerToken);
  const collaboratorSession = await openJourneyPage(browser, journeyId, collaboratorToken);
  try {
    const ownerCard = owner.page.getByTestId("member-side-quest-card");
    await expect(ownerCard).toBeVisible();
    await expect(ownerCard.getByTestId("member-side-quest-rendezvous")).toContainText("Shared rendezvous");
    await ownerCard.getByTestId("member-side-quest-search").fill(privatePlace.name);
    await ownerCard.getByTestId("member-side-quest-place").selectOption(privatePlace.id);
    await expect(ownerCard.getByTestId("member-side-quest-confirmation")).toContainText(
      `Go to ${privatePlace.name} before rejoining everyone at`,
    );
    await ownerCard.getByTestId("member-side-quest-save").click();
    await expect(ownerCard).toHaveAttribute("data-state", "READY");
    await expect(ownerCard.getByTestId("member-side-quest-owner-state")).toContainText(privatePlace.name);
    await expect(ownerCard).toContainText("shared Journey");

    await collaboratorSession.page.reload();
    const safeAway = collaboratorSession.page.getByTestId("journey-member-personal-stop");
    await expect(safeAway).toHaveAttribute("data-state", "PLANNED");
    await expect(safeAway).toContainText("destination visible only to them");
    await expect(collaboratorSession.page.locator("body")).not.toContainText(privatePlace.name);
    await expect(collaboratorSession.page.getByTestId("member-side-quest-card")).toHaveCount(0);

    await ownerCard.getByTestId("member-side-quest-start").click();
    await expect(ownerCard).toHaveAttribute("data-state", "EN_ROUTE");
    await ownerCard.getByTestId("member-side-quest-arrive").click();
    await expect(ownerCard).toHaveAttribute("data-state", "ARRIVED");
    await expect(ownerCard.getByTestId("member-side-quest-arrival-boundary")).toContainText("not device-verified physical presence");
    await ownerCard.getByTestId("member-side-quest-complete").click();
    await expect(ownerCard).toHaveAttribute("data-state", "COMPLETED");
    await expect(ownerCard.getByTestId("member-side-quest-return-emphasis")).toContainText("return to");
    await expect(ownerCard.getByTestId("member-side-quest-return-state")).toContainText("Return status unknown");
    await expect(ownerCard).toContainText("shared Journey is unchanged");

    await collaboratorSession.page.reload();
    const safeReturning = collaboratorSession.page.getByTestId("journey-member-personal-stop");
    await expect(safeReturning).toHaveAttribute("data-state", "FINISHED_RETURN_UNCONFIRMED");
    await expect(safeReturning).toContainText("return has not been confirmed");
    await expect(collaboratorSession.page.locator("body")).not.toContainText(privatePlace.name);
    await expect(collaboratorSession.page.getByTestId("member-side-quest-card")).toHaveCount(0);
    await expect(collaboratorSession.page.locator("body")).not.toContainText("You are physically rejoined");

    const finalExperience = await api<{ active_plan: { id: string } }>(request, `/api/v1/journeys/${journeyId}/experience`);
    const planRowsAfter = await api<Array<{ id: string }>>(request, `/api/v1/journeys/${journeyId}/plans`);
    expect(finalExperience.active_plan.id).toBe(activePlanIdBefore);
    expect(planRowsAfter.map((row) => row.id).sort()).toEqual(planRowsBefore.map((row) => row.id).sort());
  } finally {
    await Promise.all([owner.close(), collaboratorSession.close()]);
  }
});
