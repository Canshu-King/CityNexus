/* Private runner for the recycle-bin name-anchor guard (lane 82f55d8a).
 *
 * Starts nothing and listens on nothing: the arms it runs read source files, so it works on a bare
 * checkout with no backend, no front and no store. There is deliberately no webServer and no port to
 * default -- pointing this at a shared port would change what is being measured.
 *
 * Not the acceptance gate: `playwright.config.ts` stays the only thing that can sign one.
 */
import { defineConfig } from "@playwright/test";

export default defineConfig({
  testDir: "./e2e",
  testMatch: /qoder-82f55d8a-journeytrash-name-anchors-.*\.spec\.ts/,
  timeout: 120_000,
  reporter: [["list"], ["json", { outputFile: process.env.CITYNEXUS_NAMEANCHOR_REPORT }]],
});
