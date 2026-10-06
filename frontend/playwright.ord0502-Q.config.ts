/* ORD-0502 (lane cff87c64) — the phone mainline, walked against THIS lane's own stack.
 *
 * There is deliberately no webServer here. The backend is a uvicorn this lane started on
 * `CITYNEXUS_BACKEND_PORT` against its own fresh SQLite file (one run id per attempt), and the
 * frontend is a dev server this lane started on `CITYNEXUS_E2E_PORT`; the `server.proxy` entry in
 * `frontend/vite.config.ts`
 * resolves `/api/v1` from `CITYNEXUS_BACKEND_PORT`, so the browser can only ever reach the server
 * this invocation owns. Both ports are required rather than defaulted: a chain walked over
 * somebody else's journey is not this lane's evidence, and `:8000` is a standing 不提供 at this
 * generation.
 *
 * Service workers are blocked so a precache left by an earlier run cannot answer for this one.
 *
 * Not the acceptance gate: `playwright.config.ts` stays the only thing that can sign one.
 * Usage: python -X utf8 review/ord0502/run_ord0502_stack_r1.py
 */
import { defineConfig } from "@playwright/test";

const frontendPort = Number(process.env.CITYNEXUS_E2E_PORT ?? "");
const backendPort = Number(process.env.CITYNEXUS_BACKEND_PORT ?? "");
for (const [name, value] of [
  ["CITYNEXUS_E2E_PORT", frontendPort],
  ["CITYNEXUS_BACKEND_PORT", backendPort],
] as const) {
  if (!Number.isInteger(value) || value < 1024) {
    throw new Error(
      `[ord0502] ${name} must name the service this lane started; refusing to walk anywhere else`,
    );
  }
}
if (frontendPort === backendPort) {
  throw new Error("[ord0502] frontend and backend ports must differ");
}
for (const [name, value] of [
  ["CITYNEXUS_E2E_PORT", frontendPort],
  ["CITYNEXUS_BACKEND_PORT", backendPort],
] as const) {
  if ([8000, 4781, 4782, 8693].includes(value)) {
    throw new Error(`[ord0502] ${name} may not be ${value}: that port belongs to another stack`);
  }
}

export default defineConfig({
  testDir: "./e2e",
  testMatch: /qoder-ord0502-.*\.spec\.ts/,
  timeout: 420_000,
  expect: { timeout: 20_000 },
  workers: 1,
  reporter: [
    ["list"],
    ["json", { outputFile: process.env.CITYNEXUS_ORD0502_REPORT
      /* Named outside the tracked tree by the runner: a gate run must leave the checkout
         byte-identical, and an artefact "deleted afterwards" is not the same thing. */
      ?? "D:/moodle/_ord0502/report.json" }],
  ],
  use: {
    baseURL: `http://127.0.0.1:${frontendPort}`,
    viewport: { width: 390, height: 844 },
    hasTouch: true,
    locale: "zh-CN",
    serviceWorkers: "block",
  },
});
