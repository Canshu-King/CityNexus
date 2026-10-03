/* ORD-0545 slice 5 -- the two refusals only a device can decide, on real glass.
 *
 * Its own testMatch (`qoder-ord0545s5-`) so this run cannot move slice 2's, slice 3's or slice 4's
 * denominators, its own frontend port, and the same lane backend the other gates share.
 *
 * `--strictPort` plus `port:` are load-bearing and were bought with a stall: without them vite moves to
 * the next free port on its own, the readiness probe keeps polling a port a FOREIGN process owns, and the
 * run reads another tree for minutes instead of failing in under a second.
 */
import { defineConfig } from "@playwright/test";

const frontendPort = Number(process.env.CITYNEXUS_ORD0545S5_PORT ?? 4926);
const backendPort = Number(process.env.CITYNEXUS_ORD0545_BACKEND_PORT ?? 4921);

export default defineConfig({
  testDir: "./e2e",
  testMatch: /qoder-ord0545s5-.*\.spec\.ts/,
  timeout: 180_000,
  expect: { timeout: 20_000 },
  fullyParallel: false,
  workers: 1,
  reporter: [
    ["list"],
    ["json", { outputFile: `../review/ord0545/readouts/report_ord0545s5_${process.env.CITYNEXUS_ORD0545_TAG ?? "s5r1"}.json` }],
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
