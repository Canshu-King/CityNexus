/* ORD-0520 (lane 89f2e2d6) -- the last cell of that order: the 中止 sentences read off a real screen.
 *
 * Like ORD-0535's and ORD-0445's, this config starts nothing: both ends have to be named by the
 * runner, because a front that silently proxied to `:8000` would be judging somebody else's trips.
 * The shared ports are refused here rather than trusted to the caller, and the run's own provenance
 * receipt (`review/ord0520/abort_glass_provenance_r1.py`) checks the same ports answered the run id
 * this invocation issued before any arm is allowed to claim a reading.
 *
 * Not the acceptance gate: `playwright.config.ts` stays the only thing that can sign one.
 */
import { defineConfig } from "@playwright/test";

const frontendPort = Number(process.env.CITYNEXUS_ORD0520_PORT ?? "");
const backendPort = Number(process.env.CITYNEXUS_BACKEND_PORT ?? "");
if (!Number.isInteger(frontendPort) || frontendPort < 1024) {
  throw new Error(
    "[ord0520-glass] CITYNEXUS_ORD0520_PORT must name the vite server this lane started over its own tree",
  );
}
if (!Number.isInteger(backendPort) || backendPort < 1024) {
  throw new Error("[ord0520-glass] CITYNEXUS_BACKEND_PORT must name the backend this lane started");
}
for (const [name, value] of [
  ["CITYNEXUS_ORD0520_PORT", frontendPort],
  ["CITYNEXUS_BACKEND_PORT", backendPort],
] as const) {
  if ([8000, 4781, 4782, 8693].includes(value)) {
    throw new Error(`[ord0520-glass] ${name}=${value} is a shared port, and this order may not touch it`);
  }
}

export default defineConfig({
  testDir: "./e2e",
  testMatch: process.env.CITYNEXUS_ORD0520_MATCH
    ? new RegExp(process.env.CITYNEXUS_ORD0520_MATCH)
    : /qoder-89f2e2d6-ord0520-abort-on-the-glass-r1\.spec\.ts/,
  timeout: 300_000,
  expect: { timeout: 30_000 },
  workers: 1,
  reporter: [
    ["list"],
    ["json", { outputFile: process.env.CITYNEXUS_ORD0520_REPORT ?? "ord0520-glass-report.json" }],
  ],
  use: {
    baseURL: `http://127.0.0.1:${frontendPort}`,
    viewport: { width: 390, height: 844 },
    hasTouch: true,
    locale: "zh-CN",
  },
});
