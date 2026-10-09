import { createHmac } from "node:crypto";
import { expect, test, type APIRequestContext, type Browser, type Page } from "@playwright/test";

const API = `http://127.0.0.1:${Number(process.env.CITYNEXUS_BACKEND_PORT ?? 8000)}`;

type Traveler = { id: string; display_name: string };
type HandoffCandidate = {
  place_id: string;
  name: string;
  latitude: number;
  longitude: number;
  coordinate_system: "WGS84";
  source_label: string;
  evidence_grade: string;
  is_original_shared_stop: boolean;
  distance_from_original_m: number;
  distance_basis: "STRAIGHT_LINE_NOT_ETA";
};

function travelerToken(travelerId: string): string {
  const secret = process.env.CITYNEXUS_TRAVELER_AUTH_SECRET;
  if (!secret || Buffer.byteLength(secret, "utf8") < 32) {
    throw new Error("R79 Playwright requires a per-run CITYNEXUS_TRAVELER_AUTH_SECRET");
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

async function openPage(browser: Browser, token: string, journeyId: string): Promise<{ page: Page; close: () => Promise<void> }> {
  const context = await browser.newContext({
    locale: "en-US",
    timezoneId: "Asia/Shanghai",
    storageState: { cookies: [], origins: [] },
  });
  const page = await context.newPage();
  await page.addInitScript(({ id, bearer }) => {
    localStorage.setItem("citynexus.v8.journey_id", id);
    localStorage.setItem("citynexus.locale", "en-US");
    sessionStorage.setItem("citynexus.traveler.bearer", bearer);
  }, { id: journeyId, bearer: token });
  await page.goto("/v8/live", { waitUntil: "domcontentloaded" });
  await expect(page.getByTestId("journey-membership-panel")).toBeVisible();
  return { page, close: () => context.close() };
}

async function acceptInvitation(
  request: APIRequestContext,
  journeyPath: string,
  ownerToken: string,
  inviteeToken: string,
  inviteeId: string,
): Promise<void> {
  const offer = await api<{ invitation_id: string }>(request, journeyPath + "/membership-invitations", {
    method: "POST",
    token: ownerToken,
    headers: { "Idempotency-Key": "r79-member-" + inviteeId },
    data: { target_traveler_id: inviteeId },
  });
  await api(request, "/api/v1/journey-membership-invitations/" + offer.invitation_id + "/respond", {
    method: "POST",
    token: inviteeToken,
    data: { decision: "ACCEPT" },
  });
}

test("R79 gives the signed helper and requester a private, mutually accepted public handoff", async ({ browser, request }) => {
  test.setTimeout(180_000);
  const resetToken = process.env.CITYNEXUS_DEMO_RESET_TOKEN;
  if (!resetToken) throw new Error("R79 Playwright requires the isolated-run CITYNEXUS_DEMO_RESET_TOKEN");

  const reset = await api<{ journey_id: string; traveler_id: string }>(request, "/api/v1/demo/reset", {
    method: "POST",
    headers: { "X-Demo-Reset-Token": resetToken },
  });
  const journeyId = reset.journey_id;
  const journeyPath = "/api/v1/journeys/" + journeyId;
  const helperId = reset.traveler_id;
  const helperToken = travelerToken(helperId);
  const plans = await api<Array<{ id: string }>>(request, journeyPath + "/plans/generate", {
    method: "POST",
    data: { candidate_count: 1 },
  });
  const planId = plans[0]?.id;
  if (!planId) throw new Error("R79 E2E could not generate a current Journey plan");
  await api(request, journeyPath + "/plans/" + planId + "/select", { method: "POST", token: helperToken });
  await api(request, journeyPath + "/start", { method: "POST", token: helperToken });

  const bystander = await api<Traveler>(request, "/api/v1/travelers", {
    method: "POST", data: { display_name: "R79 Bystander", locale: "en-US", timezone: "Asia/Shanghai" },
  });
  const bystanderToken = travelerToken(bystander.id);
  await acceptInvitation(request, journeyPath, helperToken, bystanderToken, bystander.id);
  const requester = await api<Traveler>(request, "/api/v1/travelers", {
    method: "POST", data: { display_name: "R79 Requester", locale: "en-US", timezone: "Asia/Shanghai" },
  });
  const requesterToken = travelerToken(requester.id);
  await acceptInvitation(request, journeyPath, helperToken, requesterToken, requester.id);

  const helperBefore = await api<{ group_presence: { active_plan_version_id: string; current_activity_id: string | null } }>(
    request, journeyPath + "/operator", { token: helperToken },
  );
  const beforePlanId = helperBefore.group_presence.active_plan_version_id;
  const beforeCursor = helperBefore.group_presence.current_activity_id;
  const helper = await openPage(browser, helperToken, journeyId);
  const peer = await openPage(browser, bystanderToken, journeyId);
  const requesterPage = await openPage(browser, requesterToken, journeyId);
  const forbiddenPosts: string[] = [];
  for (const page of [helper.page, peer.page, requesterPage.page]) {
    page.on("request", (pageRequest) => {
      if (pageRequest.method() !== "POST") return;
      if (pageRequest.url().endsWith(journeyPath + "/location")
        || pageRequest.url().endsWith(journeyPath + "/group-presence/route")) {
        forbiddenPosts.push(pageRequest.url());
      }
    });
  }

  const osmUrls: string[] = [];
  for (const context of [helper.page.context(), requesterPage.page.context()]) {
    context.on("request", (item) => {
      if (item.url().startsWith("https://www.openstreetmap.org/")) osmUrls.push(item.url());
    });
    await context.route("**/*", async (route) => {
      if (route.request().url().startsWith("https://www.openstreetmap.org/")) {
        await route.abort();
        return;
      }
      await route.continue();
    });
  }

  try {
    await requesterPage.page.getByTestId("journey-rendezvous-help-share").click();
    const consent = requesterPage.page.getByTestId("journey-rendezvous-consent");
    await expect(consent).toBeVisible();
    await expect(consent).toContainText("Current companions who can see this");
    const helpPromise = requesterPage.page.waitForResponse((response) =>
      response.request().method() === "POST" && response.url().endsWith("/rendezvous-member-signals"),
    );
    await requesterPage.page.getByTestId("journey-rendezvous-consent-confirm").click();
    const helpResponse = await helpPromise;
    expect(helpResponse.status()).toBe(201);
    const help = await helpResponse.json() as { signal_id: string; signal_kind: string };
    expect(help.signal_kind).toBe("NEEDS_COORDINATION");

    await helper.page.getByTestId("journey-rendezvous-refresh").click();
    const helpCard = helper.page.getByTestId("journey-rendezvous-status");
    await expect(helpCard).toContainText("R79 Requester self-reports needing coordination help");
    const ackPromise = helper.page.waitForResponse((response) =>
      response.request().method() === "POST" && response.url().endsWith("/acknowledge"),
    );
    await helper.page.getByTestId("journey-rendezvous-help-acknowledge").click();
    expect((await ackPromise).ok()).toBeTruthy();
    await helper.page.getByTestId("journey-rendezvous-refresh").click();
    await expect(helper.page.getByTestId("journey-buddy-load-candidates")).toBeVisible();

    const bystanderCandidates = await request.get(
      `${API}${journeyPath}/rendezvous-buddy-handoffs/candidates?signal_id=${help.signal_id}`,
      { headers: { Authorization: `Bearer ${bystanderToken}` } },
    );
    expect(bystanderCandidates.status()).toBe(403);
    const bystanderCurrent = await api<{ items: unknown[] }>(request, journeyPath + "/rendezvous-buddy-handoffs/current", {
      token: bystanderToken,
    });
    expect(bystanderCurrent.items).toEqual([]);

    const candidatesPromise = helper.page.waitForResponse((response) =>
      response.request().method() === "GET" && response.url().includes("/rendezvous-buddy-handoffs/candidates?signal_id="),
    );
    await helper.page.getByTestId("journey-buddy-load-candidates").click();
    const candidatesResponse = await candidatesPromise;
    expect(candidatesResponse.status()).toBe(200);
    const candidateList = await candidatesResponse.json() as { items: HandoffCandidate[] };
    expect(candidateList.items.length).toBeGreaterThanOrEqual(1);
    expect(candidateList.items.length).toBeLessThanOrEqual(3);
    const selected = candidateList.items.find((item) => !item.is_original_shared_stop) ?? candidateList.items[0];
    expect(selected.evidence_grade).toBe("DEMO_FIXTURE_NOT_LIVE_VERIFIED");
    expect(selected.distance_basis).toBe("STRAIGHT_LINE_NOT_ETA");
    expect(selected.distance_from_original_m).toBeLessThanOrEqual(1500);
    await expect(helper.page.getByTestId("journey-buddy-candidate-chooser"))
      .toContainText("feasibility is unverified");
    await helper.page.getByTestId("journey-buddy-candidate-select").selectOption(selected.place_id);
    const offerPromise = helper.page.waitForResponse((response) =>
      response.request().method() === "POST" && response.url().endsWith("/rendezvous-buddy-handoffs"),
    );
    await helper.page.getByTestId("journey-buddy-offer").click();
    const offerResponse = await offerPromise;
    expect(offerResponse.status()).toBe(201);
    const offered = await offerResponse.json() as { handoff_id: string; status: string };
    expect(offered.status).toBe("OFFERED");
    await expect(helper.page.getByTestId("journey-buddy-handoff")).toContainText(selected.name);

    await requesterPage.page.getByTestId("journey-rendezvous-refresh").click();
    const requesterOffer = requesterPage.page.getByTestId("journey-buddy-handoff");
    await expect(requesterOffer).toBeVisible();
    await expect(requesterOffer).toContainText(selected.name);
    await expect(requesterOffer).toContainText("not a route or ETA");
    await expect(requesterOffer).toContainText("UNKNOWN");

    const bystanderOperator = await api<Record<string, unknown>>(request, journeyPath + "/operator", { token: bystanderToken });
    expect(JSON.stringify(bystanderOperator)).not.toContain(offered.handoff_id);
    const bystanderAfterOffer = await api<{ items: unknown[] }>(
      request, journeyPath + "/rendezvous-buddy-handoffs/current", { token: bystanderToken },
    );
    expect(bystanderAfterOffer.items).toEqual([]);
    expect(forbiddenPosts).toEqual([]);
    expect(osmUrls).toEqual([]);

    const acceptPromise = requesterPage.page.waitForResponse((response) =>
      response.request().method() === "POST" && response.url().endsWith("/rendezvous-buddy-handoffs/" + offered.handoff_id + "/respond"),
    );
    await requesterPage.page.getByTestId("journey-buddy-accept").click();
    expect((await acceptPromise).status()).toBe(200);
    await helper.page.getByTestId("journey-rendezvous-refresh").click();
    await requesterPage.page.getByTestId("journey-rendezvous-refresh").click();
    await expect(helper.page.getByTestId("journey-buddy-accepted-truth")).toContainText("not GPS proof");
    await expect(requesterPage.page.getByTestId("journey-buddy-accepted-truth")).toContainText("not GPS proof");

    // Current handoffs are fetched from the pair-private endpoint on page reload.
    await helper.page.reload({ waitUntil: "domcontentloaded" });
    await requesterPage.page.reload({ waitUntil: "domcontentloaded" });
    await expect(helper.page.getByTestId("journey-buddy-handoff")).toContainText(selected.name);
    await expect(requesterPage.page.getByTestId("journey-buddy-handoff")).toContainText(selected.name);

    // A declined map consent produces no OSM request. Each participant then
    // separately consents to opening the same exact public WGS84 pin.
    await requesterPage.page.getByTestId("journey-buddy-map-open").click();
    await expect(requesterPage.page.getByTestId("journey-buddy-map-consent")).toContainText(selected.name);
    await requesterPage.page.getByTestId("journey-buddy-map-cancel").click();
    expect(osmUrls).toEqual([]);

    const openRequesterMap = async () => {
      const requestPromise = requesterPage.page.context().waitForEvent("request", (item) =>
        item.url().startsWith("https://www.openstreetmap.org/"), { timeout: 15_000 },
      );
      const popupPromise = requesterPage.page.waitForEvent("popup");
      await requesterPage.page.getByTestId("journey-buddy-map-open").click();
      await requesterPage.page.getByTestId("journey-buddy-map-confirm").click();
      const [mapRequest, popup] = await Promise.all([requestPromise, popupPromise]);
      const url = new URL(mapRequest.url());
      expect(url.searchParams.get("mlat")).toBe(String(selected.latitude));
      expect(url.searchParams.get("mlon")).toBe(String(selected.longitude));
      expect(url.searchParams.has("origin")).toBe(false);
      await popup.close().catch(() => undefined);
    };
    await openRequesterMap();

    const openHelperMap = async () => {
      const requestPromise = helper.page.context().waitForEvent("request", (item) =>
        item.url().startsWith("https://www.openstreetmap.org/"), { timeout: 15_000 },
      );
      const popupPromise = helper.page.waitForEvent("popup");
      await helper.page.getByTestId("journey-buddy-map-open").click();
      await helper.page.getByTestId("journey-buddy-map-confirm").click();
      const [mapRequest, popup] = await Promise.all([requestPromise, popupPromise]);
      const url = new URL(mapRequest.url());
      expect(url.searchParams.get("mlat")).toBe(String(selected.latitude));
      expect(url.searchParams.get("mlon")).toBe(String(selected.longitude));
      expect(url.searchParams.has("origin")).toBe(false);
      await popup.close().catch(() => undefined);
    };
    await openHelperMap();
    expect(osmUrls).toHaveLength(2);
    expect(forbiddenPosts).toEqual([]);

    const after = await api<{ group_presence: { active_plan_version_id: string; current_activity_id: string | null } }>(
      request, journeyPath + "/operator", { token: helperToken },
    );
    expect(after.group_presence.active_plan_version_id).toBe(beforePlanId);
    expect(after.group_presence.current_activity_id).toBe(beforeCursor);

    const revokePromise = requesterPage.page.waitForResponse((response) =>
      response.request().method() === "POST" && response.url().endsWith("/rendezvous-buddy-handoffs/" + offered.handoff_id + "/revoke"),
    );
    await requesterPage.page.getByTestId("journey-buddy-close").click();
    expect((await revokePromise).status()).toBe(200);
    await expect(requesterPage.page.getByTestId("journey-buddy-handoff")).toHaveCount(0);
    const helperCurrent = await api<{ items: unknown[] }>(
      request, journeyPath + "/rendezvous-buddy-handoffs/current", { token: helperToken },
    );
    expect(helperCurrent.items).toEqual([]);
    expect(osmUrls).toHaveLength(2);
    expect(forbiddenPosts).toEqual([]);
  } finally {
    await helper.close();
    await peer.close();
    await requesterPage.close();
  }
});
