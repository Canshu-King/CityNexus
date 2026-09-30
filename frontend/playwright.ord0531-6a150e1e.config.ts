/* ORD-0531 (lane 6a150e1e) -- the recycle bin judged from a seat, at 390x844.
 *
 * This config starts nothing: the front must be this lane's built bundle served by this lane's own
 * preview, and the API must be this lane's own uvicorn over this lane's own copy of the store, because
 * the whole order is about who is allowed to see which row.
 *
 * Not the acceptance gate: `playwright.config.ts` stays the only thing that can sign one.
 */
import { defineConfig } from "@playwright/test";

const frontendPort = Number(process.env.CITYNEXUS_ORD0531_PORT ?? "");
const backendPort = Number(process.env.CITYNEXUS_BACKEND_PORT ?? "");
if (!Number.isInteger(frontendPort) || frontendPort < 1024) {
  throw new Error(
    "[ord0531] CITYNEXUS_ORD0531_PORT must name the vite preview this lane started over its own bundle",
  );
}
if (!Number.isInteger(backendPort) || backendPort < 1024) {
  throw new Error(
    "[ord0531] CITYNEXUS_BACKEND_PORT must name the backend this lane started; refusing to proxy anywhere else",
  );
}

export default defineConfig({
  testDir: "./e2e",
  testMatch: /qoder-ord0531-.*\.spec\.ts/,
  timeout: 240_000,
  expect: { timeout: 30_000 },
  reporter: [
    ["list"],
    [
      "json",
      {
        outputFile:
          process.env.CITYNEXUS_ORD0531_REPORT ??
          "D:/moodle/_qoder_6a_ord0531_20261001/report-ord0531.json",
      },
    ],
  ],
  use: {
    baseURL: `http://127.0.0.1:${frontendPort}`,
    viewport: { width: 390, height: 844 },
    hasTouch: true,
    locale: "zh-CN",
  },
});
