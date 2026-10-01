/* ORD-0535 (lane 82f55d8a) -- the recycle-bin row is judged on this lane's own dev server, in front
 * of this lane's own backend and this lane's own sqlite.
 *
 * Like ORD-0445's and ORD-0517's, this config starts nothing: both ends have to be named by the
 * runner, because a front that silently proxied to `:8000` would be judging somebody else's bin.
 * The shared ports are refused here rather than trusted to the caller.
 *
 * Not the acceptance gate: `playwright.config.ts` stays the only thing that can sign one.
 */
import { defineConfig } from "@playwright/test";

const frontendPort = Number(process.env.CITYNEXUS_ORD0535_PORT ?? "");
const backendPort = Number(process.env.CITYNEXUS_BACKEND_PORT ?? "");
if (!Number.isInteger(frontendPort) || frontendPort < 1024) {
  throw new Error(
    "[ord0535] CITYNEXUS_ORD0535_PORT must name the vite server this lane started over its own tree",
  );
}
if (!Number.isInteger(backendPort) || backendPort < 1024) {
  throw new Error("[ord0535] CITYNEXUS_BACKEND_PORT must name the backend this lane started");
}
for (const [name, value] of [
  ["CITYNEXUS_ORD0535_PORT", frontendPort],
  ["CITYNEXUS_BACKEND_PORT", backendPort],
] as const) {
  if ([8000, 4781, 4782, 8693].includes(value)) {
    throw new Error(`[ord0535] ${name}=${value} is a shared port, and this order may not touch it`);
  }
}

export default defineConfig({
  testDir: "./e2e",
  testMatch: process.env.CITYNEXUS_ORD0535_MATCH
    ? new RegExp(process.env.CITYNEXUS_ORD0535_MATCH)
    : /qoder-82f55d8a-ord0535-.*\.spec\.ts/,
  timeout: 300_000,
  expect: { timeout: 30_000 },
  reporter: [
    ["list"],
    ["json", { outputFile: process.env.CITYNEXUS_ORD0535_REPORT ?? "ord0535-report.json" }],
  ],
  use: {
    baseURL: `http://127.0.0.1:${frontendPort}`,
    viewport: { width: 390, height: 844 },
    hasTouch: true,
    locale: "zh-CN",
  },
});
