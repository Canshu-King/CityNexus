/**
 * Drawer grouping receipt -- one machine-readable line that records the rendered geometry of the
 * grouped drawer at the phone shape, so every number quoted about this change can be re-fetched
 * from a file rather than re-typed from memory.
 *
 * It reports: the viewport it measured, the drawer's own overflow, the number of group sections,
 * the number of route rows, the hit-testable rows, and each group body's own scroll extent.
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

test("DRAWER RECEIPT", async ({ browser }: { browser: Browser }) => {
  const ctx = await browser.newContext({
    viewport: { width: 390, height: 844 },
    hasTouch: true,
    locale: "en",
  });
  const page = await ctx.newPage();
  await openDrawer(page);

  const rows = page.locator('[data-testid^="v8-drawer-entry-"]');
  const total = await rows.count();
  let clickable = 0;
  for (let i = 0; i < total; i++) {
    try {
      await rows.nth(i).click({ trial: true, timeout: 4000 });
      clickable++;
    } catch {
      /* counted as unreachable below */
    }
  }
  const geom = await page.evaluate(() => {
    const drawer = document.querySelector("#v8-nav-drawer") as HTMLElement;
    const sections = Array.from(drawer.querySelectorAll(".v8-nav-group-section"));
    return {
      drawerOverflow: drawer.scrollHeight - drawer.clientHeight,
      drawerClientHeight: drawer.clientHeight,
      drawerScrollHeight: drawer.scrollHeight,
      sections: sections.length,
      bodies: sections.map((s) => {
        const el = s.querySelector(".v8-nav-group-body") as HTMLElement;
        const g = (s.getAttribute("data-group") || "?").toLowerCase();
        return g + "=" + (el.scrollHeight - el.clientHeight);
      }),
      iconWidth: Math.round(
        (document.querySelector('[data-testid^="v8-drawer-entry-"] svg') as SVGElement).getBoundingClientRect().width,
      ),
    };
  });

  const line = [
    "viewport=390x844",
    "drawerOverflow=" + geom.drawerOverflow,
    "drawerClientHeight=" + geom.drawerClientHeight,
    "drawerScrollHeight=" + geom.drawerScrollHeight,
    "groupSections=" + geom.sections,
    "routeRows=" + total,
    "clickableRows=" + clickable,
    "iconWidth=" + geom.iconWidth,
    "bodyScrollOverflow=" + geom.bodies.join(","),
  ].join(" ");
  console.log("DRAWER_RECEIPT " + line);
  expect(geom.sections, "four semantic groups must render").toBe(4);
  expect(clickable, "every route row must be clickable").toBe(total);
  await ctx.close();
});
