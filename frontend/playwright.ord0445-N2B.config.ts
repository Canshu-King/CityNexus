/* ORD-0445 (lane N2B) -- the 待规划 screen, judged on this lane's own built bundle over this lane's
 * own backend.
 *
 * This config starts nothing, the way ORD-0386's does: both ends have to be named by the runner,
 * because the front being judged is the built bundle (`vite preview` over this lane's `dist`), and a
 * front that silently proxied to `:8000` would be measuring somebody else's data.
 *
 * Not the acceptance gate: `playwright.config.ts` stays the only thing that can sign one.
 */
import { defineConfig } from "@playwright/test";

const frontendPort = Number(process.env.CITYNEXUS_N2B_PORT ?? "");
const backendPort = Number(process.env.CITYNEXUS_BACKEND_PORT ?? "");
if (!Number.isInteger(frontendPort) || frontendPort < 1024) {
  throw new Error(
    "[n2b] CITYNEXUS_N2B_PORT must name the vite preview this lane started over its own built bundle",
  );
}
if (!Number.isInteger(backendPort) || backendPort < 1024) {
  throw new Error("[n2b] CITYNEXUS_BACKEND_PORT must name the backend this lane started");
}

export default defineConfig({
  testDir: "./e2e",
  testMatch: process.env.CITYNEXUS_N2B_MATCH
    ? new RegExp(process.env.CITYNEXUS_N2B_MATCH)
    : /qoder-ord0445-.*\.spec\.ts/,
  timeout: 300_000,
  expect: { timeout: 30_000 },
  reporter: [
    ["list"],
    [
      "json",
      {
        outputFile:
          process.env.CITYNEXUS_N2B_REPORT ??
          "D:/moodle/_qoder_n2b_ord0445_20260929/report-r1.json",
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
