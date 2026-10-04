/* ORD-0562 English counted-noun ruler (lane cff87c64) — the private runner for
 * `e2e/qoder-cff87c64-ord0562-english-count-nouns-r1.spec.ts`.
 *
 * It starts nothing and listens on nothing: the ruler reads the dictionary, plural.ts and the hub, so
 * it works on a bare checkout with no backend, no front and no store. There is deliberately no webServer
 * and no port variable to default — a lane that points this at a shared port has changed what is measured.
 *
 * Not the acceptance gate: `playwright.config.ts` stays the only thing that can sign one.
 */
import { defineConfig } from "@playwright/test";

export default defineConfig({
  testDir: "./e2e",
  testMatch: /qoder-cff87c64-ord0562-english-count-nouns-.*\.spec\.ts/,
  timeout: 120_000,
  reporter: [["list"], ["json", { outputFile: process.env.CITYNEXUS_COUNT_REPORT }]],
});
