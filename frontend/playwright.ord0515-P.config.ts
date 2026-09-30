/* ORD-0515 (lane e766b154) — the poster's height bound and its pagination, judged on real artifacts.
 *
 * Three fronts, one bundle twice: `SHORT` and `LONG` both serve this order's build over two
 * databases of the same base -- one sealed, one lengthened through the product's own write doors --
 * and `UNBOUNDED` serves the *previous* generation's build over the long database, which is how the
 * counterexample gets a real artifact that lacks the bound instead of a simulated one.
 *
 * No webServer, and every port is required rather than defaulted.
 * Not the acceptance gate: `playwright.config.ts` stays the only thing that can sign one.
 */
import { defineConfig } from "@playwright/test";

for (const name of [
  "CITYNEXUS_ORD0515_SHORT_PORT",
  "CITYNEXUS_ORD0515_LONG_PORT",
  "CITYNEXUS_ORD0515_UNBOUNDED_PORT",
] as const) {
  const value = Number(process.env[name] ?? "");
  if (!Number.isInteger(value) || value < 1024) {
    throw new Error(`[ord0515] ${name} must name a front this lane started`);
  }
}

export default defineConfig({
  testDir: "./e2e",
  testMatch: /qoder-ord0515-.*\.spec\.ts/,
  timeout: 420_000,
  expect: { timeout: 30_000 },
  reporter: [["list"], ["json", { outputFile: process.env.CITYNEXUS_ORD0515_REPORT }]],
  use: { viewport: { width: 390, height: 844 }, hasTouch: true, locale: "zh-CN" },
});
