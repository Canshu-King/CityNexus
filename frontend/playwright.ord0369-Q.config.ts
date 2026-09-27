/* ORD-0369 (lane Q) — the phone replan chain, walked and judged at 390x844.
 *
 * The spec talks to a backend this lane started itself (own port, own `Connection.backup()` copy of
 * the preview DB), because the states it asserts -- expired frozen evidence, a plan whose five
 * activities are all protected, a 422 whose detail names the leg -- only exist on a real seeded
 * journey. `CITYNEXUS_BACKEND_PORT` is required rather than defaulted: a panel that silently
 * proxies to `:8000` would be measuring somebody else's decision.
 *
 * Not the acceptance gate: `playwright.config.ts` stays the only thing that can sign one.
 * Usage: python -X utf8 D:/moodle/_qoder_q_ord0369_wk/run_e2e_r1.py
 */
import { defineConfig } from "@playwright/test";

const frontendPort = Number(process.env.CITYNEXUS_ORD0369_PORT ?? 4206);
const backendPort = Number(process.env.CITYNEXUS_BACKEND_PORT ?? "");
if (!Number.isInteger(backendPort) || backendPort < 1024) {
  throw new Error(
    "[ord0369] CITYNEXUS_BACKEND_PORT must name the backend this lane started; refusing to proxy anywhere else",
  );
}

export default defineConfig({
  testDir: "./e2e",
  testMatch: process.env.CITYNEXUS_ORD0369_MATCH
    ? new RegExp(process.env.CITYNEXUS_ORD0369_MATCH)
    : /qoder-ord0369-.*\.spec\.ts/,
  timeout: 240_000,
  expect: { timeout: 30_000 },
  reporter: [
    ["list"],
    ["json", { outputFile: process.env.CITYNEXUS_ORD0369_REPORT
      /* Named by the runner so the report does not land in the tracked tree. */
      ?? "D:/moodle/_qoder_q_ord0369_wk/report-ord0369.json" }],
  ],
  use: {
    baseURL: `http://127.0.0.1:${frontendPort}`,
    viewport: { width: 390, height: 844 },
    hasTouch: true,
    locale: "zh-CN",
  },
  webServer: {
    command: `npm run dev -- --host 127.0.0.1 --port ${frontendPort}`,
    port: frontendPort,
    reuseExistingServer: false,
    timeout: 150_000,
    stdout: "pipe",
    stderr: "pipe",
  },
});
