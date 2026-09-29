/* ORD-0472 (lane e766b154) — the trip poster, walked against this lane's own stack.
 *
 * There is deliberately no webServer here: the surface is the built bundle of the pushed tip, served
 * by `cmdr_static_api_proxy_r1.py` on `CITYNEXUS_ORD0472_PORT`, and the API is a uvicorn this lane
 * started on `CITYNEXUS_BACKEND_PORT` against its own `Connection.backup()` copy of a seeded
 * database. Both ports are required rather than defaulted -- a poster drawn over somebody else's
 * journey is not this lane's evidence.
 *
 * Not the acceptance gate: `playwright.config.ts` stays the only thing that can sign one.
 * Usage: python -X utf8 D:/moodle/_qoder_e766b154_ord0472_20260930/tools/run_ord0472_gate_r1.py
 */
import { defineConfig } from "@playwright/test";

const frontendPort = Number(process.env.CITYNEXUS_ORD0472_PORT ?? "");
const backendPort = Number(process.env.CITYNEXUS_BACKEND_PORT ?? "");
for (const [name, value] of [
  ["CITYNEXUS_ORD0472_PORT", frontendPort],
  ["CITYNEXUS_BACKEND_PORT", backendPort],
]) {
  if (!Number.isInteger(value) || value < 1024) {
    throw new Error(`[ord0472] ${name} must name the service this lane started; refusing anywhere else`);
  }
}

export default defineConfig({
  testDir: "./e2e",
  testMatch: /qoder-ord0472-.*\.spec\.ts/,
  timeout: 300_000,
  expect: { timeout: 30_000 },
  reporter: [
    ["list"],
    ["json", { outputFile: process.env.CITYNEXUS_ORD0472_REPORT }],
  ],
  use: {
    baseURL: `http://127.0.0.1:${frontendPort}`,
    viewport: { width: 390, height: 844 },
    hasTouch: true,
    locale: "zh-CN",
  },
});
