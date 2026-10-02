/* CMDR 01:24 spend-face screen reading (lane 6a150e1e) -- 390x844 against this lane's own stack.
 *
 * This config starts nothing. The front must be this lane's build of the day24 tree served by this
 * lane's preview, and the API must be this lane's uvicorn over the store this lane seeded, because the
 * numbers on the page are only evidence if the doors behind them are enumerable.
 *
 * Not the acceptance gate: `playwright.config.ts` stays the only thing that can sign one.
 */
import { defineConfig } from "@playwright/test";

const frontendPort = Number(process.env.CITYNEXUS_SPEND_PORT ?? "");
const backendPort = Number(process.env.CITYNEXUS_BACKEND_PORT ?? "");
if (!Number.isInteger(frontendPort) || frontendPort < 1024) {
  throw new Error(
    "[spend] CITYNEXUS_SPEND_PORT must name the vite preview this lane started over its own bundle",
  );
}
if (!Number.isInteger(backendPort) || backendPort < 1024) {
  throw new Error(
    "[spend] CITYNEXUS_BACKEND_PORT must name the backend this lane started; refusing to proxy anywhere else",
  );
}

export default defineConfig({
  testDir: "./e2e",
  testMatch: /qoder-6a150e1e-spend-.*\.spec\.ts/,
  timeout: 240_000,
  expect: { timeout: 30_000 },
  reporter: [
    ["list"],
    [
      "json",
      {
        outputFile:
          process.env.CITYNEXUS_SPEND_REPORT ??
          "D:/moodle/_qoder_6a_ord0531_20261001/report-spend-day24.json",
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
