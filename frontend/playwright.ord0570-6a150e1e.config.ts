/* ORD-0570 (lane 6a150e1e) -- the topbar avatar's own judge, 390/360/412 against this lane's stack.
 *
 * This config starts nothing, on purpose: the front must be a bundle this lane built and this lane's
 * preview is serving, and the API must be this lane's uvicorn over the store this lane seeded, because
 * an accessible name and a clipped glyph are only evidence if the bytes behind them are enumerable.
 *
 * Not the acceptance gate: `playwright.config.ts` stays the only thing that can sign one.
 */
import { defineConfig } from "@playwright/test";

const frontendPort = Number(process.env.CITYNEXUS_AVT_PORT ?? "");
const backendPort = Number(process.env.CITYNEXUS_BACKEND_PORT ?? "");
if (!Number.isInteger(frontendPort) || frontendPort < 1024) {
  throw new Error(
    "[ord0570] CITYNEXUS_AVT_PORT must name the vite preview this lane started over its own bundle",
  );
}
if (!Number.isInteger(backendPort) || backendPort < 1024) {
  throw new Error("[ord0570] CITYNEXUS_BACKEND_PORT must name the backend this lane started");
}

export default defineConfig({
  testDir: "./e2e",
  testMatch: /qoder-6a150e1e-ord0570-.*\.spec\.ts/,
  timeout: 240_000,
  expect: { timeout: 30_000 },
  reporter: [
    ["list"],
    [
      "json",
      {
        outputFile:
          process.env.CITYNEXUS_AVT_REPORT ??
          "D:/moodle/_qoder_6a_ord0531_20261001/report-ord0570.json",
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
