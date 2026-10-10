import { expect, test } from "@playwright/test";
import { writeFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

/* ORD-0557 · the preventive panel's two last-resort lines.
 *
 * `V14PreventivePanel` used to print "no dominant mode" and "none on this
 * journey" itself when the server gave it nothing for those two slots.  They
 * now come from the dictionary.  Nothing here invents a response: the run is
 * produced by the product's own autopilot loop over a real backend, and the
 * case only reads what that run actually carries, then compares the glass
 * against the words the panel printed before the key existed.
 *
 * Readings land in review/预防工-0557/screen_readings_r1.txt (one line per arm).
 */

const API =
  process.env.CITYNEXUS_API_BASE_URL ??
  `http://127.0.0.1:${Number(process.env.CITYNEXUS_BACKEND_PORT ?? 8000)}`;

const HERE = dirname(fileURLToPath(import.meta.url));
const ARTIFACTS = resolve(HERE, "..", "..", "review/预防工-0557");
const READOUT = resolve(ARTIFACTS, "screen_readings_r1.txt");

const lines: string[] = [];
function note(text: string) {
  lines.push(text);
  writeFileSync(READOUT, lines.join("\n") + "\n", "utf-8");
}

/* ORD-0389 put a named operator token in front of `demo/reset`.  This invocation starts its
   own backend over a throwaway `_e2e_*.db` it created minutes earlier, so the state being
   reset here is this run's own and nobody else's; the token is read from the environment the
   backend was started with, so the spec never carries a secret of its own. */
const RESET_TOKEN = process.env.CITYNEXUS_DEMO_RESET_TOKEN ?? "";

async function api<T = any>(
  request: import("@playwright/test").APIRequestContext,
  url: string,
  method: "GET" | "POST" | "PUT",
  data?: unknown,
  headers?: Record<string, string>,
): Promise<T> {
  const options: any = data === undefined ? {} : { data };
  if (headers) options.headers = headers;
  const response =
    method === "GET"
      ? await request.get(`${API}${url}`)
      : method === "PUT"
        ? await request.put(`${API}${url}`, options)
        : await request.post(`${API}${url}`, options);
  if (!response.ok()) {
    throw new Error(
      `${method} ${url} -> HTTP ${response.status()}: ${(await response.text()).slice(0, 200)}`,
    );
  }
  return (await response.json()) as T;
}

/** Drive the product's own preventive cycle; returns the finished run. */
async function producePreventiveRun(
  request: import("@playwright/test").APIRequestContext,
  payload: Record<string, number>,
): Promise<{ journeyId: string; run: any }> {
  /* A per-spec fresh journey cannot reach `plans/generate` on a clean database (it answers
     422 VALIDATION_ERROR, "No feasible plan candidates satisfy the journey constraints"),
     so this case takes the demo stage's own journey instead. */
  const demo = await api<{ traveler_id: string; journey_id: string }>(
    request,
    "/api/v1/demo/reset",
    "POST",
    undefined,
    { "X-Demo-Reset-Token": RESET_TOKEN },
  );
  const journeyId = demo.journey_id;
  note(`demo/reset answered for journey=${String(journeyId).slice(0, 8)} token_present=${RESET_TOKEN ? "yes" : "no"}`);
  await api(request, `/api/v1/travelers/${demo.traveler_id}/agent-policy`, "PUT", {
    mode: "AUTONOMOUS",
    auto_accept_replan: true,
    max_auto_replan_cost_delta_minor: 5000,
    max_auto_loss_minor: 0,
    max_auto_schedule_drift_min: 120,
    allowed_activity_types: ["transport", "visit"],
    allowed_booking_types: [],
    protected_commitment_levels: ["C3_Guaranteed", "C4_Anchored"],
    allow_auto_commitment_management: false,
    allow_auto_when_provider_degraded: false,
    allow_auto_on_critical_event: false,
  });
  const plans = await api<{ id: string }[]>(
    request,
    `/api/v1/journeys/${journeyId}/plans/generate`,
    "POST",
    { candidate_count: 1 },
  );
  if (!plans.length) throw new Error(`plans/generate returned no plan for ${journeyId}`);
  await api(request, `/api/v1/journeys/${journeyId}/plans/${plans[0].id}/select`, "POST");
  /* No commitment is protected on purpose: the panel's second last-resort line is
     the one that reads "none on this journey", and it only appears when the
     active plan carries nothing protected. */
  await api(request, `/api/v1/journeys/${journeyId}/start`, "POST");
  await api(request, `/api/v1/journeys/${journeyId}/guardian/mission`, "PUT", {
    command: "Prefer a calm route, keep the day inside the envelope.",
    requested_autonomy: "EXECUTE_WITHIN_BOUNDS",
  });
  await api(request, `/api/v1/journeys/${journeyId}/guardian/provider-fixture`, "POST", {
    state: "RISK_FORECAST",
    payload,
  });
  await api(request, `/api/v1/journeys/${journeyId}/guardian/autopilot/start`, "POST", {
    interval_seconds: 0.5,
  });
  let finished: any = null;
  await expect
    .poll(
      async () => {
        const status = await api<{ runs: any[] }>(
          request,
          `/api/v1/journeys/${journeyId}/guardian/status`,
          "GET",
        );
        finished =
          (status.runs ?? []).find(
            (item) =>
              item.decision === "PREEMPTIVE_RECOVERY" &&
              item.trigger_kind === "PREDICTIVE" &&
              item.status === "COMPLETED",
          ) ?? null;
        return Boolean(finished);
      },
      { message: "the autopilot never completed a preventive run", timeout: 90_000, intervals: [1000] },
    )
    .toBe(true);
  await api(request, `/api/v1/journeys/${journeyId}/guardian/autopilot/stop`, "POST", {});
  return { journeyId, run: finished };
}

/* Two fixture states, because the two slots go empty for different reasons: the delayed
   forecast leaves a failure mode on the run, so only the protected-commitment slot reads a
   last-resort line; a forecast with no route delay and no weather signal leaves no dominant
   mode at all, which is what puts the first one on the glass. */
const STATES = [
  { name: "with-delay", payload: { risk_score: 88, forecast_horizon_min: 45, expected_route_delay_min: 18 } },
  { name: "no-signal", payload: { risk_score: 88, forecast_horizon_min: 45, expected_route_delay_min: 0 } },
];

for (const state of STATES) {
  for (const locale of ["en", "zh"] as const) {
    test(`${state.name} / ${locale}: the two last-resort slots read the dictionary words`, async ({ page, request }) => {
    test.setTimeout(240_000);
    const { journeyId, run } = await producePreventiveRun(request, state.payload);

    const modes = (run?.evidence?.prediction?.dominant_failure_modes ?? null) as unknown[] | null;
    const protectedCount = (run?.evidence ?? {}).protected ?.length ?? null;
    note(
      `[${state.name}/${locale}] run=${String(run?.id ?? "").slice(0, 8)} journey=${String(journeyId).slice(0, 8)} ` +
        `dominant_failure_modes=${modes === null ? "absent" : `array len ${modes.length}`} ` +
        `protected_in_run_evidence=${protectedCount === null ? "no such field" : protectedCount}`,
    );

    await page.addInitScript(
      ({ id, loc }) => {
        localStorage.setItem("citynexus.locale", loc);
        localStorage.setItem("citynexus.v8.journey_id", id);
        localStorage.setItem("citynexus.demo.journey_id", id);
      },
      { id: journeyId, loc: locale },
    );
    await page.setViewportSize({ width: 1280, height: 900 });
    await page.goto("/v8/authoritative");

    const evidence = page.getByTestId("v14-preventive-evidence");
    const protectedLine = page.getByTestId("v14-preventive-protected");
    await expect(evidence).toBeVisible({ timeout: 30_000 });

    const evidenceText = (await evidence.textContent()) ?? "";
    const protectedText = (await protectedLine.textContent()) ?? "";
    note(`[${state.name}/${locale}] v14-preventive-evidence textContent = ${JSON.stringify(evidenceText)}`);
    note(
      `[${state.name}/${locale}] v14-preventive-protected textContent = ${JSON.stringify(protectedText)} ` +
        `data-count=${JSON.stringify(await protectedLine.getAttribute("data-count"))}`,
    );
    await page
      .getByTestId("v14-preventive")
      .screenshot({ path: resolve(ARTIFACTS, `${state.name}_${locale}_r1.png`) });
    note(`[${state.name}/${locale}] screenshot = review/预防工-0557/${state.name}_${locale}_r1.png`);

    /* Each expectation is computed from what the server actually returned, so the same case
       reads the glass before the move and after it and demands the same words. */
    const expectedEvidenceTail =
      modes && modes.length
        ? modes
            .slice(0, 2)
            .map((m: any) => m?.label ?? m?.place_id ?? "?")
            .join(", ")
        : "no dominant mode";
    await expect(evidence).toContainText(expectedEvidenceTail);
    expect(evidenceText.trimEnd().endsWith(expectedEvidenceTail)).toBe(true);
    note(
      `[${state.name}/${locale}] arm 196 expected tail ${JSON.stringify(expectedEvidenceTail)}; ` +
        `glass read ${JSON.stringify(evidenceText)}`,
    );

    const count = Number(await protectedLine.getAttribute("data-count"));
    const expectedProtected = count ? `${count} preserved` : "none on this journey";
    await expect(protectedLine).toContainText(expectedProtected);
    note(
      `[${state.name}/${locale}] arm 228 expected ${JSON.stringify(expectedProtected)} ` +
        `(data-count=${count}); glass read ${JSON.stringify(protectedText)}`,
    );
    });
  }
}
