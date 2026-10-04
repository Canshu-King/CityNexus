/* ORD-0545 slice six -- the two retaken cells on real glass.
 *
 * Its own testMatch (`qoder-ord0545s6-`) so this run cannot move slice 2/3/4/5's denominators, its own
 * frontend port, and the same lane backend the other gates share. `--strictPort` plus `port:` are
 * load-bearing (bought with a stall: without them vite drifts to a free port and the readiness probe
 * polls a FOREIGN process).
 */
import { defineConfig } from "@playwright/test";

const frontendPort = Number(process.env.CITYNEXUS_ORD0545S6_PORT ?? 4936);
const backendPort = Number(process.env.CITYNEXUS_ORD0545_BACKEND_PORT ?? 4931);

export default defineConfig({
  testDir: "./e2e",
  testMatch: /qoder-ord0545s6-.*\.spec\.ts/,
  timeout: 180_000,
  expect: { timeout: 20_000 },
  fullyParallel: false,
  workers: 1,
  reporter: [
    ["list"],
    ["json", { outputFile: `../review/ord0545/readouts/report_ord0545s6_${process.env.CITYNEXUS_ORD0545_TAG ?? "s6r1"}.json` }],
  ],
  use: {
    baseURL: `http://127.0.0.1:${frontendPort}`,
    viewport: { width: 390, height: 844 },
    hasTouch: true,
  },
  webServer: {
    command: `node node_modules/vite/bin/vite.js --host 127.0.0.1 --port ${frontendPort} --strictPort`,
    port: frontendPort,
    reuseExistingServer: false,
    timeout: 90_000,
    env: { CITYNEXUS_BACKEND_PORT: String(backendPort) },
  },
});
