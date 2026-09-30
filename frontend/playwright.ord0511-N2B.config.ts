/* ORD-0511 (lane newlane2) -- the stay rung judged at 390x844 on this lane's own stack.
 *
 * This config starts nothing. Both ends must be named by the runner: the front has to be this lane's
 * built bundle served by this lane's `vite preview`, and the API has to be this lane's own uvicorn over
 * this lane's own copy of the store. A panel that silently proxied to `:8000` would be measuring
 * somebody else's data, which is the one thing this order's evidence must not do.
 *
 * Not the acceptance gate: `playwright.config.ts` stays the only thing that can sign one.
 */
import { defineConfig } from "@playwright/test";

const frontendPort = Number(process.env.CITYNEXUS_ORD0511_PORT ?? "");
const backendPort = Number(process.env.CITYNEXUS_BACKEND_PORT ?? "");
if (!Number.isInteger(frontendPort) || frontendPort < 1024) {
  throw new Error(
    "[ord0511] CITYNEXUS_ORD0511_PORT must name the vite preview this lane started over its own bundle",
  );
}
if (!Number.isInteger(backendPort) || backendPort < 1024) {
  throw new Error(
    "[ord0511] CITYNEXUS_BACKEND_PORT must name the backend this lane started; refusing to proxy anywhere else",
  );
}

export default defineConfig({
  testDir: "./e2e",
  testMatch: /qoder-ord0511-.*\.spec\.ts/,
  timeout: 300_000,
  expect: { timeout: 40_000 },
  reporter: [
    ["list"],
    ["json", { outputFile: process.env.CITYNEXUS_ORD0511_REPORT ?? "D:/moodle/_qoder_n2b_ord0511_20260930/report-ord0511.json" }],
  ],
  use: {
    baseURL: `http://127.0.0.1:${frontendPort}`,
    viewport: { width: 390, height: 844 },
    hasTouch: true,
    locale: "zh-CN",
  },
});
