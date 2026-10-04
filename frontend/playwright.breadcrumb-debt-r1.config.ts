/* Breadcrumb route-debt ruler (lane 82f55d8a) — the private runner for
 * `e2e/qoder-82f55d8a-breadcrumb-route-debt-r1.spec.ts`.
 *
 * It starts nothing and listens on nothing: the ruler reads three source files off disk, so it runs on a bare
 * checkout with no backend, no front end and no store. There is deliberately no webServer and no port to
 * default — a lane that points this at a shared port has changed what is being measured.
 *
 * Not the acceptance gate: `playwright.config.ts` stays the only thing that can sign one.
 */
import { defineConfig } from "@playwright/test";

export default defineConfig({
  testDir: "./e2e",
  testMatch: /qoder-82f55d8a-breadcrumb-route-debt-.*\.spec\.ts/,
  timeout: 120_000,
  reporter: [
    ["list"],
    ["json", { outputFile: process.env.CITYNEXUS_BREADCRUMB_REPORT ?? "reports/breadcrumb-route-debt/report.json" }],
  ],
});
