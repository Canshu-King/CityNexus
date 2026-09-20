import { expect, test, type Page } from "@playwright/test";
import { writeFileSync } from "node:fs";
import { ensureDemoJourney, openScreen } from "./_qoderShellSeed";
import { evidencePath } from "./_qoderEvidence";

/**
 * ORD-0038 — "is it thinking, or is it stuck?"
 *
 * The sheet used to advance a four-row checklist from a 1200ms `setInterval`.  Nothing in
 * that list was a signal: `POST /agent/commands` is synchronous and reports no phase while
 * it works, so the ✓ marks asserted backend work nobody had told us about.  A fake progress
 * bar is worse than none, because it makes people believe the system is working.
 *
 * What is asserted here instead is only what the component can prove: the seconds that
 * really elapsed, the phase it is genuinely awaiting, that cancel aborts the request rather
 * than hiding the panel, that a refused/failed request cannot be answered by the fallback
 * re-plan, and that the AI pre-flight says "unknown" when the status endpoint does not
 * answer.
 *
 * The model itself is switched off in every environment this lane may test in
 * (`CITYNEXUS_AI_ENABLED=false`), so the request is held open by the harness to stand in
 * for a slow model.  That is a substitute for *latency*, never for a real AI result: the
 * "AI actually produced plans" walk is reported as not-doable here, not as passing.
 */

const COMMANDS = "**/api/v1/journeys/*/agent/commands";
const STATUS = "**/api/v1/agent/runtime-status";
const GENERATE = "**/api/v1/journeys/*/plans/generate";
const REQUEST_TEXT = "带爸妈去厦门三天，不要走太多路，酒店要靠近地铁。";

async function openSheet(page: Page) {
  await ensureDemoJourney(page);
  await openScreen(page, "/v8/hub", ["today-heading", "today-attention"]);
  await page.getByTestId("hub-plan-with-ai").click();
  await expect(page.getByTestId("plan-ai-sheet")).toBeVisible({ timeout: 15_000 });
  await page.getByTestId("plan-ai-input").fill(REQUEST_TEXT);
}

/** Holds the command request open so a slow model can be waited on without spending 29s. */
function holdCommands(page: Page) {
  let release: (() => void) | null = null;
  const gate = new Promise<void>((resolve) => {
    release = resolve;
  });
  void page.route(COMMANDS, async (route) => {
    await gate;
    // Never answer: the traveller is meant to be able to walk away from this.
    void route.abort();
  });
  void page.route(STATUS, (route) =>
    route.fulfill({ status: 200, contentType: "application/json", body: '{"deepseek_configured":true}' }),
  );
  return { release: () => release?.() };
}

