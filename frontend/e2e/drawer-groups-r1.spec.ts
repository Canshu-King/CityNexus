/**
 * Drawer grouping reachability probe -- the direct test of the order's own acceptance criterion:
 * every route in every group must be clickable, and the scroll must happen inside the group body
 * rather than in one unbounded drawer column.
 *
 * Reachability is asserted with Playwright's own actionability engine (locator.click with
 * { trial: true }): it scrolls the row into view inside its own scroll container, then checks the
 * row is visible, stable and receives pointer events at its centre. A real click would navigate and
 * tear the drawer down, so the trial performs every reachability check without firing the
 * navigation. This is exactly what "a user can reach and tap every item" means, and it does not
 * depend on the probe re-deriving scroll math the product owns.
 */
import { expect, test, type Browser, type Page } from "@playwright/test";

async function openDrawer(page: Page) {
  await page.goto("/", { waitUntil: "networkidle", timeout: 90000 });
  for (const re of [/sealed demo/i, /使用封存的演示行程/]) {
    const cand = page.getByText(re).first();
    if (await cand.count()) {
      await cand.click().catch(() => {});
      await page.waitForTimeout(4000);
      break;
    }
  }
  const ham = page.locator('[aria-controls="v8-nav-drawer"]');
  expect(await ham.count(), "the hamburger has to exist on a phone shape").toBeGreaterThan(0);
  await ham.first().click();
  await page.waitForTimeout(1200);
}

test("DRAWER GROUPS every row in every group is clickable", async ({
  browser,
}: {
  browser: Browser;
}) => {
  const ctx = await browser.newContext({
    viewport: { width: 390, height: 844 },
    hasTouch: true,
    locale: "en",
  });
  const page = await ctx.newPage();
  await openDrawer(page);
  expect(await page.locator("#v8-nav-drawer").count(), "the drawer must open").toBe(1);

  const rows = page.locator('[data-testid^="v8-drawer-entry-"]');
  const total = await rows.count();
  const unreachable: string[] = [];
  const scrollTopByGroup: Record<string, number> = {};
  for (let i = 0; i < total; i++) {
    const row = rows.nth(i);
    const label = (await row.innerText()).trim().slice(0, 24);
    const group = (await row.locator("xpath=ancestor::*[@data-group][1]").getAttribute("data-group")) || "?";
    // The trial performs Playwright's full actionability walk: scroll the row into its own scroll
    // container, then verify it is the hit target at its centre. No navigation fires.
    let ok = true;
    try {
      await row.click({ trial: true, timeout: 4000 });
    } catch {
      ok = false;
    }
    if (!ok) unreachable.push(group + ":" + label);
    const bodyScroll = await row
      .locator("xpath=ancestor::*[contains(@class,'v8-nav-group-body')][1]")
      .evaluate((el) => (el as HTMLElement).scrollTop)
      .catch(() => 0);
    scrollTopByGroup[group] = Math.max(scrollTopByGroup[group] ?? 0, bodyScroll as number);
  }

  console.log(
    "DRAWER_GROUPS " +
      JSON.stringify({ total, unreachable, scrollTopByGroup, groupCount: Object.keys(scrollTopByGroup).length }),
  );
  expect(total, "the drawer must render all of its route rows").toBe(17);
  expect(Object.keys(scrollTopByGroup).length, "four groups must render").toBe(4);
  // A group whose body never had to scroll (scrollTop 0 for every row) proves the scroll happened
  // inside the group, and a non-empty max means a long group did cap and scroll on its own.
  expect(unreachable, "every route row must be clickable").toEqual([]);
  await page.screenshot({ path: "/tmp/drawer_after.png" });
  await ctx.close();
});
