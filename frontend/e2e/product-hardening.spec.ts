import { expect, test, type Page } from "@playwright/test";
import { testIds } from "../src/contracts/testIds";

/* This file used to hold five legacy Journey Mode cases.  Four of them guard a
 * capability the current surface no longer presents (Control Tower evidence and
 * authority, the persisted natural-language mission, assisted acceptance, and the
 * Proactive Guardian flagship button) and now live in `e2e/legacy/`, outside the
 * acceptance suite — see `docs/LEGACY_E2E_MIGRATION.md` for the per-case mapping.
 *
 * This one stays, red, on purpose.  The arbiter ruled it PORT-FIRST: envelope-safe
 * autonomous recovery through the Agent Gateway is a direction CityNexus is still
 * going in, so retiring the UI that asserted it must not delete the behaviour
 * check.  It is not skipped and not softened; pass-15 replaces it with a
 * current-surface equivalent, and until then the suite is honestly red.
 */

async function openJourney(page: Page) {
  await page.goto("/");
  await expect(page.getByTestId(testIds.journeyStatus)).toHaveAttribute("data-source", "backend");
  await expect(page.getByTestId(testIds.currentActivity)).toContainText("Tech Art Center");
}

test("Autonomous mode executes an envelope-safe recovery through the Agent Gateway", async ({
  page,
}) => {
  await openJourney(page);

  const setMode = page.waitForResponse(
    (response) =>
      response.url().includes("/agent-policy") &&
      response.request().method() === "PUT" &&
      response.status() === 200,
  );
  await page.getByTestId("agent-mode").selectOption("AUTONOMOUS");
  await setMode;

  const setCost = page.waitForResponse(
    (response) =>
      response.url().includes("/agent-policy") &&
      response.request().method() === "PUT" &&
      response.status() === 200,
  );
  await page.locator("#agent-cost-limit").fill("3000");
  await setCost;

  const setDrift = page.waitForResponse(
    (response) =>
      response.url().includes("/agent-policy") &&
      response.request().method() === "PUT" &&
      response.status() === 200,
  );
  await page.locator("#agent-drift-limit").fill("120");
  await setDrift;

  const enableAuto = page.waitForResponse(
    (response) =>
      response.url().includes("/agent-policy") &&
      response.request().method() === "PUT" &&
      response.status() === 200,
  );
  await page.getByTestId("agent-auto-accept").check();
  await enableAuto;

  await page.getByTestId(testIds.eventSimulator).click();
  const eventResponse = page.waitForResponse(
    (response) =>
      response.url().includes("/events") &&
      response.request().method() === "POST" &&
      response.status() === 201,
  );
  const requestResponse = page.waitForResponse(
    (response) =>
      response.url().endsWith("/agent/tools/request_replan") &&
      response.request().method() === "POST" &&
      response.status() === 200,
  );
  const acceptResponse = page.waitForResponse(
    (response) =>
      response.url().endsWith("/agent/tools/accept_replan") &&
      response.request().method() === "POST" &&
      response.status() === 200,
  );
  await page.getByTestId(testIds.eventClosureButton).click();
  await eventResponse;
  const requestReceipt = await (await requestResponse).json();
  const acceptReceipt = await (await acceptResponse).json();
  expect(requestReceipt.decision).toBe("ALLOW_AUTO");
  expect(acceptReceipt.decision).toBe("ALLOW_AUTO");
  expect(acceptReceipt.executed).toBe(true);
  await expect(page.getByTestId("agent-policy-decision")).toContainText("ALLOW_AUTO");
  await expect(page.getByTestId(testIds.protectedCommitment)).toContainText("River Cruise");
  await expect(page.getByTestId("reflect-summary")).toContainText("replans");

  await page.reload();
  await expect(page.getByTestId("agent-feed")).toContainText(/replan auto accepted/i);
  await expect(page.locator(".maplibre-container")).toHaveAttribute(
    "data-route-source",
    "frozen_mobility_snapshot",
  );
});
