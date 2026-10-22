import { defineConfig } from "@playwright/test";

export default defineConfig({
  testDir: "./e2e",
  testMatch: /revolution-mobile-shell\.spec\.ts/,
  timeout: 45_000,
  expect: { timeout: 10_000 },
  workers: 1,
  reporter: "list",
  use: {
    baseURL: "http://127.0.0.1:5174",
    viewport: { width: 390, height: 844 },
    hasTouch: true,
    screenshot: "only-on-failure",
  },
});
