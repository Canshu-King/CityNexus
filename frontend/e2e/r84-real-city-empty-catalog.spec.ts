import { createHmac } from "node:crypto";
import { expect, test, type APIRequestContext, type Browser } from "@playwright/test";

const API = `http://127.0.0.1:${Number(process.env.CITYNEXUS_BACKEND_PORT ?? 8000)}`;

function travelerToken(travelerId: string): string {
  const secret = process.env.CITYNEXUS_TRAVELER_AUTH_SECRET;
  if (!secret || Buffer.byteLength(secret, "utf8") < 32) {
    throw new Error("R84 requires CITYNEXUS_TRAVELER_AUTH_SECRET of at least 32 bytes");
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

test("R84 exposes a public shared-stop fallback when foreground location is unavailable", async ({ browser, request }) => {
  const resetToken = process.env.CITYNEXUS_DEMO_RESET_TOKEN;
  if (!resetToken) throw new Error("R84 requires CITYNEXUS_DEMO_RESET_TOKEN");
  const reset = await api<{ journey_id: string; traveler_id: string }>(request, "/api/v1/demo/reset", {
    method: "POST",
    headers: { "X-Demo-Reset-Token": resetToken },
  });
  const journeyId = reset.journey_id;
  const ownerToken = travelerToken(reset.traveler_id);
  const plans = await api<Array<{ id: string }>>(request, `/api/v1/journeys/${journeyId}/plans/generate`, {
    method: "POST",
    data: { candidate_count: 1 },
  });
  expect(plans.length).toBeGreaterThan(0);
  await api(request, `/api/v1/journeys/${journeyId}/plans/${plans[0].id}/select`, { method: "POST", token: ownerToken });
  await api(request, `/api/v1/journeys/${journeyId}/start`, { method: "POST", token: ownerToken });
  await api(request, `/api/v1/journeys/${journeyId}/operator/start`, {
    method: "POST",
    token: ownerToken,
    data: { interval_seconds: 3600 },
  });

  const context = await browser.newContext();
  const page = await context.newPage();
  await page.addInitScript(({ id, bearer }) => {
    localStorage.setItem("citynexus.v8.journey_id", id);
    localStorage.setItem("citynexus.locale", "en-US");
    sessionStorage.setItem("citynexus.traveler.bearer", bearer);
  }, { id: journeyId, bearer: ownerToken });
  try {
    await page.goto("/v8/live", { waitUntil: "domcontentloaded" });
    const card = page.getByTestId("moment-scout");
    await expect(card).toBeVisible();
    await card.getByTestId("moment-scout-live-opt-in").click();
    await card.getByTestId("moment-scout-live-consent-confirm").click();
    await expect(card.getByTestId("moment-scout-live-results")).toHaveAttribute("data-state", "LOCATION_UNAVAILABLE");
    const fallback = card.getByTestId("moment-scout-shared-stop-fallback");
    await expect(fallback).toBeVisible();
    await expect(fallback).toContainText("Only the public shared-stop coordinates are sent");

    await page.context().route("https://www.google.com/maps/**", (route) => route.fulfill({
      status: 200,
      contentType: "text/html",
      body: "<!doctype html><title>Maps fixture</title>",
    }));
    const popupPromise = page.waitForEvent("popup");
    await fallback.getByTestId("moment-scout-shared-stop-google").click();
    const popup = await popupPromise;
    await expect.poll(() => new URL(popup.url()).hostname).toBe("www.google.com");
    const target = new URL(popup.url());
    expect(target.pathname).toBe("/maps/dir/");
    expect(target.searchParams.get("travelmode")).toBe("walking");
    expect(target.searchParams.get("dir_action")).toBe("navigate");
    expect(target.searchParams.has("origin")).toBe(false);
    await popup.close();
    await page.context().unroute("https://www.google.com/maps/**");
  } finally {
    await context.close();
  }
});
