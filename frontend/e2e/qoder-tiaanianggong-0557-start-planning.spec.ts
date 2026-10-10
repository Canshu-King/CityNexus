/**
 * ORD-0557 (提案工) -- screen proof for the AI sheet's submit label, the one row this lane moved off
 * `zh ? "开始规划" : "Plan my trip"` onto the draft's `planning.startPlanning`.
 *
 * Nothing is forced here: the label is what a traveller sees before pressing 提交, so the arm just
 * opens the real sheet on a seeded journey in each locale and reads the painted button text.  The
 * judgment is equality against the sentence that was on screen before the move.
 */
import { expect, test, type Page } from "@playwright/test";
import { writeFileSync } from "node:fs";
import { evidencePath } from "./_qoderEvidence";

const FILE = "e2e/qoder-tiaanianggong-0557-start-planning.spec.ts";
const node = (id: string, detail: string) => `${FILE} :: ${id} — ${detail}`;
const clean = (value: string | null | undefined) =>
  String(value ?? "").replace(/\s+/g, " ").trim();

const WANT: Record<string, string> = {
  "zh-CN": "开始规划",
  en: "Plan my trip",
};

async function openSheetAndReadSubmitLabel(page: Page, locale: string): Promise<Record<string, unknown>> {
  const scene = (await (await page.request.get("/api/v1/demo/scene")).json()) as { journey_id?: string };
  const journeyId = String(scene.journey_id ?? "");
  expect(journeyId.length > 0, node(locale, "the stage named no journey")).toBe(true);
  await page.addInitScript(
    ([id, lang]) => {
      localStorage.clear();
      localStorage.setItem("citynexus.v8.journey_id", id as string);
      localStorage.setItem("citynexus.locale", lang as string);
    },
    [journeyId, locale],
  );
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/v8/hub", { waitUntil: "load" });
  await expect(page.getByTestId("today-hero"), node(locale, "the hub never rendered")).toBeVisible({
    timeout: 30_000,
  });
  await page.getByTestId("hub-plan-with-ai").click();
  const submit = page.getByTestId("plan-ai-submit");
  await expect(submit, node(locale, "the sheet never mounted its submit control")).toBeVisible();
  /* short enough that the button is not in the busy state -- busy is the other arm's sentence */
  const label = clean(await submit.innerText());
  const busy = (await submit.isDisabled()) === true;
  return { locale, label, busy, aria_disabled: await submit.getAttribute("aria-disabled") };
}

const readings: Record<string, unknown> = {};

for (const locale of ["zh-CN", "en"]) {
  test(`ord0557-submit-label-${locale} planning.startPlanning paints the pre-move label`, async ({ page }) => {
    const read = await openSheetAndReadSubmitLabel(page, locale);
    const want = WANT[locale];
    readings[locale] = { key: "planning.startPlanning", want, read };
    expect(String(read.label), node(locale, `painted label is ${JSON.stringify(read.label)}, not ${JSON.stringify(want)}`)).toBe(want);
    /* the key name must not be what the traveller reads -- that is the failure this order is about */
    expect(String(read.label), node(locale, "a bare dictionary key reached the screen")).not.toMatch(/planning\./);
  });
}

test.afterAll(() => {
  writeFileSync(evidencePath("ord0557_start_planning_readings.json"), JSON.stringify(readings, null, 2));
});
