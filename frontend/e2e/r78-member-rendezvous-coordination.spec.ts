import { createHmac } from "node:crypto";
import { expect, test, type APIRequestContext, type Browser, type Page } from "@playwright/test";

const API = `http://127.0.0.1:${Number(process.env.CITYNEXUS_BACKEND_PORT ?? 8000)}`;

type Traveler = { id: string; display_name: string };

function travelerToken(travelerId: string): string {
  const secret = process.env.CITYNEXUS_TRAVELER_AUTH_SECRET;
  if (!secret || Buffer.byteLength(secret, "utf8") < 32) {
    throw new Error("R78 Playwright requires a per-run CITYNEXUS_TRAVELER_AUTH_SECRET");
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

async function openPage(
  browser: Browser,
  token: string,
  journeyId?: string,
): Promise<{ page: Page; close: () => Promise<void> }> {
  const context = await browser.newContext({
    locale: "en-US",
    timezoneId: "Asia/Shanghai",
    storageState: { cookies: [], origins: [] },
  });
  const page = await context.newPage();
  await page.addInitScript(({ id, bearer }) => {
    if (id) localStorage.setItem("citynexus.v8.journey_id", id);
    localStorage.setItem("citynexus.locale", "en-US");
    sessionStorage.setItem("citynexus.traveler.bearer", bearer);
  }, { id: journeyId ?? null, bearer: token });
  await page.goto(journeyId ? "/v8/live" : "/v8/today", { waitUntil: "domcontentloaded" });
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
    headers: { "Idempotency-Key": "r78-member-" + inviteeId },
    data: { target_traveler_id: inviteeId },
  });
  await api(request, "/api/v1/journey-membership-invitations/" + offer.invitation_id + "/respond", {
    method: "POST",
    token: inviteeToken,
    data: { decision: "ACCEPT" },
  });
}

