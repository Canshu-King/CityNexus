import { randomBytes } from "node:crypto";
import { defineConfig } from "@playwright/test";
import { announce, backendEnv, resolveE2eEnvironment } from "./playwrightEnv";

const fixtureToken = process.env.CITYNEXUS_R73_TEST_FIXTURE_TOKEN ?? randomBytes(32).toString("hex");
process.env.CITYNEXUS_R73_TEST_FIXTURE_TOKEN = fixtureToken;

const env = resolveE2eEnvironment("r73-test-replay");
announce(env, "r73-test-replay");
const python = env.backendPython.includes(" ") ? `"${env.backendPython}"` : env.backendPython;

export default defineConfig({
  testDir: "./e2e",
  testMatch: /r73-shared-stop\.spec\.ts/,
  ...(env.authoritative ? { globalSetup: "./e2e/_qoderAuthoritativeSetup.ts" } : {}),
  timeout: 180_000,
  expect: { timeout: 15_000 },
  workers: 1,
  retries: 0,
  use: {
    baseURL: `http://127.0.0.1:${env.frontendPort}`,
    viewport: { width: 1280, height: 900 },
    locale: "en-US",
    timezoneId: "Asia/Shanghai",
  },
  webServer: [
    {
      command: `${python} tests/r73_replay_server.py`,
      cwd: "../backend",
      env: {
        ...backendEnv(env),
        CITYNEXUS_R73_TEST_REPLAY: "1",
        CITYNEXUS_R73_TEST_FIXTURE_TOKEN: fixtureToken,
      },
      url: `http://127.0.0.1:${env.backendPort}/api/v1/health`,
      reuseExistingServer: false,
      timeout: 120_000,
      stdout: "pipe",
      stderr: "pipe",
    },
    {
      command: `npm run dev -- --host 127.0.0.1 --port ${env.frontendPort}`,
      cwd: ".",
      url: `http://127.0.0.1:${env.frontendPort}`,
      reuseExistingServer: false,
      timeout: 120_000,
      stdout: "pipe",
      stderr: "pipe",
    },
  ],
});
