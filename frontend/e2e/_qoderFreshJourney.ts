import { type APIRequestContext } from "@playwright/test";

/**
 * Per-spec journey isolation (pass-9 TEST_INFRA_ISOLATION_BLOCKER).
 *
 * The suite shares one backend and one SQLite file. A global seed can therefore
 * only ever be a *default*: any spec that resets the demo, selects a different
 * option, or accepts a proposal changes what the next spec sees, which is why
 * three v10 specs pass in nine seconds alone and fail inside the serial run.
 * Reordering or retrying would just be Playwright feng shui.
 *
 * The fix is ownership: a spec that depends on journey state creates its own and
 * carries its own id, exactly as `v13-5-fully-grounded` and
 * `real-world-trip-operations-v9` already do. This helper is that pattern in one
 * place, built only from public product endpoints — no SQL, no mocked routes.
 */
export type FreshJourney = { journeyId: string; optionCount: number; optionId: string | null };

const API =
  process.env.CITYNEXUS_API_BASE_URL ??
  `http://127.0.0.1:${Number(process.env.CITYNEXUS_BACKEND_PORT ?? 8000)}`;

async function post(request: APIRequestContext, url: string, data?: unknown) {
  const res = await request.post(`${API}${url}`, { data });
  if (!res.ok()) {
    throw new Error(`${url} -> HTTP ${res.status()}: ${(await res.text()).slice(0, 180)}`);
  }
  return res.json();
}

async function get(request: APIRequestContext, url: string) {
  const res = await request.get(`${API}${url}`);
  if (!res.ok()) throw new Error(`${url} -> HTTP ${res.status()}`);
  return res.json();
}

/**
 * Two nights in Tianjin, because a one-day trip makes the stay-aware optimiser
 * return zero options and silently turns every downstream assertion into a test
 * of an empty screen.
 */
export async function createFreshJourney(
  request: APIRequestContext,
  opts: { select?: boolean } = {},
): Promise<FreshJourney> {
  const traveler = await post(request, "/api/v1/travelers", {
    display_name: "Qoder per-spec traveller",
    locale: "en-GB",
    timezone: "Asia/Shanghai",
  });
  const journey = await post(request, "/api/v1/journeys", {
    traveler_id: traveler.id,
    title: "Tianjin · per-spec weekend",
    city_code: "CN-TIANJIN",
    timezone: "Asia/Shanghai",
    start_at: "2026-10-09T18:00:00+08:00",
    end_at: "2026-10-11T15:00:00+08:00",
    budget: { amount_minor: 120000, currency: "CNY" },
  });

  let optionCount = 0;
  let optionId: string | null = null;
  if (opts.select !== false) {
    await post(request, `/api/v1/journeys/${journey.id}/stay-options/generate`);
    const listed = await get(request, `/api/v1/journeys/${journey.id}/stay-options`);
    const options = listed.options ?? [];
    optionCount = options.length;
    if (optionCount) {
      const chosen = options.find((o: any) => o.status === "RECOMMENDED") ?? options[0];
      optionId = chosen.id;
      await post(request, `/api/v1/journeys/${journey.id}/stay-options/${chosen.id}/select`);
    }
  }

  return { journeyId: journey.id, optionCount, optionId };
}

/** Carry a spec's own journey into the browser, overriding any shared seed. */
export async function useJourney(page: import("@playwright/test").Page, journeyId: string) {
  await page.addInitScript((id) => {
    localStorage.setItem("citynexus.v8.journey_id", id);
    localStorage.setItem("citynexus.demo.journey_id", id);
  }, journeyId);
}
