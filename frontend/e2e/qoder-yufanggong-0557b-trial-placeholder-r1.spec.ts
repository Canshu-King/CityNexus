import { expect, test } from "@playwright/test";
import { mkdirSync, writeFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

/* ORD-0557 · the trial form's unnamed-city placeholder.

   `JourneyTrialSetup` painted the word "某地" itself when the server had not
   identified a city, in two places (arrival and departure).  Both now read
   `setup.somePlace`.  The English arm of that same placeholder is a different,
   complete sentence -- "e.g. station or airport" -- which this order does not
   move, so the case asserts both arms in both locales and demands the words the
   form already printed.

   Readings land in review/预防工-0557b/screen_readings_r1.txt, one line per arm. */

const HERE = dirname(fileURLToPath(import.meta.url));
const ARTIFACTS = resolve(HERE, "..", "..", "review/预防工-0557b");
const READOUT = resolve(ARTIFACTS, "screen_readings_r1.txt");

const lines: string[] = [];
function note(text: string) {
  lines.push(text);
  mkdirSync(ARTIFACTS, { recursive: true });
  writeFileSync(READOUT, lines.join("\n") + "\n", "utf-8");
}

/* What each locale must show, written out here rather than derived at runtime: these are
   the strings the form printed before the key existed, copied off the base revision. */
const EXPECTED: Record<string, string> = {
  "zh-CN": "例如：某地站 / 机场",
  en: "e.g. station or airport",
};

for (const locale of ["zh-CN", "en"] as const) {
  test(`the ${locale} trial form keeps its own placeholder words`, async ({ page }) => {
    test.setTimeout(90_000);
    await page.addInitScript((loc) => {
      localStorage.clear();
      localStorage.setItem("citynexus.locale", loc);
    }, locale);
    await page.setViewportSize({ width: 1280, height: 900 });
    await page.goto("/v8/live");

    const arrival = page.getByTestId("trial-arrival");
    const departure = page.getByTestId("trial-departure");
    await expect(arrival).toBeVisible({ timeout: 30_000 });

    const arrivalPlaceholder = await arrival.getAttribute("placeholder");
    const departurePlaceholder = await departure.getAttribute("placeholder");
    note(
      `[${locale}] trial-arrival placeholder = ${JSON.stringify(arrivalPlaceholder)} ` +
        `(expected ${JSON.stringify(EXPECTED[locale])})`,
    );
    note(
      `[${locale}] trial-departure placeholder = ${JSON.stringify(departurePlaceholder)} ` +
        `(expected ${JSON.stringify(EXPECTED[locale])})`,
    );

    expect(arrivalPlaceholder).toBe(EXPECTED[locale]);
    expect(departurePlaceholder).toBe(EXPECTED[locale]);

    await page
      .getByTestId("trial-step1-body")
      .screenshot({ path: resolve(ARTIFACTS, `placeholder_${locale}_r1.png`) });
    note(`[${locale}] screenshot = review/预防工-0557b/placeholder_${locale}_r1.png`);
  });
}
