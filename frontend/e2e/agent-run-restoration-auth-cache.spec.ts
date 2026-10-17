import { expect, test } from "@playwright/test";

const journeyId = "journey-agent-run-restore-fixture";
const runId = "run-agent-run-restore-fixture";
const bearer = "agent-run-restore-fixture-token";

test("getAgentRun uses the traveler bearer and disables response caching", async ({ page }) => {
  const targetPath = `/api/v1/journeys/${journeyId}/agent/runs/${runId}`;

  await page.route("**/api/v1/**", async (route) => {
    const requestUrl = new URL(route.request().url());
    if (requestUrl.pathname === targetPath) {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          run_id: runId,
          mission_id: "mission-agent-run-restore-fixture",
          journey_id: journeyId,
          provider_key: "TEST_PROVIDER",
          model_key: "fixture-model",
          status: "COMPLETED",
          outcome: null,
          failure_reason: null,
          tool_steps: [],
        }),
      });
      return;
    }

    await route.fulfill({ status: 200, contentType: "application/json", body: "{}" });
  });

  await page.goto("/");
  const result = await page.evaluate(async ({ journeyId, runId, bearer }) => {
    window.sessionStorage.setItem("citynexus.traveler.bearer", bearer);

    const targetPath = `/api/v1/journeys/${journeyId}/agent/runs/${runId}`;
    const originalFetch = window.fetch;
    let observedRequest: { cache: RequestCache | null; authorization: string | null } | null = null;

    window.fetch = (input, init) => {
      const inputUrl = input instanceof Request ? input.url : input.toString();
      if (new URL(inputUrl, window.location.href).pathname === targetPath) {
        observedRequest = {
          cache: init?.cache ?? null,
          authorization: new Headers(init?.headers).get("Authorization"),
        };
      }
      return originalFetch(input, init);
    };

    try {
      const { cityNexusApi } = await import("/src/api/citynexus.ts");
      const run = await cityNexusApi.getAgentRun(journeyId, runId);
      return { runId: run.run_id, request: observedRequest };
    } finally {
      window.fetch = originalFetch;
    }
  }, { journeyId, runId, bearer });

  expect(result.runId).toBe(runId);
  expect(result.request).toEqual({
    cache: "no-store",
    authorization: `Bearer ${bearer}`,
  });
});
