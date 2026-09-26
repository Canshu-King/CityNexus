/* ORD-0346 (lane S4-ast-taint) — the wizard's 「看支持的目的地」 panel, read against a server.
 *
 * The spec talks to a backend this lane started itself: its own port, its own one-off SQLite, the
 * resolver seam off.  `CITYNEXUS_BACKEND_PORT` is required rather than defaulted, because a panel
 * that silently proxies to `:8000` would be measuring somebody else's decision (that port is a
 * standing "不提供" at this generation).
 *
 * Not the acceptance gate: `playwright.config.ts` stays the only thing that can sign one.
 * Usage: python -X utf8 D:/moodle/_qoder_lane_S4_0926/work/ord0346/run_e2e_r1.py
 */
import { defineConfig } from "@playwright/test";

const frontendPort = Number(process.env.CITYNEXUS_ORD0346_PORT ?? 4196);
const backendPort = Number(process.env.CITYNEXUS_BACKEND_PORT ?? "");
if (!Number.isInteger(backendPort) || backendPort < 1024) {
  throw new Error(
    "[ord0346] CITYNEXUS_BACKEND_PORT must name the backend this lane started; refusing to proxy anywhere else",
  );
}

export default defineConfig({
  testDir: "./e2e",
  /* This order changed a panel two existing wizard gates already speak about (ORD-0060's
     "no invented count / every offered name is listed", ORD-0261's positive-control hit-test), so
     the lane runs those specs on its own stack too.  The default stays this order's spec. */
  testMatch: process.env.CITYNEXUS_ORD0346_MATCH
    ? new RegExp(process.env.CITYNEXUS_ORD0346_MATCH)
    : /qoder-ord0346-.*\.spec\.ts/,
  timeout: 240_000,
  expect: { timeout: 30_000 },
  reporter: [["list"], ["json", { outputFile: process.env.CITYNEXUS_ORD0346_REPORT
    /* Named by the runner so the report does not land in the tracked tree: a gate run must leave the
       checkout byte-identical, and an artefact "deleted afterwards" is not the same thing. */
    ?? "D:/moodle/_qoder_lane_S4_0926/work/ord0346/report-ord0346.json" }]],
  use: {
    baseURL: `http://127.0.0.1:${frontendPort}`,
    viewport: { width: 390, height: 844 },
    hasTouch: true,
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
