/* ORD-0349 (lane S1) -- the two sealed-demo legs, told apart on screen and in pixels.
 * Served by vite dev because the fixture imports product modules; no backend, because neither claim
 * is about what a server said -- both are about which sentence this device is allowed to print. */
import { defineConfig } from "@playwright/test";
const port = Number(process.env.CITYNEXUS_ORD0349_PORT ?? 4195);
export default defineConfig({
  testDir: "./e2e",
  testMatch: /qoder-ord0349-.*\.spec\.ts/,
  timeout: 180_000,
  expect: { timeout: 15_000 },
  reporter: [["list"]],
  use: { baseURL: `http://127.0.0.1:${port}`, viewport: { width: 390, height: 844 }, hasTouch: true },
  webServer: {
    command: `npm run dev -- --host 127.0.0.1 --port ${port}`,
    port, reuseExistingServer: false, timeout: 120_000, stdout: "pipe", stderr: "pipe",
  },
});
