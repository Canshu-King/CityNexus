/* ORD-0386 (lane Q) — the plan-version history screen, judged at 390x844.
 *
 * This config starts nothing. Both ends have to be named by the runner, because the front that is
 * judged here must be the *built bundle* (`vite preview` over the export's `dist`), not a dev server
 * that would compile from source at request time -- an unbuilt front cannot show what actually ships.
 * The backend port is required rather than defaulted for the same reason: a panel that silently
 * proxied to `:8000` would be measuring somebody else's data.
 *
 * Not the acceptance gate: `playwright.config.ts` stays the only thing that can sign one.
 */
import { defineConfig } from "@playwright/test";

const frontendPort = Number(process.env.CITYNEXUS_ORD0386_PORT ?? "");
const backendPort = Number(process.env.CITYNEXUS_BACKEND_PORT ?? "");
if (!Number.isInteger(frontendPort) || frontendPort < 1024) {
  throw new Error(
    "[ord0386] CITYNEXUS_ORD0386_PORT must name the vite preview this lane started over its own built bundle",
  );
}
if (!Number.isInteger(backendPort) || backendPort < 1024) {
  throw new Error(
    "[ord0386] CITYNEXUS_BACKEND_PORT must name the backend this lane started; refusing to proxy anywhere else",
  );
}

export default defineConfig({
  testDir: "./e2e",
  testMatch: process.env.CITYNEXUS_ORD0386_MATCH
    ? new RegExp(process.env.CITYNEXUS_ORD0386_MATCH)
    : /qoder-ord0386-.*\.spec\.ts/,
  timeout: 240_000,
  expect: { timeout: 30_000 },
  reporter: [
    ["list"],
    ["json", { outputFile: process.env.CITYNEXUS_ORD0386_REPORT ?? "D:/moodle/_qoder_q_ord0369_wk/report-ord0386.json" }],
  ],
  use: {
    baseURL: `http://127.0.0.1:${frontendPort}`,
    viewport: { width: 390, height: 844 },
    hasTouch: true,
    locale: "zh-CN",
  },
});
