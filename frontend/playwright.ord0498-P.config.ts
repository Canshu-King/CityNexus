/* ORD-0498 (lane e766b154) — the poster's second day, measured on two journeys that differ only
 * by what the product's own write doors did.
 *
 * There is no webServer: the surface is the built bundle of the base commit, served twice --
 * `CITYNEXUS_ORD0498_UNWRITTEN_PORT` fronts a database backup nobody has written to, and
 * `CITYNEXUS_ORD0498_WRITTEN_PORT` fronts the same bundle over the copy where this lane ran
 * `PATCH /journeys/{id}` and `POST /journeys/{id}/poi-import/add`. Both proxies forward to their
 * own backend, so the only difference a reading can see is the second day itself.
 *
 * Not the acceptance gate: `playwright.config.ts` stays the only thing that can sign one.
 */
import { defineConfig } from "@playwright/test";

const unwritten = Number(process.env.CITYNEXUS_ORD0498_UNWRITTEN_PORT ?? "");
const written = Number(process.env.CITYNEXUS_ORD0498_WRITTEN_PORT ?? "");
for (const [name, value] of [
  ["CITYNEXUS_ORD0498_UNWRITTEN_PORT", unwritten],
  ["CITYNEXUS_ORD0498_WRITTEN_PORT", written],
] as const) {
  if (!Number.isInteger(value) || value < 1024) {
    throw new Error(`[ord0498] ${name} must name a front this lane started; refusing anywhere else`);
  }
}

export default defineConfig({
  testDir: "./e2e",
  testMatch: /qoder-ord0498-.*\.spec\.ts/,
  timeout: 300_000,
  expect: { timeout: 30_000 },
  reporter: [["list"], ["json", { outputFile: process.env.CITYNEXUS_ORD0498_REPORT }]],
  use: {
    viewport: { width: 390, height: 844 },
    hasTouch: true,
    locale: "zh-CN",
  },
});
