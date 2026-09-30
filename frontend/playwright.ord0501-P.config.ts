/* ORD-0501 (lane e766b154) — the multi-day poster layout, judged on pixels.
 *
 * No webServer: the surface is the built bundle of the base commit served twice over this lane's
 * own backends -- one on a database nobody wrote to, one on the copy where the product's own write
 * doors added a second day. Every port is required rather than defaulted, and the pixel instrument
 * plus its interpreter are named by the runner, because a silent fallback here would grade the
 * wrong file.
 *
 * Not the acceptance gate: `playwright.config.ts` stays the only thing that can sign one.
 */
import { defineConfig } from "@playwright/test";

const needed = [
  "CITYNEXUS_ORD0501_UNWRITTEN_PORT",
  "CITYNEXUS_ORD0501_WRITTEN_PORT",
  "CITYNEXUS_ORD0501_WRITTEN_API",
] as const;
for (const name of needed) {
  const value = Number(process.env[name] ?? "");
  if (!Number.isInteger(value) || value < 1024) {
    throw new Error(`[ord0501] ${name} must name a service this lane started`);
  }
}

export default defineConfig({
  testDir: "./e2e",
  testMatch: /qoder-ord0501-.*\.spec\.ts/,
  timeout: 300_000,
  expect: { timeout: 30_000 },
  reporter: [["list"], ["json", { outputFile: process.env.CITYNEXUS_ORD0501_REPORT }]],
  use: { viewport: { width: 390, height: 844 }, hasTouch: true, locale: "zh-CN" },
});