test.describe("ORD-0038 the AI sheet reports what it actually knows", () => {
  test("plan-ai-elapsed-ticks — the waiting number is measured time, not a timer position", async ({
    page,
  }) => {
    test.setTimeout(150_000);
    await page.emulateMedia({ colorScheme: "light", media: "screen" });
    await page.setViewportSize({ width: 390, height: 844 });
    const held = holdCommands(page);
    await openSheet(page);
    await page.getByTestId("plan-ai-submit").click();

    const live = page.getByTestId("plan-ai-live");
    await expect(live).toBeVisible({ timeout: 15_000 });
    const first = Number(await live.getAttribute("data-elapsed-seconds"));
    await expect
      .poll(
        async () => Number(await page.getByTestId("plan-ai-live").getAttribute("data-elapsed-seconds")),
        { timeout: 12_000, message: "the elapsed counter never advanced" },
      )
      .toBeGreaterThan(first);
    const later = Number(await page.getByTestId("plan-ai-live").getAttribute("data-elapsed-seconds"));
    const rendered = (await page.getByTestId("plan-ai-elapsed").innerText()).trim();

    expect(
      Number.isFinite(first) && Number.isFinite(later) && later > first,
      "e2e/qoder-plan-ai-thinking.spec.ts :: plan-ai-elapsed-ticks — the seconds rendered on the " +
        `sheet did not advance (${first} -> ${later}); a waiting state that never moves is the ` +
        `"is it stuck?" report`,
    ).toBe(true);
    expect(
      /\d/.test(rendered),
      "e2e/qoder-plan-ai-thinking.spec.ts :: plan-ai-elapsed-ticks — the line is rendered but " +
        `carries no number: ${JSON.stringify(rendered)}`,
    ).toBe(true);
    held.release();
  });

  test("plan-ai-no-fabricated-stage — no step may claim done before it was awaited", async ({
    page,
  }) => {
    test.setTimeout(150_000);
    await page.emulateMedia({ colorScheme: "light", media: "screen" });
    await page.setViewportSize({ width: 390, height: 844 });
    const held = holdCommands(page);
    await openSheet(page);
    await page.getByTestId("plan-ai-submit").click();
    await expect(page.getByTestId("plan-ai-live")).toBeVisible({ timeout: 15_000 });
    // Stay in the request phase: nothing after it has happened yet.
    await page.waitForTimeout(2500);

    const rows = await page
      .getByTestId("plan-ai-steps")
      .evaluate((list) =>
        Array.from(list.querySelectorAll("li")).map((li) => ({
          phase: li.getAttribute("data-phase") ?? "",
          state: li.getAttribute("data-phase-state") ?? "",
        })),
      );
    const phases = (wanted: string) => rows.filter((row) => row.state === wanted).map((row) => row.phase);

    expect(
      rows.length,
      "e2e/qoder-plan-ai-thinking.spec.ts :: plan-ai-no-fabricated-stage — no phase list to read",
    ).toBeGreaterThan(0);
    expect(
      phases("done"),
      "e2e/qoder-plan-ai-thinking.spec.ts :: plan-ai-no-fabricated-stage — while the request is " +
        `still in flight only the baseline read has really finished, but these claim done: ` +
        `${JSON.stringify(phases("done"))}. The old sheet ticked a ✓ every 1.2s with no signal behind it`,
    ).toEqual(["baseline"]);
    expect(
      phases("active"),
      "e2e/qoder-plan-ai-thinking.spec.ts :: plan-ai-no-fabricated-stage — exactly one row may be " +
        "current, and it must be the request",
    ).toEqual(["request"]);
    expect(
      phases("pending"),
      "e2e/qoder-plan-ai-thinking.spec.ts :: plan-ai-no-fabricated-stage — verification has not " +
        "started, so its row must still be pending",
    ).toEqual(["verify"]);
    expect(
      rows.map((row) => row.phase),
      "e2e/qoder-plan-ai-thinking.spec.ts :: plan-ai-no-fabricated-stage — the fallback re-plan row " +
        "rendered before it ran, which is a step the run never took",
    ).not.toContain("fallback");
    held.release();
  });

  test("plan-ai-cancel-aborts-request — cancel stops the request, and says what it cannot undo", async ({
    page,
  }) => {
    test.setTimeout(150_000);
    await page.emulateMedia({ colorScheme: "light", media: "screen" });
    await page.setViewportSize({ width: 390, height: 844 });
    void page.route(STATUS, (route) =>
      route.fulfill({ status: 200, contentType: "application/json", body: '{"deepseek_configured":true}' }),
    );
    const failures: string[] = [];
    page.on("requestfailed", (request) => {
      if (request.url().includes("/agent/commands")) failures.push(request.failure()?.errorText ?? "?");
    });
    await page.route(COMMANDS, async (route) => {
      await new Promise<void>((resolve) => setTimeout(resolve, 20_000));
      void route.fulfill({ status: 200, contentType: "application/json", body: "{}" });
    });
    await openSheet(page);
    await page.getByTestId("plan-ai-submit").click();
    await expect(page.getByTestId("plan-ai-cancel")).toBeVisible({ timeout: 15_000 });
    await page.getByTestId("plan-ai-cancel").click();

    const result = page.getByTestId("plan-ai-result");
    await expect(result).toBeVisible({ timeout: 15_000 });
    await expect
      .poll(() => failures.length, { timeout: 10_000, message: "the browser never aborted the request" })
      .toBeGreaterThan(0);
    const rendered = (await result.innerText()).replace(/\s+/g, " ").trim();
    const status = await result.getAttribute("data-result-status");
    const tone = await result.getAttribute("data-result-tone");

    expect(
      failures.some((text) => /ABORTED/i.test(text)),
      "e2e/qoder-plan-ai-thinking.spec.ts :: plan-ai-cancel-aborts-request — no aborted request was " +
        `observed (failures: ${JSON.stringify(failures)}); a cancel that only hides the sheet leaves ` +
        "the model running and spending money",
    ).toBe(true);
    /* The POST had already left the browser, so the honest answer is "stopped after send",
       not "cancelled, nothing happened".  The old copy would have promised the trip was
       untouched at the one moment we cannot know that. */
    expect(
      status,
      "e2e/qoder-plan-ai-thinking.spec.ts :: plan-ai-cancel-aborts-request — cancelling an " +
        `in-flight request must read as CANCELLED_AFTER_SEND, got ${JSON.stringify(status)}`,
    ).toBe("CANCELLED_AFTER_SEND");
    expect(
      /untouched|没有被改动/.test(rendered),
      "e2e/qoder-plan-ai-thinking.spec.ts :: plan-ai-cancel-aborts-request — the sheet promised the " +
        `trip was unchanged after the request had already been sent: ${JSON.stringify(rendered)}`,
    ).toBe(false);
    expect(
      tone,
      "e2e/qoder-plan-ai-thinking.spec.ts :: plan-ai-cancel-aborts-request — a cancellation is not a " +
        `success and not a warning; tone was ${JSON.stringify(tone)}`,
    ).not.toBe("ok");
    await expect(page.getByTestId("plan-ai-live")).toHaveCount(0);
  });

  test("plan-ai-cancel-before-send — cancelling the baseline read really did send nothing", async ({
    page,
  }) => {
    test.setTimeout(150_000);
    await page.emulateMedia({ colorScheme: "light", media: "screen" });
    await page.setViewportSize({ width: 390, height: 844 });
    void page.route(STATUS, (route) =>
      route.fulfill({ status: 200, contentType: "application/json", body: '{"deepseek_configured":true}' }),
    );
    await ensureDemoJourney(page);
    await openScreen(page, "/v8/hub", ["today-heading", "today-attention"]);
    let commandCalls = 0;
    await page.route(COMMANDS, (route) => {
      commandCalls += 1;
      void route.abort();
    });
    await page.getByTestId("hub-plan-with-ai").click();
    await expect(page.getByTestId("plan-ai-sheet")).toBeVisible({ timeout: 15_000 });
    await page.getByTestId("plan-ai-input").fill(REQUEST_TEXT);
    // Armed only now, so the first /plans request it sees is the sheet's baseline read
    // rather than something the hub does while the sheet is opening.
    let plansCalls = 0;
    await page.route("**/api/v1/journeys/*/plans", async (route) => {
      plansCalls += 1;
      if (plansCalls === 1) {
        // Hold the baseline read open so cancel genuinely lands before the command
        // request is ever sent.  Aborting it from here would be a network error, not
        // a cancellation, and would exercise a different branch.
        await new Promise<void>((resolve) => setTimeout(resolve, 15_000));
        void route.abort();
        return;
      }
      void route.fulfill({ status: 200, contentType: "application/json", body: "[]" });
    });
    await page.getByTestId("plan-ai-submit").click();
    await expect(page.getByTestId("plan-ai-cancel")).toBeVisible({ timeout: 15_000 });
    await page.getByTestId("plan-ai-cancel").click();

    const result = page.getByTestId("plan-ai-result");
    await expect(result).toBeVisible({ timeout: 15_000 });
    const status = await result.getAttribute("data-result-status");
    expect(
      status,
      "e2e/qoder-plan-ai-thinking.spec.ts :: plan-ai-cancel-before-send — nothing had been sent yet, " +
        `so this must read as a clean CANCELLED, not ${JSON.stringify(status)} (baseline reads seen: ` +
        `${plansCalls}; if that is not 1 the hub made an extra /plans call and this case needs a ` +
        "different lever)",
    ).toBe("CANCELLED");
    // Let a stray request arrive before claiming none was made, or a mutant that ignores
    // the abort still reads zero.
    await page.waitForTimeout(1500);
    expect(
      commandCalls,
      "e2e/qoder-plan-ai-thinking.spec.ts :: plan-ai-cancel-before-send — the command request was " +
        `sent ${commandCalls} time(s) after the traveller cancelled the step before it; "cancel" must ` +
        "stop the run, not just the panel",
    ).toBe(0);
  });

  test("plan-ai-failure-not-loading — a refused request is named, and the fallback may not answer for it", async ({
    page,
  }) => {
    test.setTimeout(150_000);
    await page.emulateMedia({ colorScheme: "light", media: "screen" });
    await page.setViewportSize({ width: 390, height: 844 });
    void page.route(STATUS, (route) =>
      route.fulfill({ status: 200, contentType: "application/json", body: '{"deepseek_configured":true}' }),
    );
    const generateCalls: string[] = [];
    void page.route(GENERATE, (route) => {
      generateCalls.push(route.request().url());
      void route.abort();
    });
    await page.route(COMMANDS, (route) =>
      route.fulfill({
        status: 422,
        contentType: "application/json",
        body: JSON.stringify({ detail: "JOURNEY_DAYS_OUT_OF_BOUNDS: 行程天数超过上限" }),
      }),
    );
    await openSheet(page);
    await page.getByTestId("plan-ai-submit").click();

    const result = page.getByTestId("plan-ai-result");
    await expect(result).toBeVisible({ timeout: 20_000 });
    const status = await result.getAttribute("data-result-status");
    await page.getByTestId("plan-ai-detail-toggle").click();
    const reason = (await page.getByTestId("plan-ai-reason").innerText()).trim();
    const busyStillShown = await page.getByTestId("plan-ai-live").count();

    expect(
      status,
      "e2e/qoder-plan-ai-thinking.spec.ts :: plan-ai-failure-not-loading — a 422 must be reported " +
        `as the refusal it is, got ${JSON.stringify(status)}`,
    ).toBe("HTTP_422");
    expect(
      reason.includes("JOURNEY_DAYS_OUT_OF_BOUNDS"),
      "e2e/qoder-plan-ai-thinking.spec.ts :: plan-ai-failure-not-loading — the backend's own reason " +
        `never reached the sheet, technical detail reads ${JSON.stringify(reason)}`,
    ).toBe(true);
    expect(
      busyStillShown,
      "e2e/qoder-plan-ai-thinking.spec.ts :: plan-ai-failure-not-loading — the waiting block is " +
        "still on screen next to the failure, so loading and failure are not one glance apart",
    ).toBe(0);
    expect(
      generateCalls.length,
      "e2e/qoder-plan-ai-thinking.spec.ts :: plan-ai-failure-not-loading — the synthetic fallback " +
        `re-plan ran ${generateCalls.length} time(s) after a refused request; that path can report ` +
        "COMPLETED for a call the backend rejected",
    ).toBe(0);
  });

  test("plan-ai-preflight-honest — an unreadable AI status is reported as unknown, never as ready", async ({
    page,
  }) => {
    test.setTimeout(150_000);
    const cases: { body: string; status: number; want: string }[] = [
      { body: '{"deepseek_configured":true}', status: 200, want: "ready" },
      { body: '{"deepseek_configured":false}', status: 200, want: "unconfigured" },
      { body: "boom", status: 500, want: "unknown" },
      { body: '{"runtime_identity":"x"}', status: 200, want: "unknown" },
    ];
    const seen: Record<string, string> = {};
    for (const item of cases) {
      await page.emulateMedia({ colorScheme: "light", media: "screen" });
      await page.setViewportSize({ width: 390, height: 844 });
      await page.route(STATUS, (route) =>
        route.fulfill({ status: item.status, contentType: "application/json", body: item.body }),
      );
      await openSheet(page);
      const chip = page.getByTestId("plan-ai-preflight");
      await expect(chip).toBeVisible({ timeout: 15_000 });
      const got = (await chip.getAttribute("data-ai-state")) ?? "";
      const text = (await chip.innerText()).trim();
      seen[`http ${item.status} ${item.body.slice(0, 28)}`] = `${got} :: ${text}`;
      if (item.want === "unknown") {
        expect(
          /已接入|is configured/.test(text),
          "e2e/qoder-plan-ai-thinking.spec.ts :: plan-ai-preflight-honest — the sheet claimed a " +
            `model was configured after ${item.status}/${item.body.slice(0, 20)}: ${JSON.stringify(text)}`,
        ).toBe(false);
      }
      expect(
        got,
        "e2e/qoder-plan-ai-thinking.spec.ts :: plan-ai-preflight-honest — status endpoint answered " +
          `${item.status} ${item.body.slice(0, 30)}, sheet said ${JSON.stringify(got)}`,
      ).toBe(item.want);
      await page.getByTestId("plan-ai-dismiss").click();
      await expect(page.getByTestId("plan-ai-sheet")).toHaveCount(0);
    }
    writeFileSync(
      evidencePath("ui-overnight/plan-ai-preflight.json"),
      JSON.stringify({ generatedBy: "e345b9d6", order: "ORD-0038", cases: seen }, null, 2) + "\n",
      "utf-8",
    );
  });
});
