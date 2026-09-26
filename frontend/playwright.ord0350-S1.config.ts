/* ORD-0350 (lane S1) -- the confirmation step's per-item exits, walked on the real wizard.
 * Vite serves the fixture; no backend, because nothing here is about what the API answers.
 * Not the acceptance gate: `playwright.config.ts` stays the only thing that can sign one. */
import { defineConfig } from "@playwright/test";
const port = Number(process.env.CITYNEXUS_ORD0350_PORT ?? 4196);
export default defineConfig({
  testDir: "./e2e",
  testMatch: /qoder-ord0350-.*.spec.ts/,
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