test("R78 closes a signed, audience-bound rendezvous help loop without location or plan side effects", async ({ browser, request }) => {
  test.setTimeout(180_000);
  const resetToken = process.env.CITYNEXUS_DEMO_RESET_TOKEN;
  if (!resetToken) throw new Error("R78 Playwright requires the isolated-run CITYNEXUS_DEMO_RESET_TOKEN");

  const reset = await api<{ journey_id: string; traveler_id: string }>(request, "/api/v1/demo/reset", {
    method: "POST",
    headers: { "X-Demo-Reset-Token": resetToken },
  });
  const journeyId = reset.journey_id;
  const journeyPath = "/api/v1/journeys/" + journeyId;
  const ownerId = reset.traveler_id;
  const ownerToken = travelerToken(ownerId);
  const plans = await api<Array<{ id: string }>>(request, journeyPath + "/plans/generate", {
    method: "POST",
    data: { candidate_count: 1 },
  });
  const planId = plans[0]?.id;
  if (!planId) throw new Error("R78 E2E could not generate an active Journey plan");
  await api(request, journeyPath + "/plans/" + planId + "/select", { method: "POST", token: ownerToken });
  await api(request, journeyPath + "/start", { method: "POST", token: ownerToken });

  const peer = await api<Traveler>(request, "/api/v1/travelers", {
    method: "POST",
    data: { display_name: "R78 Existing Companion", locale: "en-US", timezone: "Asia/Shanghai" },
  });
  const peerToken = travelerToken(peer.id);
  await acceptInvitation(request, journeyPath, ownerToken, peerToken, peer.id);

  const newcomer = await api<Traveler>(request, "/api/v1/travelers", {
    method: "POST",
    data: { display_name: "R78 New Companion", locale: "en-US", timezone: "Asia/Shanghai" },
  });
  const newcomerToken = travelerToken(newcomer.id);
  const later = await api<Traveler>(request, "/api/v1/travelers", {
    method: "POST",
    data: { display_name: "R78 Later Companion", locale: "en-US", timezone: "Asia/Shanghai" },
  });
  const laterToken = travelerToken(later.id);

  const owner = await openPage(browser, ownerToken, journeyId);
  const existingPeer = await openPage(browser, peerToken, journeyId);
  const companion = await openPage(browser, newcomerToken);
  const locationPosts: string[] = [];
  const routePosts: string[] = [];
  companion.page.on("request", (pageRequest) => {
    if (pageRequest.method() !== "POST") return;
    if (pageRequest.url().endsWith(journeyPath + "/location")) locationPosts.push(pageRequest.url());
    if (pageRequest.url().endsWith(journeyPath + "/group-presence/route")) routePosts.push(pageRequest.url());
  });

  let lateCompanion: Awaited<ReturnType<typeof openPage>> | null = null;
  try {
    const invitePromise = owner.page.waitForResponse((response) =>
      response.request().method() === "POST" && response.url().endsWith(journeyPath + "/membership-invitations"),
    );
    await owner.page.getByTestId("journey-membership-target-id").fill(newcomer.id);
    await owner.page.getByTestId("journey-membership-send").click();
    const inviteResponse = await invitePromise;
    expect(inviteResponse.status()).toBe(201);
    await companion.page.getByTestId("journey-membership-refresh").click();
    const invitation = companion.page.getByTestId("journey-membership-invitation");
    await expect(invitation).toBeVisible();
    await invitation.getByTestId("journey-membership-accept").click();
    await expect(companion.page.getByTestId("journey-membership-catchup")).toBeVisible();
    await expect(companion.page.getByTestId("journey-rendezvous-coordination")).toBeVisible();
    await expect(companion.page.getByTestId("journey-rendezvous-no-status")).toBeVisible();
    expect(locationPosts).toHaveLength(0);
    expect(routePosts).toHaveLength(0);

    // The first attempt is only a preview; cancelling it has no API side effect.
    await companion.page.getByTestId("journey-rendezvous-heading-share").click();
    const consent = companion.page.getByTestId("journey-rendezvous-consent");
    await expect(consent).toContainText("Current companions who can see this");
    await expect(consent).toContainText("R78 Existing Companion");
    await expect(consent).toContainText("GPS origin");
    await expect(consent).toContainText("not evidence of route danger, physical arrival");
    await consent.getByRole("button", { name: "Cancel" }).click();

    const firstSharePromise = companion.page.waitForResponse((response) =>
      response.request().method() === "POST" && response.url().endsWith("/rendezvous-member-signals"),
    );
    await companion.page.getByTestId("journey-rendezvous-heading-share").click();
    await companion.page.getByTestId("journey-rendezvous-consent-confirm").click();
    const firstShare = await firstSharePromise;
    expect(firstShare.status()).toBe(201);
    const firstSignal = await firstShare.json() as { signal_id: string; signal_kind: string };
    expect(firstSignal.signal_kind).toBe("HEADING_TO_RENDEZVOUS");
    expect(locationPosts).toHaveLength(0);
    expect(routePosts).toHaveLength(0);

    await owner.page.getByTestId("journey-rendezvous-refresh").click();
    await existingPeer.page.getByTestId("journey-rendezvous-refresh").click();
    const ownerStatus = owner.page.getByTestId("journey-rendezvous-status");
    const peerStatus = existingPeer.page.getByTestId("journey-rendezvous-status");
    await expect(ownerStatus).toContainText("R78 New Companion self-reports heading to the rendezvous");
    await expect(peerStatus).toContainText("R78 New Companion self-reports heading to the rendezvous");
    await expect(ownerStatus).toContainText("Self-reported and unverified");
    await owner.page.reload({ waitUntil: "domcontentloaded" });
    await expect(owner.page.getByTestId("journey-rendezvous-status")).toContainText("R78 New Companion");

    for (const viewerToken of [ownerToken, peerToken]) {
      const projected = await api<{ group_presence: { coordination_signals: Array<Record<string, unknown>> } }>(
        request, journeyPath + "/operator", { token: viewerToken },
      );
      const serialized = JSON.stringify(projected.group_presence.coordination_signals);
      expect(serialized).not.toContain("latitude");
      expect(serialized).not.toContain("longitude");
      expect(serialized).not.toContain("location_observation_id");
      expect(serialized).not.toContain("route_geometry");
    }

    // The consent dialog originally named A/B/C. After D joins, refreshing
    // the audience MUST close that consent instead of silently adding D to it.
    await companion.page.getByTestId("journey-rendezvous-help-share").click();
    const preJoinConsent = companion.page.getByTestId("journey-rendezvous-consent");
    await expect(preJoinConsent).toBeVisible();
    await expect(preJoinConsent).not.toContainText("R78 Later Companion");

    // A new member cannot inherit the earlier audience-bound disclosure.
    await acceptInvitation(request, journeyPath, ownerToken, laterToken, later.id);
    lateCompanion = await openPage(browser, laterToken, journeyId);
    await expect(lateCompanion.page.getByTestId("journey-rendezvous-no-status")).toBeVisible();
    await owner.page.getByTestId("journey-rendezvous-refresh").click();
    await companion.page.getByTestId("journey-rendezvous-refresh").click();
    await expect(companion.page.getByTestId("journey-rendezvous-consent")).toHaveCount(0);
    await expect(companion.page.getByTestId("journey-rendezvous-message"))
      .toContainText("companion list changed");
    await expect(owner.page.getByTestId("journey-rendezvous-no-status")).toBeVisible();
    await expect(companion.page.getByTestId("journey-rendezvous-no-status")).toBeVisible();

    const renewedSharePromise = companion.page.waitForResponse((response) =>
      response.request().method() === "POST" && response.url().endsWith("/rendezvous-member-signals"),
    );
    await companion.page.getByTestId("journey-rendezvous-heading-share").click();
    const renewedConsent = companion.page.getByTestId("journey-rendezvous-consent");
    await expect(renewedConsent).toContainText("R78 Later Companion");
    await companion.page.getByTestId("journey-rendezvous-consent-confirm").click();
    const renewedResponse = await renewedSharePromise;
    expect(renewedResponse.status()).toBe(201);
    const renewedSignal = await renewedResponse.json() as { signal_id: string };
    expect(renewedSignal.signal_id).not.toBe(firstSignal.signal_id);
    // A stale tab still holding the old signal cannot claim that its
    // withdrawal also stopped C's newly consented, expanded-audience status.
    const staleWithdraw = await request.post(
      `${API}${journeyPath}/rendezvous-member-signals/${firstSignal.signal_id}/withdraw`,
      { headers: { Authorization: `Bearer ${newcomerToken}` } },
    );
    expect(staleWithdraw.status()).toBe(409);
    expect(await staleWithdraw.text()).toContain("RENDEZVOUS_SIGNAL_WITHDRAW_TARGET_STALE");
    await lateCompanion.page.getByTestId("journey-rendezvous-refresh").click();
    const lateStatus = lateCompanion.page.getByTestId("journey-rendezvous-status");
    await expect(lateStatus).toHaveAttribute("data-signal-id", renewedSignal.signal_id);
    await expect(lateStatus).not.toHaveAttribute("data-signal-id", firstSignal.signal_id);

    const withdrawHeadingPromise = companion.page.waitForResponse((response) =>
      response.request().method() === "POST" && response.url().endsWith("/withdraw"),
    );
    await companion.page.getByTestId("journey-rendezvous-withdraw").click();
    expect((await withdrawHeadingPromise).ok()).toBeTruthy();
    await owner.page.getByTestId("journey-rendezvous-refresh").click();
    await expect(owner.page.getByTestId("journey-rendezvous-no-status")).toBeVisible();

    const helpSharePromise = companion.page.waitForResponse((response) =>
      response.request().method() === "POST" && response.url().endsWith("/rendezvous-member-signals"),
    );
    await companion.page.getByTestId("journey-rendezvous-help-share").click();
    await expect(companion.page.getByTestId("journey-rendezvous-consent")).toContainText("R78 Later Companion");
    await companion.page.getByTestId("journey-rendezvous-consent-confirm").click();
    const helpShare = await helpSharePromise;
    expect(helpShare.status()).toBe(201);
    const helpSignal = await helpShare.json() as { signal_id: string; signal_kind: string };
    expect(helpSignal.signal_kind).toBe("NEEDS_COORDINATION");

    await owner.page.getByTestId("journey-rendezvous-refresh").click();
    const helpCard = owner.page.getByTestId("journey-rendezvous-status");
    await expect(helpCard).toContainText("R78 New Companion self-reports needing coordination help");
    const acknowledgePromise = owner.page.waitForResponse((response) =>
      response.request().method() === "POST" && response.url().endsWith("/acknowledge"),
    );
    await owner.page.getByTestId("journey-rendezvous-help-acknowledge").click();
    const acknowledgementResponse = await acknowledgePromise;
    expect(acknowledgementResponse.ok()).toBeTruthy();
    const acknowledgement = await acknowledgementResponse.json() as { responder_display_name: string };

    await companion.page.getByTestId("journey-rendezvous-refresh").click();
    await expect(companion.page.getByTestId("journey-rendezvous-help-acknowledgement"))
      .toContainText(acknowledgement.responder_display_name);
    await expect(companion.page.getByTestId("journey-rendezvous-help-acknowledgement"))
      .toContainText("not a promise to wait there");
    await companion.page.reload({ waitUntil: "domcontentloaded" });
    await expect(companion.page.getByTestId("journey-rendezvous-help-acknowledgement"))
      .toContainText(acknowledgement.responder_display_name);
    await expect(owner.page.getByTestId("journey-rendezvous-help-acknowledge")).toHaveCount(0);

    const withdrawHelpPromise = companion.page.waitForResponse((response) =>
      response.request().method() === "POST" && response.url().endsWith("/withdraw"),
    );
    await companion.page.getByTestId("journey-rendezvous-withdraw").click();
    expect((await withdrawHelpPromise).ok()).toBeTruthy();
    await owner.page.getByTestId("journey-rendezvous-refresh").click();
    await expect(owner.page.getByTestId("journey-rendezvous-no-status")).toBeVisible();

    expect(locationPosts).toHaveLength(0);
    expect(routePosts).toHaveLength(0);
  } finally {
    await lateCompanion?.close();
    await owner.close();
    await existingPeer.close();
    await companion.close();
  }
});
