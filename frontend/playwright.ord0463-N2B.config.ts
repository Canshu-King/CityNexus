/* ORD-0463 (lane N2B) -- the screenshot shell, judged on this lane's own built bundle over this
 * lane's own backend. The config starts nothing: both ends are named by the runner, because the front
 * being judged is the built bundle, and a front that silently proxied to `:8000` would be measuring
 * somebody else's data.
 *
 * Not the acceptance gate: `playwright.config.ts` stays the only thing that can sign one.
 */
import { defineConfig } from "@playwright/test";

const frontendPort = Number(process.env.CITYNEXUS_N2B_0463_PORT ?? "");
const backendPort = Number(process.env.CITYNEXUS_BACKEND_PORT ?? "");
if (!Number.isInteger(frontendPort) || frontendPort < 1024) {
  throw new Error("[n2b-0463] CITYNEXUS_N2B_0463_PORT must name this lane's vite preview");
}
if (!Number.isInteger(backendPort) || backendPort < 1024) {
  throw new Error("[n2b-0463] CITYNEXUS_BACKEND_PORT must name this lane's backend");
}

export default defineConfig({
  testDir: "./e2e",
  testMatch: process.env.CITYNEXUS_N2B_0463_MATCH
    ? new RegExp(process.env.CITYNEXUS_N2B_0463_MATCH)
    : /qoder-ord0463-.*\.spec\.ts/,
  timeout: 240_000,
  expect: { timeout: 30_000 },
  reporter: [
    ["list"],
    [
      "json",
      {
        outputFile:
          process.env.CITYNEXUS_N2B_0463_REPORT ??
          "D:/moodle/_qoder_n2b_ord0463_20260929/report-r1.json",
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
