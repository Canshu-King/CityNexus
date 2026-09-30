/* ORD-0533 (lane 6a773af1) -- the copy gate for the POI import screen.
 *
 * Frontend only, like its sibling: the backend is this lane's stack
 * (`review/ord0525/lane_stack_r1.py`) and is reused because the screen needs a real trip to render,
 * not because this order changes any server door.  `testMatch` is scoped to `qoder-0533-*` so this
 * config cannot be mistaken for the authoritative gate, and it starts no backend of its own.
 *
 * Usage:  npx playwright test -c playwright.ord0533-copygate.config.ts
 */
import { defineConfig } from "@playwright/test";

const frontendPort = Number(process.env.CITYNEXUS_ORD0533_PORT ?? 4913);
const backendPort = Number(process.env.CITYNEXUS_ORD0525_BACKEND_PORT ?? 4911);

export default defineConfig({
  testDir: "./e2e",
  testMatch: /qoder-0533-.*\.spec\.ts/,
  timeout: 240_000,
  expect: { timeout: 20_000 },
  fullyParallel: false,
  workers: 1,
  reporter: [
    ["list"],
    [
      "json",
      {
        outputFile: `../review/ord0533/readouts/report_ord0533_${
          process.env.CITYNEXUS_ORD0533_TAG ?? "r3"
        }.json`,
      },
    ],
  ],
  use: {
    baseURL: `http://127.0.0.1:${frontendPort}`,
    viewport: { width: 390, height: 844 },
    hasTouch: true,
  },
  webServer: {
    command: `npm run dev -- --host 127.0.0.1 --port ${frontendPort}`,
    port: frontendPort,
    reuseExistingServer: false,
    timeout: 180_000,
    stdout: "pipe",
    stderr: "pipe",
    env: { CITYNEXUS_BACKEND_PORT: String(backendPort) },
  },
});
