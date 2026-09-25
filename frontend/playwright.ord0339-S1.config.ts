/* ORD-0339 (lane S1) — a two-arm DOM check for the sealed-demo alert, run against the vite dev
 * server with every /api answer stubbed inside the spec, because the state under test is *caused*
 * by a broken read and no backend fact is being claimed here.
 *
 * Not the acceptance gate: `playwright.config.ts` stays the only thing that can sign one, and this
 * config deliberately starts no backend so it cannot borrow a neighbour's (pass-12's lesson).
 * Usage:  npx playwright test -c playwright.ord0339-S1.config.ts
 */
import { defineConfig } from "@playwright/test";

const frontendPort = Number(process.env.CITYNEXUS_ORD0339_PORT ?? 4193);

export default defineConfig({
  testDir: "./e2e",
  testMatch: /qoder-ord0339-.*\.spec\.ts/,
  timeout: 240_000,
  expect: { timeout: 20_000 },
  reporter: [["list"], ["json", { outputFile: "report-ord0339.json" }]],
  use: {
    baseURL: `http://127.0.0.1:${frontendPort}`,
    viewport: { width: 390, height: 844 },
    hasTouch: true,
  },
  webServer: {
    command: `npm run dev -- --host 127.0.0.1 --port ${frontendPort}`,
    port: frontendPort,
    reuseExistingServer: false,
    timeout: 120_000,
    stdout: "pipe",
    stderr: "pipe",
  },
});
