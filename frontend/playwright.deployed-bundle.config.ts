import { defineConfig } from "@playwright/test";
import {
  announce,
  backendCommand,
  backendEnv,
  resolveE2eEnvironment,
} from "./playwrightEnv";

/**
 * ORD-0226 follow-up ② (commander 02:1x): read this lane's targets against **the bytes the phone is
 * served**, not against a build of the current working tree.
 *
 * `playwright.prod-gate.config.ts` builds first, and since `e08131e` a build of this tree no longer
 * equals the deployed bundle -- so a green there would say "my tree", not "the generation on the
 * phone".  `vite preview --outDir <deployed dist>` serves the deployed artifact as it sits in the
 * preview chain's `dist/`, and `preview.proxy` in `vite.config.ts` still resolves `/api/v1` from
 * `CITYNEXUS_BACKEND_PORT`, so the API side is **this run's own throwaway database**.  Nothing here
 * opens `_preview.db`: the deployed directory is only ever read.
 *
 * Service workers are blocked on purpose.  This chain measures the bundle that `index.html` names;
 * a precache from an earlier run on a reused port would silently answer for it.
 */
const env = resolveE2eEnvironment("deployed-bundle");
announce(env, "deployed-bundle");

const DEPLOYED_DIST = process.env.CITYNEXUS_DEPLOYED_DIST ?? "D:/moodle/_qoder_preview_20260920/dist";

export default defineConfig({
  testDir: "./e2e",
  testIgnore: /[\\/]e2e[\\/]legacy[\\/]/,
  ...(env.authoritative ? { globalSetup: "./e2e/_qoderAuthoritativeSetup.ts" } : {}),
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
    serviceWorkers: "block",
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
      // No `npm run build`: the whole point is to run the artifact that is already on disk.
      command: `npm exec -- vite preview --host 127.0.0.1 --port ${env.frontendPort} --strictPort --outDir ${DEPLOYED_DIST}`,
      cwd: ".",
      url: `http://127.0.0.1:${env.frontendPort}/v8/hub`,
      reuseExistingServer: false,
      timeout: 240_000,
      stdout: "pipe",
      stderr: "pipe",
    },
  ],
});
