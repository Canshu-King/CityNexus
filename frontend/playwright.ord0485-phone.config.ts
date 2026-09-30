/* ORD-0485 (lane phone) — a config that runs the word-carrier spec against a SERVED
 * production bundle, not against `npm run dev`.
 *
 * The order asks what a person can demo on a phone at 390x844, so the surface under test has to
 * be the thing a phone would be handed: `vite preview` over this lane's own outDir, with the
 * `/api` proxy pointed at this lane's own backend by CITYNEXUS_BACKEND_PORT.  There is no
 * `webServer` block here on purpose -- Playwright booting `npm run dev` would collect dev-chain
 * numbers, which mission 003 ⑤ rules out of evidence, and a lane must not be able to point its
 * browser at somebody else's backend by accident.  `CITYNEXUS_ORD0485_BASE` is therefore
 * required, not defaulted: refuse rather than proxy somewhere unknown.
 *
 * Not the acceptance gate: `playwright.config.ts` stays the only thing that can sign one.
 */
import { defineConfig } from "@playwright/test";

const base = process.env.CITYNEXUS_ORD0485_BASE ?? "";
if (!/^http:\/\/127\.0\.0\.1:4[0-9]{3}$/.test(base)) {
  throw new Error(
    "[ord0485] CITYNEXUS_ORD0485_BASE must name the 127.0.0.1:4xxx face this lane is serving; " +
      "refusing to run against " + (base || "nothing"),
  );
}

export default defineConfig({
  testDir: "./e2e",
  testMatch: process.env.CITYNEXUS_ORD0485_MATCH
    ? new RegExp(process.env.CITYNEXUS_ORD0485_MATCH)
    : /qoder-ord0485-.*\.spec\.ts/,
  timeout: 240_000,
  expect: { timeout: 30_000 },
  reporter: [["list"], ["json", { outputFile: process.env.CITYNEXUS_ORD0485_REPORT
    /* Outside the tracked tree: a gate run must leave the checkout byte-identical. */
    ?? "D:/moodle/_qoder_phone_ord0485_20260930/run/report-ord0485.json" }]],
  use: {
    baseURL: base,
    viewport: { width: 390, height: 844 },
    hasTouch: true,
    trace: "off",
    screenshot: "off",
  },
});
