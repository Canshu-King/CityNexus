/* ORD-0553 execution-status wording ruler (lane 45d25bfb) — the private runner for
 * `e2e/qoder-45d25bfb-authoritative-status-vocabulary-r1.spec.ts`, in the shape of
 * `playwright.hubq-r1.config.ts` and `playwright.runtimeq-r1.config.ts`.
 *
 * It starts nothing and listens on nothing: the ruler it runs reads five source files, so it works on a bare
 * checkout with no backend, no front and no store. There is deliberately no webServer and no port variable
 * to default — a lane that points this at a shared port has changed what is being measured.
 *
 * Not the acceptance gate: `playwright.config.ts` stays the only thing that can sign one.
 */
import { defineConfig } from "@playwright/test";

export default defineConfig({
  testDir: "./e2e",
  testMatch: /qoder-45d25bfb-authoritative-status-vocabulary-.*\.spec\.ts/,
  timeout: 120_000,
  reporter: [["list"], ["json", { outputFile: process.env.CITYNEXUS_STATUSQ_REPORT }]],
});
