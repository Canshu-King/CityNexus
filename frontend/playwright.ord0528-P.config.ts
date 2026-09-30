/* ORD-0528 (lane e766b154) — the poster travels with sharing, judged on real artifacts.
 *
 * One front, named by the runner: `candidate` for this order's build, `base` for the generation
 * before it, `mutant` for the bundle whose receiver ignores the address tail. The ruler does not
 * change between the three -- which is the whole point of the counterexample that runs against the
 * mutant: an arm that cannot go red on a screen that confuses the two shapes is not measuring the
 * shapes.
 *
 * No webServer, and the port is required rather than defaulted.
 * Not the acceptance gate: `playwright.config.ts` stays the only thing that can sign one.
 */
import { defineConfig } from "@playwright/test";

for (const name of ["CITYNEXUS_ORD0528_FRONT"] as const) {
  const value = Number(process.env[name] ?? "");
  if (!Number.isInteger(value) || value < 1024) {
    throw new Error(`[ord0528] ${name} must name a front this lane started`);
  }
}

export default defineConfig({
  testDir: "./e2e",
  testMatch: /qoder-ord0528-.*\.spec\.ts/,
  timeout: 420_000,
  expect: { timeout: 30_000 },
  reporter: [["list"], ["json", { outputFile: process.env.CITYNEXUS_ORD0528_REPORT }]],
  use: { viewport: { width: 390, height: 844 }, hasTouch: true, locale: "zh-CN", actionTimeout: 20_000 },
});
