/* ORD-0529 (lane 8e5245f0) — the unscheduled-trip cell, walked against this lane's own stack.
 *
 * No webServer on purpose: the surface is the bundle this tree built, served by this lane's
 * `vite preview` on CITYNEXUS_ORD0529_PORT, and the API is a uvicorn this lane started on
 * CITYNEXUS_BACKEND_PORT against its own copy of a seeded store.  Both ports are required rather
 * than defaulted -- a reading taken over somebody else's journey is not this lane's evidence, and a
 * bundle left in the directory from an older head would otherwise pass for a new one.
 *
 * Not the acceptance gate: `playwright.config.ts` stays the only thing that can sign one.
 */
import { defineConfig } from "@playwright/test";

const frontendPort = Number(process.env.CITYNEXUS_ORD0529_PORT ?? "");
const backendPort = Number(process.env.CITYNEXUS_BACKEND_PORT ?? "");
for (const [name, value] of [
  ["CITYNEXUS_ORD0529_PORT", frontendPort],
  ["CITYNEXUS_BACKEND_PORT", backendPort],
]) {
  if (!Number.isInteger(value) || value < 1024) {
    throw new Error(`[ord0529] ${name} must name the service this lane started; refusing anywhere else`);
  }
}

export default defineConfig({
  testDir: "./e2e",
  testMatch: /qoder-ord0529-.*\.spec\.ts/,
  timeout: 300_000,
  expect: { timeout: 30_000 },
  reporter: [
    ["list"],
    ["json", { outputFile: process.env.CITYNEXUS_ORD0529_REPORT }],
  ],
  use: {
    baseURL: `http://127.0.0.1:${frontendPort}`,
    viewport: { width: 390, height: 844 },
    hasTouch: true,
    locale: "zh-CN",
  },
});
