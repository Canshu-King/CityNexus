/* ORD-0545 slice 4 -- the POI import screen walkthrough (CMDR 01:24, line `6a773af1`).
 *
 * Its own testMatch (`qoder-ord0545s4-`) so this run cannot move slice 2's three-arm or slice 3's
 * three-arm denominators, its own frontend port, and the same lane backend the other two gates share.
 */
import { defineConfig } from "@playwright/test";

const frontendPort = Number(process.env.CITYNEXUS_ORD0545S4_PORT ?? 4916);
const backendPort = Number(process.env.CITYNEXUS_ORD0545_BACKEND_PORT ?? 4911);

export default defineConfig({
  testDir: "./e2e",
  testMatch: /qoder-ord0545s4-.*\.spec\.ts/,
  timeout: 300_000,
  expect: { timeout: 20_000 },
  fullyParallel: false,
  workers: 1,
  reporter: [
    ["list"],
    [
      "json",
      {
        outputFile: `../review/ord0545/readouts/report_ord0545s4_${
          process.env.CITYNEXUS_ORD0545_TAG ?? "r1"
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
    /* --strictPort is the whole point: without it vite silently moves to the next free port, this probe
     * keeps polling a port that a DIFFERENT process owns, and a two-second collision looks like a
     * six-minute hang.  Measured that way round: the stall I was told to explain. */
    command: `node node_modules/vite/bin/vite.js --host 127.0.0.1 --port ${frontendPort} --strictPort`,
    port: frontendPort,
    reuseExistingServer: false,
    timeout: 90_000,
    env: { CITYNEXUS_BACKEND_PORT: String(backendPort) },
  },
});
