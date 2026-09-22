import { defineConfig } from "@playwright/test";
import {
  announce,
  backendCommand,
  backendEnv,
  resolveE2eEnvironment,
} from "./playwrightEnv";

/**
 * The production-build chain for this lane's acceptance gates.
 *
 * ORD-0088 (merged into ORD-0082) item 4 says the run must be a production build, not Vite dev --
 * dev numbers are not release evidence, and the artefact a teacher is shown on a phone is what this
 * chain serves (`npm run build` + `vite preview`, which proxies /api through `preview.proxy` in
 * vite.config.ts because `vite preview` does not inherit `server.proxy`).
 *
 * Additive on purpose: `playwright.config.ts` and `playwrightEnv.ts` belong to another lane and are
 * used read-only here, so the only way to run these specs against the built bundle is a config of
 * its own rather than editing the acceptance harness's地基.
 */
const env = resolveE2eEnvironment("prod-gate");
announce(env, "prod-gate");

export default defineConfig({
  testDir: "./e2e",
  testIgnore: /[\\/]e2e[\\/]legacy[\\/]/,
  ...(env.authoritative ? { globalSetup: "./e2e/_qoderAuthoritativeSetup.ts" } : {}),
  /* Same two projects as the acceptance suite, read-only: the seed creates a journey through the
     product API and writes the storageState the tests then replay.  A chain without it measures an
     empty stage and a context with no journey at all. */
  projects: [
    { name: "real-seed", testMatch: /_qoderRealSeed\.setup\.ts/ },
    {
      name: "chromium",
      dependencies: ["real-seed"],
      use: { storageState: "./e2e/.qoder-seed-state.json" },
    },
  ],
  timeout: 420_000,
  expect: { timeout: 15_000 },
  workers: 1,
  use: {
    baseURL: `http://127.0.0.1:${env.frontendPort}`,
    serviceWorkers: "allow",
  },
  webServer: [
    {
      command: backendCommand(env),
      cwd: "../backend",
      env: backendEnv(env),
      url: `http://127.0.0.1:${env.backendPort}/api/v1/health`,
      reuseExistingServer: false,
      timeout: 120_000,
      stdout: "pipe",
      stderr: "pipe",
    },
    {
      command: `npm run build && npm exec -- vite preview --host 127.0.0.1 --port ${env.frontendPort}`,
      cwd: ".",
      url: `http://127.0.0.1:${env.frontendPort}/v8/hub`,
      reuseExistingServer: false,
      timeout: 240_000,
      stdout: "pipe",
      stderr: "pipe",
    },
  ],
});
