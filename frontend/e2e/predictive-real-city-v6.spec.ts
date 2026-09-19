import { expect, test } from "@playwright/test";

/* PORT-FIRST (pass-15 D) — prevention, not detection, and not recovery-after-the-fact.
 *
 * `v13-5-fully-grounded` already proves grounded discovery and that a weakness can
 * be *seen*.  What this case must still prove is the half nothing else covers:
 * CityNexus acts before the failure happens, and the traveller can see why.
 *
 * So the assertions are deliberately shaped as:
 *   - no hard failure exists at the moment of action (checked, not assumed);
 *   - a forecast pulse alone produces a preventive run, with predictive evidence;
 *   - the plan really changes, and locked commitments stay intact;
 *   - nobody clicked anything (a scan request would make this reactive, not predictive);
 *   - the current product surface explains it.
 *
 * The last bullet is where this test is expected to fail today, and it is left
 * failing on purpose.  The backend implements preventive recovery end to end
 * (`decision=PREEMPTIVE_RECOVERY`, `trigger_kind=PREDICTIVE`, evidence carries
 * `forecast_before_hard_failure`), but every guardian testid that renders it —
 * `guardian-decision`, `guardian-predictive-resilience`, `guardian-provenance`,
 * `guardian-trace` — exists only in `src/main.tsx`, i.e. the legacy surface under
 * `/legacy`.  Nothing in V8 owns the result.  Per the ruling, that is reported as
 * a product integration gap by a red test rather than converted into a
 * backend-only green one, and it must not be "fixed" by relabelling a reactive
 * recovery as prevention.
 */

const API =
  process.env.CITYNEXUS_API_BASE_URL ??
  `http://127.0.0.1:${Number(process.env.CITYNEXUS_BACKEND_PORT ?? 8000)}`;

async function api<T>(
  request: import("@playwright/test").APIRequestContext,
  url: string,
  method: "GET" | "POST" | "PUT",
  data?: unknown,
): Promise<T> {
  const options = data === undefined ? {} : { data };
  const response =
    method === "GET"
      ? await request.get(`${API}${url}`, { headers: { "Content-Type": "application/json" } })
      : method === "PUT"
        ? await request.put(`${API}${url}`, { ...options, headers: { "Content-Type": "application/json" } })
        : await request.post(`${API}${url}`, { ...options, headers: { "Content-Type": "application/json" } });
  if (!response.ok()) {
    throw new Error(
      `${method} ${url} -> HTTP ${response.status()}: ${(await response.text()).slice(0, 220)}`,
    );
  }
  return (await response.json()) as T;
}

type GuardianRun = {
  decision: string;
  status: string;
  action_status: string;
  trigger_kind: string | null;
  reasoning_summary?: string | null;
  active_plan_before_id: string | null;
  active_plan_after_id: string | null;
  evidence?: {
    observation?: { trigger_kind?: string; forecast_before_hard_failure?: boolean };
    prediction?: { weakness?: string | null; score?: number | null } & Record<string, unknown>;
    inference?: { decision?: string; reason?: string };
  };
};

