/**
 * The staging both slice-1 gates share: the journey this run's own seed built, a traveller's token
 * minted the way this branch's door signs it, and a page opened as one identity.
 *
 * Extracted rather than copied because two specs now drive the same fixture -- the four behaviour
 * arms (`qoder-ord0510-ported-faces-answer-the-doors.spec.ts`) and the saved 390x844 walkthrough
 * (`qoder-ord0510-walk-390x844.spec.ts`).  A copy would let the two drift into proving different
 * journeys while reading like the same one.
 *
 * Identity is one browser context per traveller.  The seed of each page is an `addInitScript`, which
 * replays on every navigation, so switching a bearer inside one tab would be silently undone by the
 * next `goto`.
 */
import { createHmac } from "node:crypto";
import { expect, type APIRequestContext, type Browser, type Page } from "@playwright/test";

export const FILE_DIR = "e2e";
export const VIEWPORT = { width: 390, height: 844 };
export const API = `http://127.0.0.1:${Number(process.env.CITYNEXUS_BACKEND_PORT ?? 8000)}`;

/** The token this branch's own door accepts, minted from the per-run test secret (the r73 idiom). */
export function tokenFor(travelerId: string): string {
  const secret = process.env.CITYNEXUS_TRAVELER_AUTH_SECRET;
  if (!secret || Buffer.byteLength(secret, "utf8") < 32) {
    throw new Error("these gates need a per-run CITYNEXUS_TRAVELER_AUTH_SECRET of at least 32 bytes");
  }
  const iat = Math.floor(Date.now() / 1000);
  const body = Buffer.from(
    JSON.stringify({ aud: "citynexus-traveler", exp: iat + 3600, iat, sub: travelerId, v: 1 }),
  ).toString("base64url");
  return `${body}.${createHmac("sha256", secret).update(body, "ascii").digest("base64url")}`;
}

export async function ask<T = any>(
  request: APIRequestContext,
  method: "GET" | "POST",
  path: string,
  options: { token?: string; data?: unknown } = {},
): Promise<T> {
  const headers = options.token ? { Authorization: `Bearer ${options.token}` } : undefined;
  const res =
    method === "GET"
      ? await request.get(`${API}${path}`, { headers })
      : await request.post(`${API}${path}`, { data: options.data, headers });
  const text = await res.text();
  if (!res.ok()) throw new Error(`${method} ${path} -> ${res.status()}: ${text.slice(0, 240)}`);
  return JSON.parse(text) as T;
}

export type Stage = {
  journeyId: string;
  travelerId: string;
  timezone: string;
  token: string;
  placeIds: string[];
};

/** The journey this run's own seed built: located stops, one selected plan, a trip timezone. */
export async function stage(request: APIRequestContext, who: string): Promise<Stage> {
  const scene = await ask(request, "GET", "/api/v1/demo/scene");
  const journeyId = String(scene.journey_id ?? "");
  expect(journeyId.length > 0, `${who} :: the seed named no journey`).toBe(true);
  const journey = await ask(request, "GET", `/api/v1/journeys/${journeyId}`);
  const experience = await ask(request, "GET", `/api/v1/journeys/${journeyId}/experience`);
  const activities: any[] = experience?.active_plan?.activities ?? [];
  expect(activities.length, `${who} :: this journey has no plan to stamp`).toBeGreaterThan(0);
  const travelerId = String(journey.traveler_id ?? "");
  expect(travelerId.length > 0, `${who} :: the journey names no traveller`).toBe(true);
  return {
    journeyId,
    travelerId,
    timezone: String(journey.timezone ?? ""),
    token: tokenFor(travelerId),
    placeIds: activities.map((a) => String(a.place_id ?? "")).filter(Boolean),
  };
}

/**
 * Open the shell as one traveller and hand back the URL list as the page asked it.
 * The bearer is written before the first script runs, so the screen's own read is its first request.
 */
export async function openAs(
  browser: Browser,
  s: Stage,
  token: string | null,
  route: string,
): Promise<{ page: Page; asked: string[]; close: () => Promise<void> }> {
  const context = await browser.newContext({ viewport: VIEWPORT, hasTouch: true });
  const page = await context.newPage();
  const asked: string[] = [];
  page.on("request", (r) => asked.push(r.url()));
  await page.addInitScript(
    ({ id, bearer }) => {
      localStorage.setItem("citynexus.v8.journey_id", id);
      localStorage.setItem("citynexus.locale", "zh-CN");
      if (bearer) sessionStorage.setItem("citynexus.traveler.bearer", bearer);
      else sessionStorage.removeItem("citynexus.traveler.bearer");
    },
    { id: s.journeyId, bearer: token },
  );
  await page.goto(route, { waitUntil: "load", timeout: 90_000 });
  return { page, asked, close: () => context.close() };
}

export const flat = (s: string) => s.replace(/\s+/g, " ");
export const checkinsPath = (journeyId: string) =>
  `/api/v1/journeys/${encodeURIComponent(journeyId)}/checkins`;
