/**
 * ORD-0555 (lane 复位工-0428) — the panel table's own fold label is read from the dictionary.
 *
 * The row the commander's table gives: `frontend/src/app/v8PanelRegistry.tsx:481` painted
 * `s.zh ? "高级 / 开发者" : "Advanced / developer"` -- an inline bilingual literal sitting in a mount
 * table. It now reads `t("v8panelregistry.advancedDeveloper")`. Two properties must hold, and they are
 * different properties:
 *
 *   N1/N2 the SCREEN still says exactly what it said before, in both locales, and does not fall back
 *      to printing the key itself (`LocaleContext`'s `t` arm answers an unknown key with the key, so a
 *      half-installed key looks like success in the source and a defect on the screen);
 *   N3 the disclosure still opens -- replacing the label must not quietly break the fold it belongs to;
 *   N4 the SOURCE no longer carries the literal pair, which is the half the order is actually about.
 *
 * Readings are painted text (`innerText`), never a `data-*` mirror; the summary is scrolled into the
 * viewport and hit-tested before anything is claimed about it, and the fold is measured closed before
 * it is opened.
 */
import { expect, test, type Page } from "@playwright/test";
import { fileURLToPath } from "node:url";
import { readFileSync, writeFileSync } from "node:fs";

import { evidencePath } from "./_qoderEvidence";

const FILE = "e2e/qoder-fuiweigong-0555-advanced-fold-label-r1.spec.ts";
const node = (id: string, detail: string) => `${FILE} :: ${id} — ${detail}`;
const RUN = process.env.CITYNEXUS_E2E_RUN_ID ?? "dev";
/* Resolved against this file, not against the shell's cwd: the source is the thing being judged.
 * This suite loads specs as ES modules, so `__dirname` is not available here. */
const REGISTRY = fileURLToPath(new URL("../src/app/v8PanelRegistry.tsx", import.meta.url));
const KEY = "v8panelregistry.advancedDeveloper";

const clean = (value: string | null | undefined) =>
  String(value ?? "").replace(/\s+/g, " ").trim();

/** A journey of this lane's own, with nothing behind it: the fold belongs to the bookings panel, not
 *  to any reservation, so an empty trip is the shape that isolates the label. */
async function seedBareJourney(page: Page) {
  const traveler = await (
    await page.request.post("/api/v1/travelers", {
      data: { display_name: "ORD-0555 lane", locale: "zh-CN", timezone: "Asia/Shanghai" },
    })
  ).json();
  const journey = await (
    await page.request.post("/api/v1/journeys", {
      data: {
        traveler_id: traveler.id,
        title: "天津周末",
        city_code: "CN-TIANJIN",
        timezone: "Asia/Shanghai",
        start_at: "2026-10-19T18:00:00+08:00",
        end_at: "2026-10-21T15:00:00+08:00",
        budget: { amount_minor: 120000, currency: "CNY" },
        party_size: 2,
        arrival_anchor: { at: "2026-10-19T18:00:00+08:00", location: "Tianjin West Station" },
        departure_anchor: { at: "2026-10-21T15:00:00+08:00", location: "Tianjin Binhai Airport" },
      },
    })
  ).json();
  return String(journey.id);
}

async function openBookingsFold(page: Page, journeyId: string, locale: string) {
  await page.addInitScript(
    ({ id, loc }) => {
      localStorage.clear();
      localStorage.setItem("citynexus.v8.journey_id", id);
      localStorage.setItem("citynexus.locale", loc);
    },
    { id: journeyId, loc: locale },
  );
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/v8/trips", { waitUntil: "load" });
  await page.getByTestId("trips-tab-bookings").click();
  const fold = page.locator(".trips-advanced").first();
  await expect(fold, node("boot", "the bookings panel never mounted its Advanced disclosure")).toBeAttached({
    timeout: 30_000,
  });
  return fold.locator("summary").first();
}

