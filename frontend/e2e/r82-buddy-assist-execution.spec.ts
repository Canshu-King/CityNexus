import { createHmac } from "node:crypto";
import { spawnSync } from "node:child_process";
import { expect, test, type APIRequestContext, type Browser, type Page } from "@playwright/test";

const API = `http://127.0.0.1:${Number(process.env.CITYNEXUS_BACKEND_PORT ?? 8000)}`;

type Traveler = { id: string; display_name: string };
type Stop = {
  activity_id: string;
  place_id: string;
  place_name: string;
  latitude: number | null;
  longitude: number | null;
  coordinate_system: string | null;
};
type Presence = {
  active_plan_version_id: string;
  current_activity_id: string | null;
  rendezvous: Stop;
  members: Array<{ member_id: string }>;
};

function travelerToken(travelerId: string): string {
  const secret = process.env.CITYNEXUS_TRAVELER_AUTH_SECRET;
  if (!secret || Buffer.byteLength(secret, "utf8") < 32) {
    throw new Error("R82 Playwright requires a per-run CITYNEXUS_TRAVELER_AUTH_SECRET");
  }
  const issuedAt = Math.floor(Date.now() / 1000);
  const body = Buffer.from(JSON.stringify({
    aud: "citynexus-traveler", exp: issuedAt + 3600, iat: issuedAt, sub: travelerId, v: 1,
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
  return text ? JSON.parse(text) as T : {} as T;
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
    headers: { "Idempotency-Key": "r82-member-" + inviteeId },
    data: { target_traveler_id: inviteeId },
  });
  await api(request, "/api/v1/journey-membership-invitations/" + offer.invitation_id + "/respond", {
    method: "POST", token: inviteeToken, data: { decision: "ACCEPT" },
  });
}

async function openPage(
  browser: Browser,
  token: string,
  journeyId: string,
  geolocation: { latitude: number; longitude: number; accuracy: number },
): Promise<{ page: Page; close: () => Promise<void> }> {
  const context = await browser.newContext({
    locale: "en-US",
    timezoneId: "Asia/Shanghai",
    permissions: ["geolocation"],
    geolocation,
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

function runIsolatedDatabasePython(code: string, ...args: string[]): string {
  const python = process.env.CITYNEXUS_PYTHON;
  const databaseUrl = process.env.CITYNEXUS_DATABASE_URL;
  if (!python || !databaseUrl?.startsWith("sqlite:///")) {
    throw new Error("R82 controlled-expiry checks require the authoritative isolated SQLite run");
  }
  const databasePath = databaseUrl.replace(/^sqlite:\/\//, "");
  const result = spawnSync(python, ["-c", code, databasePath, ...args], { encoding: "utf8" });
  if (result.status !== 0) {
    throw new Error(`R82 isolated SQLite helper failed: ${result.stderr || result.stdout}`);
  }
  return result.stdout.trim();
}

function expireProposalAndHelpSignal(handoffId: string): string {
  return runIsolatedDatabasePython(
    [
      "import sqlite3, sys",
      "from datetime import datetime, timedelta, timezone",
      "db, handoff_id = sys.argv[1:3]",
      "conn = sqlite3.connect(db)",
      "expired = (datetime.now(timezone.utc) - timedelta(minutes=1)).isoformat()",
      "row = conn.execute('SELECT signal_id FROM journey_rendezvous_buddy_handoffs WHERE id = ?', (handoff_id,)).fetchone()",
      "assert row is not None",
      "conn.execute('UPDATE journey_rendezvous_buddy_handoffs SET expires_at = ? WHERE id = ?', (expired, handoff_id))",
      "conn.execute(\"UPDATE journey_rendezvous_member_signals SET status = 'EXPIRED', expires_at = ?, updated_at = ? WHERE id = ?\", (expired, expired, row[0]))",
      "execution = conn.execute('SELECT status, expires_at FROM journey_rendezvous_buddy_executions WHERE handoff_id = ?', (handoff_id,)).fetchone()",
      "assert execution is not None and execution[0] == 'ACTIVE'",
      "conn.commit()",
      "print(execution[1])",
      "conn.close()",
    ].join("\n"),
    handoffId,
  );
}

function changeCursorForStaleConsent(journeyId: string): string {
  return runIsolatedDatabasePython(
    [
      "import sqlite3, sys",
      "from datetime import datetime, timezone",
      "db, journey_id = sys.argv[1:3]",
      "conn = sqlite3.connect(db)",
      "journey = conn.execute('SELECT active_plan_version_id, current_activity_id FROM journeys WHERE id = ?', (journey_id,)).fetchone()",
      "assert journey is not None",
      "next_activity = conn.execute('SELECT id FROM activities WHERE plan_version_id = ? AND id != ? ORDER BY sequence_no LIMIT 1', (journey[0], journey[1] or '')).fetchone()",
      "assert next_activity is not None",
      "conn.execute('UPDATE journeys SET current_activity_id = ?, updated_at = ? WHERE id = ?', (next_activity[0], datetime.now(timezone.utc).isoformat(), journey_id))",
      "conn.commit()",
      "print(next_activity[0])",
      "conn.close()",
    ].join("\n"),
    journeyId,
  );
}

function isolatedCountsAndCursor(journeyId: string): Record<string, unknown> {
  return JSON.parse(runIsolatedDatabasePython(
    [
      "import json, sqlite3, sys",
      "db, journey_id = sys.argv[1:3]",
      "conn = sqlite3.connect(db)",
      "tables = ['plan_versions', 'route_acquisition_operations', 'provider_calls', 'agent_runs', 'guardian_runs', 'guardian_pulses', 'journey_outcome_events']",
      "counts = {table: conn.execute('SELECT COUNT(*) FROM ' + table).fetchone()[0] for table in tables}",
      "journey = conn.execute('SELECT active_plan_version_id, current_activity_id FROM journeys WHERE id = ?', (journey_id,)).fetchone()",
      "assert journey is not None",
      "print(json.dumps({'counts': counts, 'active_plan_version_id': journey[0], 'current_activity_id': journey[1]}))",
      "conn.close()",
    ].join("\n"),
    journeyId,
  ));
}

test("R82 lets a signed buddy pair finish and rejoin after the offer expires", async ({ browser, request }) => {
  test.setTimeout(180_000);
  const resetToken = process.env.CITYNEXUS_DEMO_RESET_TOKEN;
  if (!resetToken) throw new Error("R82 Playwright requires the isolated-run CITYNEXUS_DEMO_RESET_TOKEN");

  const reset = await api<{ journey_id: string; traveler_id: string }>(request, "/api/v1/demo/reset", {
    method: "POST", headers: { "X-Demo-Reset-Token": resetToken },
  });
  const journeyId = reset.journey_id;
  const journeyPath = "/api/v1/journeys/" + journeyId;
  const helperId = reset.traveler_id;
  const helperToken = travelerToken(helperId);
  const plans = await api<Array<{ id: string }>>(request, journeyPath + "/plans/generate", {
    method: "POST", data: { candidate_count: 1 },
  });
  const planId = plans[0]?.id;
  if (!planId) throw new Error("R82 E2E could not generate the shared Journey plan");
  await api(request, journeyPath + "/plans/" + planId + "/select", { method: "POST", token: helperToken });
  await api(request, journeyPath + "/start", { method: "POST", token: helperToken });

  const bystander = await api<Traveler>(request, "/api/v1/travelers", {
    method: "POST", data: { display_name: "R82 Existing Bystander B", locale: "en-US", timezone: "Asia/Shanghai" },
  });
  const bystanderToken = travelerToken(bystander.id);
  await acceptInvitation(request, journeyPath, helperToken, bystanderToken, bystander.id);
  const requester = await api<Traveler>(request, "/api/v1/travelers", {
    method: "POST", data: { display_name: "R82 Help Requester C", locale: "en-US", timezone: "Asia/Shanghai" },
  });
  const requesterToken = travelerToken(requester.id);
  await acceptInvitation(request, journeyPath, helperToken, requesterToken, requester.id);

  const helper = await openPage(browser, helperToken, journeyId, { latitude: 39.9042, longitude: 116.4074, accuracy: 12 });
  const bystanderPage = await openPage(browser, bystanderToken, journeyId, { latitude: 35.6762, longitude: 139.6503, accuracy: 20 });
  const requesterPage = await openPage(browser, requesterToken, journeyId, { latitude: 31.2304, longitude: 121.4737, accuracy: 15 });
  let laterMemberPage: Awaited<ReturnType<typeof openPage>> | null = null;
  try {
    const requesterOperator = await api<{ group_presence: Presence }>(request, journeyPath + "/operator", { token: requesterToken });
    const presence = requesterOperator.group_presence;
    const target = presence.rendezvous;
    if (target.latitude === null || target.longitude === null || target.coordinate_system !== "WGS84") {
      throw new Error("R82 E2E needs an exact public WGS84 shared-stop destination");
    }

    await requesterPage.page.getByTestId("journey-rendezvous-help-share").click();
    await expect(requesterPage.page.getByTestId("journey-rendezvous-consent")).toBeVisible();
    await requesterPage.page.getByTestId("journey-rendezvous-consent-confirm").click();
    await expect(requesterPage.page.getByTestId("journey-rendezvous-status")).toContainText("self-reports needing coordination help");

    await helper.page.getByTestId("journey-rendezvous-refresh").click();
    const helpCard = helper.page.getByTestId("journey-rendezvous-status").filter({ hasText: requester.display_name });
    await expect(helpCard).toContainText("self-reports needing coordination help");
    await helpCard.getByTestId("journey-rendezvous-help-acknowledge").click();
    await expect(helpCard.getByTestId("journey-rendezvous-help-acknowledgement")).toBeVisible();

    const signalId = await helpCard.getAttribute("data-signal-id");
    if (!signalId) throw new Error("R82 E2E could not read the current signed help signal id");
    const candidates = await api<{
      active_plan_version_id: string;
      current_activity_id: string | null;
      rendezvous_activity_id: string;
      original_public_place_id: string;
      audience_sha256: string;
      items: Array<{ place_id: string; name: string }>;
    }>(request, journeyPath + "/rendezvous-buddy-handoffs/candidates?signal_id=" + signalId, { token: helperToken });
    const selected = candidates.items.find((item) => item.place_id !== target.place_id) ?? candidates.items[0];
    if (!selected) throw new Error("R82 E2E found no server-suggested public handoff place");

    await helpCard.getByTestId("journey-buddy-load-candidates").click();
    await expect(helper.page.getByTestId("journey-buddy-candidate-chooser")).toBeVisible();
    await helper.page.getByTestId("journey-buddy-candidate-select").selectOption(selected.place_id);
    await helper.page.getByTestId("journey-buddy-execution-window").selectOption("60");
    const offerResponsePromise = helper.page.waitForResponse((response) =>
      response.request().method() === "POST" && response.url().endsWith("/rendezvous-buddy-handoffs"),
    );
    await helper.page.getByTestId("journey-buddy-offer").click();
    const offerResponse = await offerResponsePromise;
    expect(offerResponse.status()).toBe(201);
    const offered = await offerResponse.json() as { handoff_id: string };
    const handoffId = offered.handoff_id;

    await requesterPage.page.getByTestId("journey-rendezvous-refresh").click();
    const handoffCard = requesterPage.page.getByTestId("journey-buddy-handoff");
    await expect(handoffCard).toContainText(selected.name);
    await expect(handoffCard.getByTestId("journey-buddy-window-offer-truth")).toContainText("60-minute");
    await handoffCard.getByTestId("journey-buddy-accept").click();
    await expect(requesterPage.page.getByTestId("journey-buddy-execution-active")).toBeVisible();
    await expect(helper.page.getByTestId("journey-rendezvous-refresh")).toBeVisible();

    const laterMember = await api<Traveler>(request, "/api/v1/travelers", {
      method: "POST", data: { display_name: "R82 Later Member D", locale: "en-US", timezone: "Asia/Shanghai" },
    });
    const laterMemberToken = travelerToken(laterMember.id);
    await acceptInvitation(request, journeyPath, helperToken, laterMemberToken, laterMember.id);
    laterMemberPage = await openPage(browser, laterMemberToken, journeyId, { latitude: 37.5665, longitude: 126.9780, accuracy: 18 });

    const activeWindowExpiry = expireProposalAndHelpSignal(handoffId);
    expect(Date.parse(activeWindowExpiry)).toBeGreaterThan(Date.now());
    for (const page of [helper.page, requesterPage.page]) {
      await page.getByTestId("journey-rendezvous-refresh").click();
      await expect(page.getByTestId("journey-buddy-execution-active")).toBeVisible();
      await expect(page.getByTestId("journey-buddy-execution-active")).toContainText("60 minutes");
    }
    await bystanderPage.page.getByTestId("journey-rendezvous-refresh").click();
    await laterMemberPage.page.getByTestId("journey-rendezvous-refresh").click();
    await expect(bystanderPage.page.getByTestId("journey-buddy-handoff")).toHaveCount(0);
    await expect(laterMemberPage.page.getByTestId("journey-buddy-handoff")).toHaveCount(0);
    expect((await api<{ items: unknown[] }>(request, journeyPath + "/rendezvous-buddy-handoffs/current", { token: bystanderToken })).items).toEqual([]);
    expect((await api<{ items: unknown[] }>(request, journeyPath + "/rendezvous-buddy-handoffs/current", { token: laterMemberToken })).items).toEqual([]);

    const helperView = helper.page.getByTestId("journey-buddy-handoff");
    const requesterView = requesterPage.page.getByTestId("journey-buddy-handoff");
    const helperAckPromise = helper.page.waitForResponse((response) =>
      response.request().method() === "POST" && response.url().includes(`/execution/`) && response.url().endsWith("/report"),
    );
    await helperView.getByTestId("journey-buddy-met-ack").click();
    const helperAck = await helperAckPromise;
    expect(helperAck.status()).toBe(200);
    await expect(helperView.getByTestId("journey-buddy-execution-active")).toContainText("Waiting");
    await expect(helperView.getByTestId("journey-buddy-return-open")).toHaveCount(0);

    const requesterAckPromise = requesterPage.page.waitForResponse((response) =>
      response.request().method() === "POST" && response.url().includes(`/execution/`) && response.url().endsWith("/report"),
    );
    await requesterView.getByTestId("journey-buddy-met-ack").click();
    const requesterAck = await requesterAckPromise;
    expect(requesterAck.status()).toBe(200);
    await expect(requesterPage.page.getByTestId("journey-buddy-mutual-outcome")).toContainText("device-verified physical reunion");
    await expect(bystanderPage.page.getByTestId("journey-buddy-handoff")).toHaveCount(0);
    await expect(laterMemberPage.page.getByTestId("journey-buddy-handoff")).toHaveCount(0);

    const factsBeforeDirections = isolatedCountsAndCursor(journeyId);
    const externalMapRequests: URL[] = [];
    await requesterPage.page.context().route("https://www.google.com/maps/**", async (route) => {
      externalMapRequests.push(new URL(route.request().url()));
      await route.fulfill({ status: 200, contentType: "text/html", body: "<!doctype html><title>Mock Maps</title>" });
    });
    await requesterPage.page.getByTestId("journey-buddy-return-open").click();
    const returnConsent = requesterPage.page.getByTestId("journey-buddy-return-directions-consent");
    await expect(returnConsent).toContainText(target.place_name);
    await expect(returnConsent).toContainText("only the WGS84 destination");
    const popupPromise = requesterPage.page.waitForEvent("popup");
    await returnConsent.getByTestId("journey-buddy-return-directions-confirm").click();
    const popup = await popupPromise;
    await popup.waitForURL((url) => url.origin === "https://www.google.com" && url.pathname === "/maps/dir/");
    const mapUrl = new URL(popup.url());
    expect(mapUrl.origin).toBe("https://www.google.com");
    expect(mapUrl.pathname).toBe("/maps/dir/");
    expect(mapUrl.searchParams.get("destination")).toBe(`${target.latitude},${target.longitude}`);
    expect(mapUrl.searchParams.get("travelmode")).toBe("walking");
    expect(mapUrl.searchParams.get("origin")).toBeNull();
    expect(externalMapRequests).toHaveLength(1);
    expect(externalMapRequests[0].searchParams.get("origin")).toBeNull();
    expect(externalMapRequests[0].searchParams.get("destination")).toBe(`${target.latitude},${target.longitude}`);
    await popup.close();

    // A consent captured for one cursor cannot release a destination after the
    // current shared Journey advances before the user confirms.
    await requesterPage.page.getByTestId("journey-buddy-return-open").click();
    await expect(requesterPage.page.getByTestId("journey-buddy-return-directions-consent")).toBeVisible();
    const changedCursor = changeCursorForStaleConsent(journeyId);
    expect(changedCursor).not.toBe(factsBeforeDirections.current_activity_id);
    await requesterPage.page.getByTestId("journey-buddy-return-directions-confirm").click();
    await expect(requesterPage.page.getByTestId("journey-buddy-return-directions-consent")).toHaveCount(0);
    await expect(requesterPage.page.getByTestId("journey-buddy-message")).toContainText("No destination was sent");
    expect(externalMapRequests).toHaveLength(1);

    const factsAfterDirections = isolatedCountsAndCursor(journeyId);
    const beforeCounts = factsBeforeDirections.counts as Record<string, number>;
    const afterCounts = factsAfterDirections.counts as Record<string, number>;
    for (const table of [
      "plan_versions", "route_acquisition_operations", "provider_calls", "agent_runs",
      "guardian_runs", "guardian_pulses", "journey_outcome_events",
    ]) {
      expect(afterCounts[table], table).toBe(beforeCounts[table]);
    }
    expect(factsAfterDirections.active_plan_version_id).toBe(factsBeforeDirections.active_plan_version_id);
    expect(factsAfterDirections.current_activity_id).toBe(changedCursor);
    const requesterOperatorAfter = await api<{ group_presence: Presence }>(request, journeyPath + "/operator", { token: requesterToken });
    expect(requesterOperatorAfter.group_presence.active_plan_version_id).toBe(presence.active_plan_version_id);
  } finally {
    await helper.close();
    await bystanderPage.close();
    await requesterPage.close();
    await laterMemberPage?.close();
  }
});
