/* ORD-0545 slice 3 -- the refusal-on-glass gate.
 *
 * Its own testMatch (`qoder-ord0545s3-`) so it cannot silently join slice 2's three-arm denominator,
 * and its own frontend port.  The backend is this lane's runner (review/ord0533/lane_stack_r1.py) on
 * the port named by CITYNEXUS_ORD0545_BACKEND_PORT: the walk needs a real server, because the whole
 * point of the slice is a refusal the server itself names.
 */
import { defineConfig } from "@playwright/test";

const frontendPort = Number(process.env.CITYNEXUS_ORD0545S3_PORT ?? 4915);
const backendPort = Number(process.env.CITYNEXUS_ORD0545_BACKEND_PORT ?? 4911);

export default defineConfig({
  testDir: "./e2e",
  testMatch: /qoder-ord0545s3-.*\.spec\.ts/,
  timeout: 240_000,
  expect: { timeout: 20_000 },
  fullyParallel: false,
  workers: 1,
  reporter: [
    ["list"],
    [
      "json",
      {
        outputFile: `../review/ord0545/readouts/report_ord0545s3_${
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
    command: `node node_modules/vite/bin/vite.js --host 127.0.0.1 --port ${frontendPort}`,
    url: `http://127.0.0.1:${frontendPort}`,
    reuseExistingServer: false,
    timeout: 180_000,
    env: { CITYNEXUS_BACKEND_PORT: String(backendPort) },
  },
});
