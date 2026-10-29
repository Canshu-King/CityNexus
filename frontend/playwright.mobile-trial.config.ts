import { defineConfig } from "@playwright/test";

const port = process.env.CITYNEXUS_MOBILE_UI_PORT ?? "14273";

/** Isolated browser fixtures. A passing run is not a live provider or Agent run. */
export default defineConfig({
  testDir: "./e2e",
  testMatch: /revolution-(?:dialogue|source-media|visual-travel|draft-variants|draft-preparation|guardian-stream|amap-research-ui|mobile-shell|human-session-recovery|night-out-rest-preferences|place-card-facts|mobile-hermes-transparency|mobile-plan-workbench|workspace-actions|sim-traveller)\.spec\.ts$/,
  // 50 sequential UI fixtures against one dev server: at 45s three different tests were clipped
  // mid-flow across runs (a reload wait and an initial tab render); 90s full runs passed twice.
  timeout: 90_000,
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
