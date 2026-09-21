import { expect, type Page } from "@playwright/test";

/**
 * Open the Simulation entry the way a traveller does.
 *
 * ORD-0085 settled the default: on a phone the entry is collapsed, because eleven action rows cannot
 * be laid out past a fixed bottom nav without either sitting in its band (in flow) or keeping
 * overlapping rects while clipped/covered (out of flow).  So any gate that presses a stage action has
 * to open the disclosure first, and it has to do so *instead of* assuming the panel is visible --
 * asserting against a collapsed `<details>` would just hang until the timeout and read as a product
 * failure.
 */
export async function openStageEntry(page: Page, reason: string, timeout = 30_000) {
  const entry = page.getByTestId("sim-entry");
  await expect(
    entry,
    `${reason}: there is no Simulation entry on this screen to open`,
  ).toBeVisible({ timeout });
  if (await entry.evaluate((element) => (element as HTMLDetailsElement).open)) return;
  await page.getByTestId("sim-entry-summary").click();
  await expect(
    entry,
    `${reason}: the entry's summary was pressed and the disclosure never opened`,
  ).toHaveJSProperty("open", true, { timeout });
}

/** The declaration the collapsed line owes the reader, as one string. */
export async function stageDeclaration(page: Page) {
  const text = await page.getByTestId("sim-entry-summary").innerText();
  return text.replace(/\s+/g, " ").trim();
}
