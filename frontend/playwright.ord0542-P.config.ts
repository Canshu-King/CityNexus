/* ORD-0542 (lane e766b154) -- the guest poster's day line, judged against two real bundles.
 *
 * `CANDIDATE` serves this order's build, `BASE` serves the tip it was cut from -- the generation
 * where the receiving screen printed 「天数未知」 on one line and a counted 「2 天」 on the next. The
 * counterexample is therefore not a stub: it is the previous generation's own bytes.
 *
 * No webServer, and both ports are required rather than defaulted.
 * Not the acceptance gate: `playwright.config.ts` stays the only thing that can sign one.
 */
import { defineConfig } from "@playwright/test";

for (const name of [
  "CITYNEXUS_ORD0542_CANDIDATE_PORT",
  "CITYNEXUS_ORD0542_BASE_PORT",
] as const) {
  const value = Number(process.env[name] ?? "");
  if (!Number.isInteger(value) || value < 1024) {
    throw new Error(`[ord0542] ${name} must name a front this lane started`);
  }
}

export default defineConfig({
  testDir: "./e2e",
  testMatch: /qoder-ord0542-.*\.spec\.ts/,
  timeout: 420_000,
  expect: { timeout: 30_000 },
  reporter: [["list"], ["json", { outputFile: process.env.CITYNEXUS_ORD0542_REPORT }]],
  use: { viewport: { width: 390, height: 844 }, hasTouch: true, locale: "zh-CN", actionTimeout: 20_000 },
});
