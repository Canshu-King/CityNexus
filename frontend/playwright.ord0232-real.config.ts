import { defineConfig } from "@playwright/test";
import {
  announce,
  backendCommand,
  backendEnv,
  resolveE2eEnvironment,
} from "./playwrightEnv";

/**
 * ORD-0232's **end-to-end** arm, on purpose outside the acceptance suite (`testDir` is
 * `./e2e-ord0232-real`, which `playwright.config.ts` and `playwright.prod-gate.config.ts` never
 * discover).
 *
 * Why it is separate: its positive assertion needs the emitter `plans.candidate_rejected`, which
 * lives in `a96fabf` on branch `agent/canary-ord198-20260922` and is not an ancestor of this tip.  A
 * node that is red for a reason outside this lane's control would pollute the shared red baseline,
 * and a node that quietly passes because nothing was ever emitted would be worse.  So the arm ships
 * as a runnable, self-refusing command: `review/ord0232_e2e_replay.py`.
 */
const env = resolveE2eEnvironment("ord0232-real-chain");
announce(env, "ord0232-real-chain");

export default defineConfig({
  testDir: "./e2e-ord0232-real",
  ...(env.authoritative ? { globalSetup: "./e2e/_qoderAuthoritativeSetup.ts" } : {}),
  projects: [
    { name: "real-seed", testMatch: /_qoderRealSeed\.setup\.ts/, testDir: "./e2e" },
    {
      name: "chromium",
      dependencies: ["real-seed"],
      use: { storageState: "./e2e/.qoder-seed-state.json" },
    },
  ],
  timeout: 420_000,
  expect: { timeout: 20_000 },
  workers: 1,
  use: {
    baseURL: `http://127.0.0.1:${env.frontendPort}`,
    viewport: { width: 390, height: 844 },
    hasTouch: true,
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
