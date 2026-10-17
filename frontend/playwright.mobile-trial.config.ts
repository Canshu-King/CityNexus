import { defineConfig } from "@playwright/test";

const port = process.env.CITYNEXUS_MOBILE_UI_PORT ?? "14273";

/**
 * Strict isolated UI-layout test config. Unlike playwright.config.ts this does
 * NOT adopt anyone's backend, credentials, database or already-running server.
 * Explicit page.route TEST_PROVIDER fixtures own the few API reads. No live
 * Nominatim/Overpass, model or signed backend proof occurs here.
 */
export default defineConfig({
  testDir: "./e2e",
  testMatch: /revolution-(?:mobile-shell|human-session-recovery)\.spec\.ts$/,
  timeout: 45_000,
  expect: { timeout: 9_000 },
  workers: 1,
  retries: 0,
  reporter: [["list"], ["html", { outputFolder: "mobile-ui-report", open: "never" }]],
  outputDir: "mobile-ui-results",
  projects: [{
    name: "mobile-ui-chromium-fixture",
    use: {
      browserName: "chromium",
      baseURL: `http://127.0.0.1:${port}`,
      viewport: { width: 390, height: 844 },
      hasTouch: true,
      serviceWorkers: "block",
      trace: "retain-on-failure",
      screenshot: "only-on-failure",
    },
  }],
  webServer: {
    command: `npm run dev -- --host 127.0.0.1 --port ${port} --strictPort`,
    cwd: ".",
    url: `http://127.0.0.1:${port}`,
    reuseExistingServer: false,
    timeout: 120_000,
    env: { VITE_REV_TRIAL_MODE: "sample" },
  },
});
