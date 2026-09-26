/* ORD-0353 (lane S1) -- the create-failure screen gets a technical-detail fold, and the fold holds
 * only what this device measured plus the server's own recitable number.
 * Vite serves the product; the two POST legs the wizard makes are answered here so both receipt
 * shapes can be put on the same screen.  Not the acceptance gate.
 */
import { defineConfig } from "@playwright/test";
const port = Number(process.env.CITYNEXUS_ORD0353_PORT ?? 4201);
export default defineConfig({
  testDir: "./e2e",
  testMatch: /qoder-ord0353-.*.spec.ts/,
  timeout: 180_000,
  expect: { timeout: 15_000 },
  reporter: [["list"]],
  use: { baseURL: `http://127.0.0.1:${port}`, viewport: { width: 390, height: 844 }, hasTouch: true },
  webServer: {
    command: `npm run dev -- --host 127.0.0.1 --port ${port}`,
    port,
    reuseExistingServer: false,
    timeout: 120_000,
    stdout: "pipe",
    stderr: "pipe",
  },
});
