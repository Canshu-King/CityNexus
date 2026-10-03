/* ORD-0551 extraction-status wording ruler (lane cff87c64) — the private runner for
 * `e2e/qoder-cff87c64-ord0551-extraction-status-vocabulary-r1.spec.ts`.
 *
 * It starts nothing and listens on nothing: the ruler reads three source files, so it works on a bare
 * checkout with no backend, no front and no store. There is deliberately no webServer and no port variable
 * to default — a lane that points this at a shared port has changed what is being measured.
 *
 * Not the acceptance gate: `playwright.config.ts` stays the only thing that can sign one.
 */
import { defineConfig } from "@playwright/test";

export default defineConfig({
  testDir: "./e2e",
  testMatch: /qoder-cff87c64-ord0551-extraction-status-vocabulary-.*\.spec\.ts/,
  timeout: 120_000,
  reporter: [["list"], ["json", { outputFile: process.env.CITYNEXUS_EXSTAT_REPORT }]],
});
