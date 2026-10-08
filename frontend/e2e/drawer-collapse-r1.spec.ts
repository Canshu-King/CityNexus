import { expect, test } from "@playwright/test";

test("DRAWER COLLAPSE toggling a group header hides its body", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/", { waitUntil: "networkidle", timeout: 90000 });
  for (const re of [/sealed demo/i, /使用封存的演示行程/]) {
    const c = page.getByText(re).first();
    if (await c.count()) { await c.click().catch(() => {}); await page.waitForTimeout(4000); break; }
  }
  await page.locator('[aria-controls="v8-nav-drawer"]').first().click();
  await page.waitForTimeout(1000);

  const header = page.locator('[data-testid="v8-drawer-group-SYSTEM"]');
  const body = page.locator('[data-testid="v8-drawer-group-body-SYSTEM"]');
  await expect(header).toBeVisible();
  await expect(body).toBeVisible();

  await header.click();
  await page.waitForTimeout(400);
  // The body is collapsed: its rows are no longer hit-testable, and the drawer total grew shorter.
  const after = await page.evaluate(() => {
    const drawer = document.querySelector("#v8-nav-drawer") as HTMLElement;
    const body = document.querySelector('[data-testid="v8-drawer-group-body-SYSTEM"]') as HTMLElement;
    return {
      drawerScroll: drawer.scrollHeight - drawer.clientHeight,
      bodyHidden: body.hasAttribute("hidden") || getComputedStyle(body).display === "none",
      headerExpanded: document.querySelector('[data-testid="v8-drawer-group-SYSTEM"]')!.getAttribute("aria-expanded"),
    };
  });
  console.log("DRAWER_COLLAPSE " + JSON.stringify(after));
  expect(after.bodyHidden, "the collapsed group body must be hidden").toBe(true);
  expect(after.headerExpanded).toBe("false");
  // Reopen it.
  await header.click();
  await page.waitForTimeout(400);
  const reopened = await page.evaluate(() => {
    const body = document.querySelector('[data-testid="v8-drawer-group-body-SYSTEM"]') as HTMLElement | null;
    return body ? getComputedStyle(body).display : "missing";
  });
  expect(reopened, "reopening the group must show its body again").not.toBe("none");
});
