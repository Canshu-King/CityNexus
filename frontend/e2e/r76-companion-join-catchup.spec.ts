import { createHmac } from "node:crypto";
import { expect, test, type APIRequestContext, type Browser, type Page } from "@playwright/test";

const API = `http://127.0.0.1:${Number(process.env.CITYNEXUS_BACKEND_PORT ?? 8000)}`;

type Traveler = { id: string; display_name: string };

function travelerToken(travelerId: string): string {
  const secret = process.env.CITYNEXUS_TRAVELER_AUTH_SECRET;
  if (!secret || Buffer.byteLength(secret, "utf8") < 32) {
    throw new Error("R76 Playwright requires a per-run CITYNEXUS_TRAVELER_AUTH_SECRET");
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

test("R76 lets a signed nonmember accept an active-Journey invite and see honest catch-up", async ({ browser, request }) => {
  test.setTimeout(120_000);
  const resetToken = process.env.CITYNEXUS_DEMO_RESET_TOKEN;
  if (!resetToken) throw new Error("R76 Playwright requires the isolated-run CITYNEXUS_DEMO_RESET_TOKEN");

  const reset = await api<{ journey_id: string; traveler_id: string }>(request, "/api/v1/demo/reset", {
    method: "POST",
    headers: { "X-Demo-Reset-Token": resetToken },
  });
  const journeyId = reset.journey_id;
  const ownerId = reset.traveler_id;
  const ownerToken = travelerToken(ownerId);
  const journeyPath = `/api/v1/journeys/${journeyId}`;
  const plans = await api<Array<{ id: string }>>(request, `${journeyPath}/plans/generate`, {
    method: "POST",
    data: { candidate_count: 1 },
  });
  const planId = plans[0]?.id;
  if (!planId) throw new Error("R76 E2E could not generate an active Journey plan");
  await api(request, `${journeyPath}/plans/${planId}/select`, { method: "POST", token: ownerToken });
  await api(request, `${journeyPath}/start`, { method: "POST", token: ownerToken });

  const target = await api<Traveler>(request, "/api/v1/travelers", {
    method: "POST",
    data: { display_name: "R76 Signed New Companion", locale: "en-US", timezone: "Asia/Shanghai" },
  });
  const targetToken = travelerToken(target.id);

  const directAdd = await request.post(`${API}${journeyPath}/members`, {
    data: { traveler_id: target.id, role: "COLLABORATOR", invited_by: ownerId },
    headers: { Authorization: `Bearer ${ownerToken}` },
  });
  expect(directAdd.status()).toBe(409);
  expect(await directAdd.text()).toContain("RECIPIENT_ACCEPTANCE_REQUIRED");
  const beforeMembers = await api<Array<{ traveler_id: string }>>(request, `${journeyPath}/members`, { token: ownerToken });
  expect(beforeMembers.some((member) => member.traveler_id === target.id)).toBe(false);
  const beforeOperator = await request.get(`${API}${journeyPath}/operator`, {
    headers: { Authorization: `Bearer ${targetToken}` },
  });
  expect(beforeOperator.status()).toBe(403);

  const owner = await openPage(browser, ownerToken, journeyId);
  const companion = await openPage(browser, targetToken);
  try {
    const inviteTarget = owner.page.getByTestId("journey-membership-target-id");
    await inviteTarget.fill(target.id);
    const inviteResponsePromise = owner.page.waitForResponse((response) =>
      response.request().method() === "POST" && response.url().endsWith(`${journeyPath}/membership-invitations`),
    );
    await owner.page.getByTestId("journey-membership-send").click();
    const inviteResponse = await inviteResponsePromise;
    expect(inviteResponse.status()).toBe(201);
    const invitation = await inviteResponse.json() as { invitation_id: string; proposed_role: string; state: string };
    expect(invitation.proposed_role).toBe("COLLABORATOR");
    expect(invitation.state).toBe("OFFERED");

    const inbox = await api<Array<Record<string, unknown>>>(request, "/api/v1/travelers/me/journey-membership-invitations", {
      token: targetToken,
    });
    expect(inbox).toHaveLength(1);
    expect(Object.keys(inbox[0] ?? {}).sort()).toEqual([
      "approximate_start_date",
      "city_code",
      "expires_at",
      "invitation_id",
      "inviter_display_name",
      "journey_title",
      "proposed_role",
      "state",
    ].sort());
    const serializedInbox = JSON.stringify(inbox);
    expect(serializedInbox).not.toContain(journeyId);
    expect(serializedInbox).not.toContain(planId);

    await companion.page.getByTestId("journey-membership-refresh").click();
    const preview = companion.page.getByTestId("journey-membership-invitation");
    await expect(preview).toBeVisible();
    await expect(preview).toContainText(String(inbox[0]?.inviter_display_name));
    await expect(preview).toContainText(String(inbox[0]?.journey_title));
    await expect(preview).toContainText(String(inbox[0]?.city_code));
    await expect(preview).toContainText("COLLABORATOR");
    await expect(preview).not.toContainText(planId);
    await expect(preview).not.toContainText(journeyId);

    const acceptPromise = companion.page.waitForResponse((response) =>
      response.request().method() === "POST" && response.url().endsWith(`/journey-membership-invitations/${invitation.invitation_id}/respond`),
    );
    await preview.getByTestId("journey-membership-accept").click();
    const acceptedResponse = await acceptPromise;
    expect(acceptedResponse.ok()).toBeTruthy();
    await expect(companion.page.getByTestId("journey-group-presence")).toBeVisible();
    await expect(companion.page.getByTestId("journey-membership-catchup")).toBeVisible();
    await expect(companion.page.getByTestId("journey-membership-catchup")).toContainText("UNKNOWN / ROUTE_UNAVAILABLE");

    // Catch-up is a persistent current-Journey action, not a one-render
    // success toast. A newcomer can come back after a browser reload.
    await companion.page.reload({ waitUntil: "domcontentloaded" });
    await expect(companion.page.getByTestId("journey-membership-catchup")).toBeVisible();
    await expect(companion.page.getByTestId("journey-membership-catchup")).toContainText("UNKNOWN / ROUTE_UNAVAILABLE");

    const afterMembers = await api<Array<{ traveler_id: string; role: string; joined_at?: string | null }>>(
      request,
      `${journeyPath}/members`,
      { token: ownerToken },
    );
    const joined = afterMembers.filter((member) => member.traveler_id === target.id);
    expect(joined).toHaveLength(1);
    expect(joined[0].role).toBe("COLLABORATOR");
    expect(joined[0].joined_at).toBeTruthy();

    const duplicateAccept = await request.post(`${API}/api/v1/journey-membership-invitations/${invitation.invitation_id}/respond`, {
      data: { decision: "ACCEPT" },
      headers: { Authorization: `Bearer ${targetToken}` },
    });
    expect(duplicateAccept.status()).toBe(409);
    const finalMembers = await api<Array<{ traveler_id: string }>>(request, `${journeyPath}/members`, { token: ownerToken });
    expect(finalMembers.filter((member) => member.traveler_id === target.id)).toHaveLength(1);
  } finally {
    await owner.close();
    await companion.close();
  }
});
