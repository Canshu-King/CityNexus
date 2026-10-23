/* Private runner for the SimulationPanel stage-copy arm (lane 1d64acf5).
 *
 * Starts nothing and listens on nothing: the arm calls the dictionary module and reads source
 * files, so it works on a bare checkout with no backend, no front and no store. There is
 * deliberately no webServer and no port to default -- pointing this at a shared port would change
 * what is being measured.
 *
 * Not the acceptance gate: `playwright.config.ts` stays the only thing that can sign one.
 */
import { defineConfig } from "@playwright/test";

export default defineConfig({
  testDir: "./e2e",
  testMatch: "qoder-1d64acf5-simstage-copy-r1.spec.ts",
  timeout: 120_000,
  reporter: [["list"], ["json", { outputFile: process.env.CITYNEXUS_SIMSTAGE_REPORT }]],
});
