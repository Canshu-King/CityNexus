/* Runtime-identity wording ruler (lane cmdra) — the private runner for
 * `e2e/qoder-cmdra-runtime-identity-vocabulary-r1.spec.ts`, in the shape lane 82f55d8a shipped for the
 * hub quality family.
 *
 * It starts nothing and listens on nothing: the ruler it runs reads four source files, so it works on a
 * bare checkout with no backend, no front and no store. There is deliberately no webServer and no port
 * variable to default — a lane that points this at a shared port has changed what is being measured.
 *
 * Not the acceptance gate: `playwright.config.ts` stays the only thing that can sign one.
 */
import { defineConfig } from "@playwright/test";

export default defineConfig({
  testDir: "./e2e",
  testMatch: /qoder-cmdra-runtime-identity-vocabulary-.*\.spec\.ts/,
  timeout: 120_000,
  reporter: [["list"], ["json", { outputFile: process.env.CITYNEXUS_RUNTIMEQ_REPORT }]],
});
