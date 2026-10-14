import { expect, test } from "@playwright/test";

/**
 * Regression for 2026-10-15 real first-user screenshot.
 * The pasted URL ended with two Markdown '*' characters; V8 silently
 * presented its old "New Journey" wizard instead of Revolution.
 *
 * This test checks ROUTING only, not model tool calls or user journey success.
 */
test("Revolution copied link with Markdown stars opens the intended app", async ({ page }) => {
  await page.goto("/revolution**");
  await expect(page).toHaveURL(/\/revolution$/);
  await expect(page.getByTestId("revolution-first-look")).toBeVisible();
  await expect(page.getByTestId("revolution-agent-runtime")).toBeVisible();
});

test("Canonical Revolution link opens directly, without the legacy wizard", async ({ page }) => {
  await page.goto("/revolution");
  await expect(page.getByTestId("revolution-first-look")).toBeVisible();
});
