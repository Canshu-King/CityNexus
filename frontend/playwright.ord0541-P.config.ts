/* ORD-0541 (lane e766b154) — the poster share outlet writes once, judged on the requests it makes.
 *
 * One front, named by the runner: `candidate` for this order's build, `base` for the generation it was
 * cut from (which writes before it asks), `mutant` for the bundle whose reuse predicate ignores the
 * tier (which would hand over a PUBLIC row as if it were this screen's link). The ruler does not
 * change between the three, which is the only reason a red on the mutant means anything.
 *
 * No webServer, and the port is required rather than defaulted.
 * Not the acceptance gate: `playwright.config.ts` stays the only thing that can sign one.
 */
import { defineConfig } from "@playwright/test";

for (const name of ["CITYNEXUS_ORD0541_FRONT"] as const) {
  const value = Number(process.env[name] ?? "");
  if (!Number.isInteger(value) || value < 1024) {
    throw new Error(`[ord0541] ${name} must name a front this lane started`);
  }
}

export default defineConfig({
  testDir: "./e2e",
  testMatch: /qoder-ord0541-.*\.spec\.ts/,
  timeout: 420_000,
  expect: { timeout: 30_000 },
  reporter: [["list"], ["json", { outputFile: process.env.CITYNEXUS_ORD0541_REPORT }]],
  use: { viewport: { width: 390, height: 844 }, hasTouch: true, locale: "zh-CN", actionTimeout: 20_000 },
});