test("a forecast is prevented before the failure happens, and the traveller can see why", async ({
  page,
  request,
}) => {
  test.setTimeout(150_000);
  await page.addInitScript(() => localStorage.setItem("citynexus.locale", "en"));

  const demo = await api<{ traveler_id: string; journey_id: string }>(
    request,
    "/api/v1/demo/reset",
    "POST",
  );
  const journeyId = demo.journey_id;

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

  const plans = await api<{ id: string; activities: { id: string; place_id: string | null; title: string }[] }[]>(
    request,
    `/api/v1/journeys/${journeyId}/plans/generate`,
    "POST",
    { candidate_count: 1 },
  );
  await api(request, `/api/v1/journeys/${journeyId}/plans/${plans[0].id}/select`, "POST");
  await api(request, `/api/v1/journeys/${journeyId}/start`, "POST");
  const mission = await api<{ status: string }>(
    request,
    `/api/v1/journeys/${journeyId}/guardian/mission`,
    "PUT",
    {
      command:
        "Keep the cruise and dinner protected, prefer indoor alternatives, allow autonomous reversible recovery.",
      requested_autonomy: "EXECUTE_WITHIN_BOUNDS",
    },
  );
  expect(mission.status).toBe("ACTIVE");
  await api(
    request,
    `/api/v1/journeys/${journeyId}/guardian/autopilot/start`,
    "POST",
    { interval_seconds: 0.5 },
  );

  const before = await api<{ active_plan: { id: string } }>(
    request,
    `/api/v1/journeys/${journeyId}/experience`,
    "GET",
  );

  /* "Before the failure" has to be a measured fact.  A hard failure here means a
     CLOSURE or CRITICAL event on the journey; none is injected in this test, and
     the assertion proves the preventive action was not a reaction to something
     that had already gone wrong. */
  const eventsBefore = await api<{ event_type: string; severity: string }[]>(
    request,
    `/api/v1/journeys/${journeyId}/events`,
    "GET",
  );
  const hardFailures = eventsBefore.filter((e) =>
    /CLOSURE/.test(e.event_type) || e.severity === "CRITICAL",
  );
  expect(
    hardFailures.length,
    "a hard failure already exists on this journey, so anything after it is recovery, not prevention",
  ).toBe(0);

  /* A scan request would mean the test asked for the decision, which is exactly
     what makes a case reactive. */
  let scanRequests = 0;
  page.on("request", (entry) => {
    if (entry.url().endsWith("/guardian/scan")) scanRequests += 1;
  });

  const fixture = await api<{ state: string }>(
    request,
    `/api/v1/journeys/${journeyId}/guardian/provider-fixture`,
    "POST",
    { state: "RISK_FORECAST", payload: {} },
  );
  expect(fixture.state).toBe("RISK_FORECAST");

  let preventive: GuardianRun | null = null;
  await expect
    .poll(
      async () => {
        const status = await api<{ runs: GuardianRun[] }>(
          request,
          `/api/v1/journeys/${journeyId}/guardian/status`,
          "GET",
        );
        preventive =
          status.runs.find(
            (run) => run.decision === "PREEMPTIVE_RECOVERY" && run.trigger_kind === "PREDICTIVE",
          ) ?? null;
        return preventive !== null;
      },
      {
        message:
          "no PREEMPTIVE_RECOVERY run appeared from a forecast alone — the backend does not perform " +
          "autonomous prevention, which is a capability gap rather than a surface gap",
        timeout: 60_000,
        intervals: [1000],
      },
    )
    .toBe(true);

  const run = preventive as unknown as GuardianRun;
  expect(run.action_status, "the preventive run never executed").toBe("EXECUTED");
  expect(run.evidence?.observation?.forecast_before_hard_failure, "the run does not claim to be pre-failure")
    .toBe(true);
  expect(run.active_plan_after_id, "the preventive action left no plan identity behind").toBeTruthy();
  expect(
    run.active_plan_before_id,
    "the preventive run did not record which plan it moved away from",
  ).toBe(before.active_plan.id);

  const after = await api<{ active_plan: { id: string; activities?: { title?: string }[] } }>(
    request,
    `/api/v1/journeys/${journeyId}/experience`,
    "GET",
  );
  expect(after.active_plan.id, "the authoritative plan did not change after prevention")
    .not.toBe(before.active_plan.id);
  expect(
    (after.active_plan.activities ?? []).some((a) => /river cruise/i.test(String(a.title ?? ""))),
    "the protected River Cruise commitment was spent by a preventive action",
  ).toBe(true);

  expect(scanRequests, "the test itself asked for the decision, so this is not zero-touch").toBe(0);
  console.log(
    `[prevention] decision=${run.decision} trigger=${run.trigger_kind} action=${run.action_status} ` +
      `plan ${before.active_plan.id} -> ${after.active_plan.id} with no hard failure on the journey ` +
      `and ${scanRequests} scan requests`,
  );

  /* The traveller has to be able to see it.  This is the missing link: the run
     exists, the plan changed, and no V8 surface renders a preventive recovery —
   */
  await page.addInitScript((id) => {
    localStorage.setItem("citynexus.v8.journey_id", id);
    localStorage.setItem("citynexus.demo.journey_id", id);
  }, journeyId);
  await page.setViewportSize({ width: 1280, height: 900 });
  await page.goto("/v8/authoritative");
  await expect(page.getByTestId("v14-recovery-truth")).toBeVisible();
  await expect(
    page.locator("body"),
    "PRODUCT INTEGRATION GAP: the backend prevented a failure (PREEMPTIVE_RECOVERY / " +
      "trigger_kind=PREDICTIVE / forecast_before_hard_failure=true) and changed the authoritative " +
      "plan, but no current V8 surface says so. The only components that render a preventive " +
      "recovery are guardian-decision / guardian-predictive-resilience / guardian-provenance / " +
      "guardian-trace, and all of them exist solely in src/main.tsx behind /legacy. " +
      "Fix by giving V8 an owner for the preventive result — do not turn this test into a " +
      "backend-only assertion, and do not relabel a reactive recovery as prevention.",
  ).toContainText(/PREEMPTIVE|predictive|before it happened|forecast/i);
});
