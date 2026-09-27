import { expect, test, type Page } from "@playwright/test";
import { writeFileSync } from "node:fs";
import { ensureDemoJourney, openScreen } from "./_qoderShellSeed";
import { evidencePath } from "./_qoderEvidence";

/**
 * ORD-A — the basemap provider's name has to be on the glass.
 *
 * Both map surfaces construct maplibre with `attributionControl:false`
 * (`components/v8/MapPanel.tsx:245`, `components/JourneyMap.tsx:112`), so the OSM notice only ever
 * reached the tile source's metadata. This gate walks the same entry the product offers — the
 * sealed-demo journey on the setup screen, then the 底栏「地图」 button — and reads
 * `document.body.innerText`, because the thing a traveller can comply with is the painted string,
 * not a data attribute, not an aria label, and not "injected into the style document".
 *
 * It is asserted per viewport width (320/360/390/414) because the notice wraps, and a wrapped
 * overlay is exactly how the gesture bubble ended up covering it during this order's own first
 * measurement pass — every geometric assertion passed while the screenshot showed the text buried.
 * So each arm additionally requires: the notice inside the panel's own bounds, not clipped by its
 * box, no horizontal scroll added to the page, and no rectangle overlap with the gesture bubble.
 *
 * The host substring is what is checked rather than a whole sentence: both language arms carry
 * `tile.openstreetmap.org` verbatim, so the assertion cannot be satisfied by a paraphrase and does
 * not depend on which locale the deployment serves.
 */

const FILE = "e2e/qoder-ordA-basemap-attribution-on-glass.spec.ts";
const WIDTHS = [320, 360, 390, 414];
const HOST = "tile.openstreetmap.org";

async function enterMap(page: Page): Promise<void> {
  await ensureDemoJourney(page);
  await openScreen(page, "/v8/hub", ["today-heading", "today-attention"]);
  await page.getByTestId("nav-map").click();
  await expect(page.getByTestId("v8-maplibre-panel").first()).toBeVisible({ timeout: 25_000 });
  await page.waitForTimeout(1_200);
}

async function readGlass(page: Page) {
  return page.evaluate((host: string) => {
    const bodyText = document.body.innerText || "";
    const el = document.querySelector<HTMLElement>("[data-testid='v8-map-attribution']");
    const panel = document.querySelector<HTMLElement>(".v8-map-panel");
    const hint = document.querySelector<HTMLElement>("[data-testid='v8-map-gesture-hint']");
    const out: Record<string, unknown> = {
      locale: document.documentElement.lang || null,
      innerTextHasHost: bodyText.includes(host),
      // every painted occurrence of the notice text, counted in the body string itself
      hostOccurrences: (bodyText.match(new RegExp(host.replace(/\./g, "\\."), "g")) || []).length,
      noticePresent: !!el,
    };
    if (!el || !panel) return out;
    const r = el.getBoundingClientRect();
    const pr = panel.getBoundingClientRect();
    const cs = getComputedStyle(el);
    out.noticeText = el.textContent?.trim() ?? "";
    out.box = { x: Math.round(r.x), y: Math.round(r.y), w: Math.round(r.width), h: Math.round(r.height) };
    out.insidePanel =
      r.left >= pr.left - 1 && r.right <= pr.right + 1 &&
      r.top >= pr.top - 1 && r.bottom <= pr.bottom + 1;
    out.clippedX = el.scrollWidth - el.clientWidth;
    out.clippedY = el.scrollHeight - el.clientHeight;
    out.pointerEvents = cs.pointerEvents;
    out.pageScrollW = document.documentElement.scrollWidth;
    out.winW = window.innerWidth;
    if (hint) {
      const hr = hint.getBoundingClientRect();
      const w = Math.min(r.right, hr.right) - Math.max(r.left, hr.left);
      const h = Math.min(r.bottom, hr.bottom) - Math.max(r.top, hr.top);
      out.overlapWithHintPx2 = w > 0 && h > 0 ? Math.round(w * h) : 0;
    }
    return out;
  }, HOST);
}

const rows: Record<string, unknown>[] = [];

for (const width of WIDTHS) {
  test(`attribution-on-glass @${width} — provider name readable in body.innerText`, async ({
    page,
  }) => {
    await page.setViewportSize({ width, height: 844 });
    await enterMap(page);
    const m = await readGlass(page);
    const shot = evidencePath("ord0042-attribution", `glass_${width}.png`);
    await page.screenshot({ path: shot });
    rows.push({ width, ...m, shot });

    expect(m.innerTextHasHost, `body.innerText must contain ${HOST}`).toBe(true);
    expect(m.hostOccurrences, "at least one painted occurrence").toBeGreaterThan(0);
    expect(m.noticePresent, "the notice element exists").toBe(true);
    expect(m.insidePanel, "notice stays inside the map panel bounds").toBe(true);
    expect(m.clippedX, "not clipped horizontally").toBeLessThanOrEqual(0);
    expect(m.clippedY, "not clipped vertically").toBeLessThanOrEqual(0);
    expect(m.pointerEvents, "read-only: must not swallow a map gesture").toBe("none");
    expect(m.overlapWithHintPx2, "must not sit under the gesture bubble").toBe(0);
    expect(m.pageScrollW, "no horizontal page scroll added").toBeLessThanOrEqual(
      (m.winW as number) + 1,
    );
  });
}

test(`attribution-on-glass @390 zh — the notice survives the language switch`, async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await enterMap(page);
  /* The commander's own before-reading was taken on the Chinese screen, so the Chinese arm is the
     one that has to be proven on glass; the four width arms above land on the seeded English
     state. Both arms carry `tile.openstreetmap.org` verbatim, which is what the assertion pins. */
  await page.getByTestId("topbar-language").click();
  await expect(page.getByTestId("v8-maplibre-panel").first()).toBeVisible({ timeout: 25_000 });
  await page.waitForTimeout(1_200);
  const m = await readGlass(page);
  const shot = evidencePath("ord0042-attribution", "glass_390_zh.png");
  await page.screenshot({ path: shot });
  rows.push({ width: 390, locale: "zh-toggle", ...m, shot });

  expect(m.innerTextHasHost, `body.innerText must contain ${HOST}`).toBe(true);
  expect(m.noticePresent).toBe(true);
  expect(m.insidePanel).toBe(true);
  expect(m.clippedY, "not clipped vertically").toBeLessThanOrEqual(0);
  expect(m.overlapWithHintPx2, "must not sit under the gesture bubble").toBe(0);
  expect(String(m.noticeText)).toContain("底图数据");
});

test.afterAll(() => {
  writeFileSync(
    evidencePath("ord0042-attribution", "glass_reading.json"),
    JSON.stringify({ file: FILE, host: HOST, widths: WIDTHS, rows }, null, 1),
  );
});
