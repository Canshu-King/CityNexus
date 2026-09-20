import { expect, test } from "@playwright/test";
import { writeFileSync } from "node:fs";
import { openScreen } from "./_qoderShellSeed";
import { evidencePath } from "./_qoderEvidence";

/**
 * ORD-0034 — a failed journey creation must be visible.
 *
 * The user's report was "stuck on 确认创建".  The shell's createJourney catch does write
 * the named backend error into state, and the shell does render state — but this screen
 * returns before the shell exists (V8Experience.tsx:794), so nothing reached the display.
 * Retrying the button looked identical to it working, which is what read as frozen.
 *
 * This gate drives the real product with a real failing request rather than asserting on
 * markup: POST /api/v1/journeys answers 500 with the same body shape the backend uses, so
 * the path under test is v8Request -> createJourney's catch -> the wizard's own failure
 * signal, not a fixture.
 *
 * It is deliberately killable in two places, and both are named in the run log:
 *   - remove the wizard's failure render  -> this test must go red
 *   - remove the `message` prop plumbing  -> see the reason assertion below
 */

const NAMED_ERROR = "V13_JOURNEY_DAYS_OUT_OF_BOUNDS:9";

async function openFreshWizard(page: import("@playwright/test").Page) {
  await page.addInitScript(() => {
    try {
      localStorage.clear();
    } catch {
      /* nothing to clear before the first commit */
    }
  });
  await openScreen(page, "/v8", ["trial-setup"]);
}

async function walkToStep3(page: import("@playwright/test").Page) {
  await page.getByTestId("trial-city").fill("Tianjin");
  await page.getByTestId("trial-arrival").fill("Tianjin West Station");
  await page.getByTestId("trial-departure").fill("Tianjin Binhai Airport");
  await page.getByTestId("trial-next").click();
  await page.waitForTimeout(300);
  await page.getByTestId("trial-next").click();
  await page.waitForTimeout(500);
  await expect(page.getByTestId("trial-create")).toBeVisible({ timeout: 10_000 });
}

