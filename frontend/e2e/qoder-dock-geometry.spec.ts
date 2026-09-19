import { expect, test } from "@playwright/test";
import { createFreshJourney, useJourney } from "./_qoderFreshJourney";

/* pass-13 C — measure before claiming.
 *
 * pass-12 concluded from a 390x2250 fullPage capture that the Copilot pill sat
 * over the Live EVIDENCE row.  That was the wrong instrument: a `position: fixed`
 * overlay is painted at its viewport position into a stitched image, so a long
 * screenshot can show a collision that no user ever sees, and hide one that they
 * do.  This file therefore measures the real thing — the dock's rectangle and the
 * rectangles of the actionable elements under it, at 390x844, at three scroll
 * positions — and prints the numbers before it asserts anything.
 */

type Rect = { x: number; y: number; w: number; h: number };

type Probe = {
  dock: Rect & { idleCompact: string; state: string };
  viewport: { w: number; h: number };
  scrollY: number;
  maxScroll: number;
  covered: { tag: string; label: string; rect: Rect; overlap: Rect }[];
  actionableInView: number;
};

async function probe(page: import("@playwright/test").Page): Promise<Probe> {
  return page.evaluate(() => {
    const dock = document.querySelector(".cn-copilot-dock") as HTMLElement | null;
    if (!dock) throw new Error("no .cn-copilot-dock on screen");
    const d = dock.getBoundingClientRect();
    const rect = (el: Element) => {
      const r = (el as HTMLElement).getBoundingClientRect();
      return { x: r.left, y: r.top, w: r.width, h: r.height };
    };
    const selectors = "button, a[href], input, select, textarea, [role=button]";
    const scroller =
      document.scrollingElement ?? (document.querySelector(".v8-content") as Element | null);
    const candidates = Array.from(document.querySelectorAll(selectors)).filter((el) => {
      const r = el.getBoundingClientRect();
      if (r.width === 0 || r.height === 0) return false;
      if (r.bottom < 0 || r.top > window.innerHeight) return false;
      return !dock.contains(el) && !el.contains(dock);
    });
    const covered = candidates
      .map((el) => {
        const r = el.getBoundingClientRect();
        const x = Math.max(r.left, d.left);
        const y = Math.max(r.top, d.top);
        const right = Math.min(r.right, d.right);
        const bottom = Math.min(r.bottom, d.bottom);
        const w = right - x;
        const h = bottom - y;
        if (w <= 1 || h <= 1) return null;
        const label =
          (el.getAttribute("aria-label") ||
            el.getAttribute("data-testid") ||
            (el.textContent || "").trim().slice(0, 32) ||
            el.tagName.toLowerCase());
        return { tag: el.tagName.toLowerCase(), label, rect: rect(el), overlap: { x, y, w, h } };
      })
      .filter(Boolean) as Probe["covered"];
    return {
      dock: {
        ...rect(dock),
        idleCompact: dock.getAttribute("data-idle-compact") ?? "?",
        state: dock.className.replace("cn-copilot-dock", "").trim() || "default",
      },
      viewport: { w: window.innerWidth, h: window.innerHeight },
      scrollY: Math.round(scroller ? scroller.scrollTop : window.scrollY),
      maxScroll: Math.round(scroller ? scroller.scrollHeight - scroller.clientHeight : 0),
      covered,
      actionableInView: candidates.length,
    };
  });
}

function report(route: string, at: string, probe: Probe) {
  const lines = probe.covered.map(
    (c) =>
      `      ${c.tag} "${c.label}" rect=${Math.round(c.rect.y)}..${Math.round(
        c.rect.y + c.rect.h,
      )} overlap=${Math.round(c.overlap.w)}x${Math.round(c.overlap.h)}px`,
  );
  console.log(
    `[dock-geometry] ${route} @${at} viewport=${probe.viewport.w}x${probe.viewport.h} ` +
      `dock=${Math.round(probe.dock.x)},${Math.round(probe.dock.y)} ${Math.round(
        probe.dock.w,
      )}x${Math.round(probe.dock.h)} state=${probe.dock.state} idleCompact=${probe.dock.idleCompact} ` +
      `scrollY=${probe.scrollY}/${probe.maxScroll} actionableInView=${probe.actionableInView} ` +
      `covered=${probe.covered.length}`,
  );
  for (const line of lines) console.log(line);
}

test.describe("Copilot dock geometry at phone size", () => {
  test.beforeEach(async ({ page }) => {
    await page.addInitScript(() => localStorage.setItem("citynexus.locale", "en"));
  });

  for (const route of ["/v8/live", "/v8/hub"]) {
    test(`${route}: the dock must not sit on an actionable element at the end of the scroll`, async ({
      page,
      request,
    }) => {
      const { journeyId } = await createFreshJourney(request);
      await useJourney(page, journeyId);
      await page.setViewportSize({ width: 390, height: 844 });
      await page.goto(route);
      await page.waitForFunction(
        () => !!document.querySelector(".cn-copilot-dock"),
        undefined,
        { timeout: 15_000 },
      );
      await page.waitForTimeout(900);

      /* Measure the whole scroll range.  A fixed overlay necessarily passes over
         content while the page scrolls; what must never happen is a control being
         unreachable where the page comes to rest. */
      const positions = ["top", "middle", "bottom"] as const;
      const results = new Map<string, Probe>();
      for (const at of positions) {
        await page.evaluate((where) => {
          const scroller =
            document.scrollingElement ?? document.querySelector(".v8-content");
          if (!scroller) return;
          const max = scroller.scrollHeight - scroller.clientHeight;
          scroller.scrollTop = where === "top" ? 0 : where === "middle" ? max / 2 : max;
        }, at);
        await page.waitForTimeout(450);
        const measured = await probe(page);
        results.set(at, measured);
        report(route, at, measured);
      }

      if (route === "/v8/live") {
        await page.screenshot({
          path: "../reports/dock-geometry/live-390x844-bottom.png",
        });
      } else {
        await page.screenshot({
          path: "../reports/dock-geometry/today-390x844-bottom.png",
        });
      }

      const bottom = results.get("bottom")!;
      expect(
        bottom.covered.length,
        `${route} at rest: ${bottom.covered.length} actionable element(s) sit under the dock ` +
          `(${bottom.covered.map((c) => c.label).join(", ")})`,
      ).toBe(0);
    });
  }
});
