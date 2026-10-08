import { expect, test, type Browser } from "@playwright/test";

/* Is the desktop rail the same "one unbounded column" the drawer just was? The rail renders the
   same 15 desktop routes, so at a short viewport it has to either scroll or overflow. This measures
   the rail's own geometry per shape and reports whether it scrolls, whether its last row is
   reachable, and whether that last row lands under the fixed bottom bar the way the drawer's did. */
const SHAPES = [
  { name: "landscape-phone", width: 740, height: 360 },
  { name: "desktop-short", width: 1280, height: 600 },
  { name: "desktop", width: 1280, height: 800 },
  { name: "desktop-tall", width: 1440, height: 900 },
];

for (const shape of SHAPES) {
  test(`RAIL SHAPE ${shape.name} ${shape.width}x${shape.height}`, async ({ browser }: { browser: Browser }) => {
    const ctx = await browser.newContext({ viewport: { width: shape.width, height: shape.height }, locale: "en" });
    const page = await ctx.newPage();
    let rec: Record<string, unknown> = { shape: shape.name };
    try {
      await page.goto("/", { waitUntil: "networkidle", timeout: 90000 });
      for (const re of [/sealed demo/i, /使用封存的演示行程/]) {
        const c = page.getByText(re).first();
        if (await c.count()) { await c.click().catch(() => {}); await page.waitForTimeout(4000); break; }
      }
      rec = await page.evaluate((s) => {
        const rail = document.querySelector("nav.v8-nav") as HTMLElement | null;
        if (!rail) return { railPresent: false, viewport: s };
        const rows = Array.from(rail.querySelectorAll("button")).filter((b) => (b.textContent || "").trim());
        const cs = getComputedStyle(rail);
        const last = rows[rows.length - 1] as HTMLElement | undefined;
        // The rail is not a scroller, so the only way a traveller could reach a row below the fold
        // is the page itself. Try that door before calling anything unreachable.
        window.scrollTo(0, document.documentElement.scrollHeight);
        const se = document.scrollingElement as HTMLElement | null;
        if (se) se.scrollTop = se.scrollHeight;
        const docScrollable = document.documentElement.scrollHeight > window.innerHeight;
        const lb = last ? last.getBoundingClientRect() : null;
        const nav = document.querySelector(".v8-mobile-nav") as HTMLElement | null;
        const nb = nav ? nav.getBoundingClientRect() : null;
        let lastHit: string | null = null;
        let lastHitInside = false;
        if (lb) {
          const h = document.elementFromPoint(Math.round(lb.left + lb.width / 2), Math.round(lb.top + lb.height / 2));
          lastHit = h ? h.tagName.toLowerCase() : "none";
          lastHitInside = !!(h && last && (h === last || last.contains(h)));
        }
        return {
          railPresent: true,
          viewport: s,
          railOverflowY: cs.overflowY,
          railScroll: rail.scrollHeight - rail.clientHeight,
          railClientHeight: rail.clientHeight,
          rows: rows.length,
          docScrollable,
          docScrollTopAfterMax: se ? Math.round(se.scrollTop) : null,
          docRemainingScroll: se ? Math.round(se.scrollHeight - se.scrollTop - se.clientHeight) : null,
          lastRowText: last ? (last.textContent || "").trim().slice(0, 18) : null,
          lastRowBottom: lb ? Math.round(lb.bottom) : null,
          lastRowVisibleInViewport: lb ? lb.bottom <= window.innerHeight && lb.top >= 0 : null,
          bottomBarTop: nb ? Math.round(nb.top) : null,
          lastHit,
          lastHitInside,
        };
      }, `${shape.width}x${shape.height}`);
      // Definitive reachability, measured while the page is still open: Playwright's own
      // actionability walk scrolls by whatever means the element needs (the page here, since the
      // rail is not a scroller) and then hit-tests the centre. Max-page-scroll alone is not a
      // verdict -- at a short height the row can pass above the fold on the way to the bottom.
      const lastRailRow = page.locator("nav.v8-nav button").last();
      try {
        await lastRailRow.click({ trial: true, timeout: 5000 });
        rec.lastRowReachable = true;
      } catch {
        rec.lastRowReachable = false;
      }
    } finally {
      await ctx.close();
    }
    console.log("RAIL_SHAPE " + JSON.stringify(rec));
    expect(rec.railPresent, "the desktop rail has to be on screen at this shape").toBe(true);
  });
}