/** Prove the label is on screen before anything is read off it: scroll it in, then hit-test its centre. */
async function paintedLabel(page: Page, summary: ReturnType<Page["locator"]>, id: string) {
  await summary.scrollIntoViewIfNeeded({ timeout: 5_000 });
  const box = await summary.boundingBox();
  expect(box, node(id, "the summary has no box, so no painted text was measured")).not.toBeNull();
  const hit = await page.evaluate(
    (point) => {
      const el = document.elementFromPoint(point.x, point.y);
      return el ? el.closest("summary") !== null : false;
    },
    { x: (box as { x: number; y: number; width: number; height: number }).x + (box as { width: number }).width / 2,
      y: (box as { x: number; y: number }).y + (box as { height: number }).height / 2 },
  );
  expect(hit, node(id, "the summary's centre hit something else, so the reading is not the screen's")).toBe(true);
  return clean(await summary.innerText());
}

test.describe("ORD-0555 the panel table reads its own fold label from the dictionary", () => {
  for (const arm of [
    { code: "zh", locale: "zh-CN", expect: "高级 / 开发者" },
    { code: "en", locale: "en", expect: "Advanced / developer" },
  ]) {
    test(`ord0555-1-painted-label-${arm.code} — 折叠标签的屏上文字逐字不变`, async ({ page }) => {
      test.setTimeout(180_000);
      const NODE = `ord0555-1-${arm.code}`;
      const journeyId = await seedBareJourney(page);
      const summary = await openBookingsFold(page, journeyId, arm.locale);

      const text = await paintedLabel(page, summary, NODE);
      expect(text, node(NODE, `the fold label painted "${text}", not "${arm.expect}"`)).toBe(arm.expect);
      /* The failure mode this guard exists for: an absent key paints the key. */
      expect(text, node(NODE, "the label slot fell back to printing the dictionary key")).not.toContain(KEY);

      writeFileSync(
        evidencePath(`fuiweigong-0555/label-${arm.code}.json`),
        JSON.stringify({ run: RUN, node: NODE, journey_id: journeyId, painted: text, key: KEY }, null, 2) + "\n",
        "utf-8",
      );
    });
  }

  test("ord0555-2-disclosure-still-opens — 换标签没把折叠换成死控件", async ({ page }) => {
    test.setTimeout(180_000);
    const NODE = "ord0555-2";
    const journeyId = await seedBareJourney(page);
    const summary = await openBookingsFold(page, journeyId, "zh-CN");
    const fold = page.locator(".trips-advanced").first();

    /* Measured closed, before the click: an already-open fold would make the after-reading vacuous. */
    await expect(summary, node(NODE, "the label is not rendered as a <summary> element")).toHaveCount(1);
    expect(await fold.evaluate((el) => (el as HTMLDetailsElement).open),
      node(NODE, "the disclosure was already open, so the open-step below proves nothing")).toBe(false);

    await summary.click();
    await expect(fold, node(NODE, "clicking the new label no longer opens the disclosure"))
      .toHaveClass(/trips-advanced/);
    expect(await fold.evaluate((el) => (el as HTMLDetailsElement).open),
      node(NODE, "the disclosure did not open on the click")).toBe(true);

    writeFileSync(
      evidencePath("fuiweigong-0555/disclosure.json"),
      JSON.stringify({ run: RUN, node: NODE, journey_id: journeyId, opened_by_click: true }, null, 2) + "\n",
      "utf-8",
    );
  });

  test("ord0555-3-source-carries-no-inline-pair — 写死串那半从表里消失了", async () => {
    const NODE = "ord0555-3";
    const src = readFileSync(REGISTRY, "utf-8");
    const inline = src.match(/zh \?|locale === \w|=== "zh-CN"/g) ?? [];
    expect(inline, node(NODE, `the mount table still holds ${JSON.stringify([...new Set(inline)])}`)).toEqual([]);
    expect(src.includes("<TripsAdvancedFoldLabel />"),
      node(NODE, "the label slot does not read through the dictionary arm")).toBe(true);
  });
});
