/**
 * Drawer grouping shape sweep.
 *
 * The grouping was accepted at one phone shape, so every other shape was still an assumption. This
 * walks the shapes a traveller actually opens the drawer on and asks two things per shape: does the
 * drawer's own column stay bounded (the grouping's whole purpose is that total height stops growing
 * with the route list), and is every route row still clickable inside its own group body.
 *
 * A shape where the drawer itself still scrolls is reported, not hidden -- at short viewports four
 * capped bodies can exceed the screen, and that residual scroll is the thing a traveller would feel.
 */
import { expect, test, type Browser } from "@playwright/test";

const SHAPES: { name: string; width: number; height: number; touch: boolean }[] = [
  { name: "small-phone", width: 360, height: 640, touch: true },
  { name: "phone", width: 390, height: 844, touch: true },
  { name: "phone-large", width: 414, height: 896, touch: true },
  { name: "landscape-phone", width: 740, height: 360, touch: true },
  { name: "tablet", width: 768, height: 1024, touch: true },
];

for (const shape of SHAPES) {
  // One test per shape: five shapes and seventeen per-row actionability walks do not fit in the
  // suite's 60s per-test budget, and a single over-budget test reads as a product failure.
  test(`DRAWER SHAPE ${shape.name} ${shape.width}x${shape.height}`, async ({
    browser,
  }: {
    browser: Browser;
  }) => {
    const ctx = await browser.newContext({
      viewport: { width: shape.width, height: shape.height },
      hasTouch: shape.touch,
      locale: "en",
    });
    const page = await ctx.newPage();
    const rec: Record<string, unknown> = { shape: shape.name, w: shape.width, h: shape.height };
    try {
      await page.goto("/", { waitUntil: "networkidle", timeout: 90000 });
      for (const re of [/sealed demo/i, /使用封存的演示行程/]) {
        const c = page.getByText(re).first();
        if (await c.count()) { await c.click().catch(() => {}); await page.waitForTimeout(4000); break; }
      }
      const ham = page.locator('[aria-controls="v8-nav-drawer"]');
      rec.ham = await ham.count();
      // Count is not visibility: above the phone breakpoint the hamburger stays in the DOM but is
      // display:none (the desktop rail is the nav there), and clicking it would hang to timeout.
      const hamVisible = rec.ham ? await ham.first().isVisible() : false;
      rec.hamVisible = hamVisible;
      if (hamVisible) {
        await ham.first().click();
        await page.waitForTimeout(1000);
      }
      const open = await page.locator("#v8-nav-drawer").count();
      rec.drawerOpen = open;
      if (open) {
        const entries = page.locator('[data-testid^="v8-drawer-entry-"]');
        const n = await entries.count();
        rec.routeRows = n;
        let clickable = 0;
        for (let i = 0; i < n; i++) {
          try { await entries.nth(i).click({ trial: true, timeout: 4000 }); clickable++; } catch { /* */ }
        }
        rec.clickableRows = clickable;
        rec.geom = await page.evaluate(() => {
          const d = document.querySelector("#v8-nav-drawer") as HTMLElement;
          const cs = getComputedStyle(d);
          return {
            drawerOverflow: d.scrollHeight - d.clientHeight,
            sections: d.querySelectorAll(".v8-nav-group-section").length,
            bodiesScrollAlone: Array.from(d.querySelectorAll(".v8-nav-group-body")).map(
              (b) => (b as HTMLElement).scrollHeight - (b as HTMLElement).clientHeight,
            ),
            drawerOverflowStyle: cs.overflowY,
          };
        });
      }
    } finally {
      await ctx.close();
    }
    console.log("DRAWER_SHAPE " + JSON.stringify(rec));
    // Above the phone breakpoint the hamburger is not drawn, so the drawer is simply unavailable
    // there; that is recorded, not asserted away.
    if (rec.drawerOpen) {
      const g = rec.geom as { drawerOverflow: number; sections: number };
      expect(g.sections, `${shape.name}: the four groups must render`).toBe(4);
      expect(rec.clickableRows, `${shape.name}: every route row must be clickable`).toBe(rec.routeRows);
      expect(g.drawerOverflow, `${shape.name}: the drawer column must not grow with the route list`)
        .toBe(0);
    }
  });
}