test.describe("ORD-0034 onboarding surfaces a failed create", () => {
  test("a 500 on journey creation shows a visible, named failure instead of silence", async ({
    page,
  }) => {
    test.setTimeout(180_000);
    await page.emulateMedia({ colorScheme: "light", media: "screen" });
    await page.setViewportSize({ width: 412, height: 915 });

    let sawCreateRequest = false;
    await page.route("**/api/v1/journeys", async (route) => {
      if (route.request().method() !== "POST") return route.fallback();
      sawCreateRequest = true;
      await route.fulfill({
        status: 500,
        contentType: "application/json",
        body: JSON.stringify({ detail: NAMED_ERROR }),
      });
    });

    await openFreshWizard(page);
    await walkToStep3(page);

    // Precondition: before the attempt there must be no error node, or this proves nothing.
    await expect(page.getByTestId("trial-create-error")).toHaveCount(0);

    await page.getByTestId("trial-create").click();

    const error = page.getByTestId("trial-create-error");
    await expect(error, "e2e/qoder-onboarding-failure.spec.ts :: trial-create-error").toBeVisible({
      timeout: 15_000,
    });

    const text = (await error.textContent()) ?? "";
    /* Requirement 3: no silent "looks clickable again" state.  The notice has to say the
       step did not complete even when the reason itself cannot reach this screen. */
    const saysItFailed =
      /没有成功|did not complete|no journey was created/i.test(text);

    const evidence = {
      generatedBy: "e345b9d6",
      sawCreateRequest,
      namedErrorFromBackend: NAMED_ERROR,
      renderedText: text.trim(),
      saysItFailed,
      carriesNamedReason: text.includes(NAMED_ERROR),
    };
    writeFileSync(
      evidencePath("ui-overnight/onboarding-create-failure.json"),
      JSON.stringify(evidence, null, 2) + "\n",
      "utf-8",
    );

    expect(sawCreateRequest, "the wizard never issued a POST /api/v1/journeys").toBe(true);
    expect(
      saysItFailed,
      `the failure notice does not state the step failed; it rendered: "${text.trim()}"`,
    ).toBe(true);
  });

  /* Split out on purpose.  Kept inside the test above, this would share one red/green
     verdict with the fix that has landed, and a suite reading could not tell "the wizard
     is no longer silent" apart from "the named reason still cannot reach this screen".
     The remaining gap is one prop at V8Experience.tsx:800, a file this lane does not own. */
  test("the named backend reason reaches the onboarding screen", async ({ page }) => {
    test.setTimeout(180_000);
    await page.emulateMedia({ colorScheme: "light", media: "screen" });
    await page.setViewportSize({ width: 412, height: 915 });

    await page.route("**/api/v1/journeys", async (route) => {
      if (route.request().method() !== "POST") return route.fallback();
      /* A4-1 froze the envelope: `VALIDATION_ERROR` with details.errors[].loc/msg.  This is
         the body a real create returns when an anchor location is left blank. */
      await route.fulfill({
        status: 422,
        contentType: "application/json",
        body: JSON.stringify({
          error: {
            code: "VALIDATION_ERROR",
            message: "Request validation failed",
            trace_id: "probe-trace",
            details: {
              errors: [
                {
                  loc: ["body", "arrival_anchor", "location"],
                  msg: "String should have at least 1 character",
                  type: "string_too_short",
                },
              ],
            },
          },
        }),
      });
    });

    await openFreshWizard(page);
    await walkToStep3(page);
    await page.getByTestId("trial-create").click();

    const error = page.getByTestId("trial-create-error");
    await expect(error).toBeVisible({ timeout: 15_000 });
    const shown = (await error.innerText()).replace(/\s+/g, " ");
    await expect(
      error,
      "e2e/qoder-onboarding-failure.spec.ts :: named reason inside trial-create-error",
    ).toContainText("arrival_anchor.location");
    await expect(
      error,
      "e2e/qoder-onboarding-failure.spec.ts :: named reason inside trial-create-error",
    ).toContainText("String should have at least 1 character");
    expect(
      /^Request validation failed\s*$/.test(shown.trim()),
      "e2e/qoder-onboarding-failure.spec.ts :: named reason inside trial-create-error — the panel " +
        `shows only the constant headline: ${JSON.stringify(shown.trim())}`,
    ).toBe(false);
  });

  /* ORD-0044 -- the acceptance item.  Nothing is mocked here: a 4-day window is legal by a
     wide margin, so if the success path advances, `.v8-product-shell` must appear inside
     five seconds.  Remove the stay-options/generate call from createJourney and this node
     goes red while the journeys row still exists -- a half-created trip, which is precisely
     what the user was clicking "retry" against. */
  test("legal-window-create-advances — a legal trip reaches the app within 5s", async ({ page }) => {
    test.setTimeout(180_000);
    const started = Date.now();
    await page.emulateMedia({ colorScheme: "light", media: "screen" });
    await page.setViewportSize({ width: 390, height: 844 });
    await openFreshWizard(page);
    await page.getByTestId("trial-city").fill("Tianjin");
    await page.getByTestId("trial-arrival").fill("Tianjin West Station");
    await page.getByTestId("trial-departure").fill("Tianjin Binhai Airport");
    await page.getByTestId("trial-start").fill("2026-10-09T18:00");
    await page.getByTestId("trial-end").fill("2026-10-13T15:00");
    await page.getByTestId("trial-next").click();
    await page.getByTestId("trial-next").click();
    await expect(page.getByTestId("trial-create")).toBeVisible({ timeout: 10_000 });
    await page.getByTestId("trial-create").click();

    await expect(
      page.locator(".v8-product-shell"),
      "e2e/qoder-onboarding-failure.spec.ts :: legal-window-create-advances — a legal 4-day trip " +
        "never reached the app: the create stopped after the journey row was written, which is " +
        "the 'nothing happens, retry it' report on non-erroring input",
    ).toBeVisible({ timeout: 5_000 });
    const elapsed = Date.now() - started;
    expect(
      await page.evaluate(() => localStorage.getItem("citynexus.v8.journey_id")),
      "e2e/qoder-onboarding-failure.spec.ts :: legal-window-create-advances — the shell appeared " +
        "but no journey id was stored, so the create did not really complete",
    ).toMatch(/^[0-9a-f-]{36}$/);
    console.log(`legal-window-create-advances reached the shell in ${elapsed}ms`);
  });

  /* ORD-0044's root cause: the API requires a non-empty anchor location at both ends, but
     the field looked optional and the review page showed a dash, so a legal-looking trip
     died on a 422.  Blocked before submit is right; blocked *silently* is not. */
  test("missing-anchor-is-named-before-submit", async ({ page }) => {
    test.setTimeout(120_000);
    await page.emulateMedia({ colorScheme: "light", media: "screen" });
    await page.setViewportSize({ width: 390, height: 844 });
    await openFreshWizard(page);
    await page.getByTestId("trial-city").fill("Tianjin");

    await expect(
      page.getByTestId("trial-required-hint"),
      "e2e/qoder-onboarding-failure.spec.ts :: missing-anchor-is-named-before-submit — the anchor " +
        "fields are required by the API but the wizard gives no reason for the blocked Next",
    ).toContainText(/抵达|离开|arrive|leave/i, { timeout: 5_000 });
    await expect(
      page.getByTestId("trial-next"),
      "e2e/qoder-onboarding-failure.spec.ts :: missing-anchor-is-named-before-submit — Next was " +
        "enabled with an empty anchor, so the traveller would have met the 422 instead",
    ).toBeDisabled();

    await page.getByTestId("trial-arrival").fill("Tianjin West Station");
    await page.getByTestId("trial-departure").fill("Tianjin Binhai Airport");
    await expect(
      page.getByTestId("trial-next"),
      "e2e/qoder-onboarding-failure.spec.ts :: missing-anchor-is-named-before-submit — Next stayed " +
        "blocked after every required field was filled",
    ).toBeEnabled();
  });
});
