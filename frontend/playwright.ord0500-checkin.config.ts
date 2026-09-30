/* ORD-0500 (lane phone) — runs the footprint-truth carrier against a SERVED production bundle.
 *
 * Same shape as the accepted ORD-0485 carrier config, because that shape is the point: the order asks
 * what a person can do on a phone, so the surface under test has to be the bundle a phone would be
 * handed (`vite preview` over this lane's own outDir, `/api` proxied to this lane's own backend by
 * CITYNEXUS_BACKEND_PORT).  There is no `webServer` block -- Playwright booting `npm run dev` would
 * collect dev-chain numbers, which are not release evidence -- and `CITYNEXUS_ORD0500_BASE` is
 * required rather than defaulted, so a lane cannot point its browser at somebody else's backend.
 *
 * Not the acceptance gate: `playwright.config.ts` stays the only thing that can sign one.
 */
import { defineConfig } from "@playwright/test";

const base = process.env.CITYNEXUS_ORD0500_BASE ?? "";
if (!/^http:\/\/127\.0\.0\.1:4[0-9]{3}$/.test(base)) {
  throw new Error(
    "[ord0500] CITYNEXUS_ORD0500_BASE must name the 127.0.0.1:4xxx face this lane is serving; " +
      "refusing to run against " + (base || "nothing"),
  );
}

export default defineConfig({
  testDir: "./e2e",
  testMatch: /qoder-ord0500-.*\.spec\.ts/,
  timeout: 240_000,
  expect: { timeout: 30_000 },
  reporter: [["list"], ["json", {
    /* Outside the tracked tree: a gate run must leave the checkout byte-identical. */
    outputFile:
      process.env.CITYNEXUS_ORD0500_REPORT
      ?? "D:/moodle/_qoder_phone_ord0485_20260930/run/report-ord0500.json",
  }]],
  use: {
    baseURL: base,
    viewport: { width: 390, height: 844 },
    hasTouch: true,
    trace: "off",
    screenshot: "off",
  },
});
