/* ORD-0545 slice 2 -- the copy gate for the moved POI-import family.
 *
 * Its own frontend port and its own backend variable, so no other order's run can move it: the first
 * cut of the sibling config read ORD-0525's port name, which is how one gate ends up pointed at
 * another lane's stack.  The backend is this lane's runner (`review/ord0525/lane_stack_r1.py`); this
 * config starts none of its own, because the screen needs a real trip to render.
 */
import { defineConfig } from "@playwright/test";

const frontendPort = Number(process.env.CITYNEXUS_ORD0545_PORT ?? 4914);
const backendPort = Number(process.env.CITYNEXUS_ORD0545_BACKEND_PORT ?? 4911);

export default defineConfig({
  testDir: "./e2e",
  testMatch: /qoder-ord0545-.*\.spec\.ts/,
  timeout: 240_000,
  expect: { timeout: 20_000 },
  fullyParallel: false,
  workers: 1,
  reporter: [
    ["list"],
    ["json", { outputFile: `../review/ord0545/readouts/report_family_${process.env.CITYNEXUS_ORD0545_TAG ?? "r1"}.json` }],
  ],
  use: {
    baseURL: `http://127.0.0.1:${frontendPort}`,
    viewport: { width: 390, height: 844 },
  },
  webServer: {
    command: `node node_modules/vite/bin/vite.js --host 127.0.0.1 --port ${frontendPort}`,
    url: `http://127.0.0.1:${frontendPort}`,
    reuseExistingServer: false,
    timeout: 180_000,
    env: { CITYNEXUS_BACKEND_PORT: String(backendPort) },
  },
});
