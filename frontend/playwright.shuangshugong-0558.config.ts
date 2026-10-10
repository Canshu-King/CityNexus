import { defineConfig } from "@playwright/test";
import { mkdirSync } from "node:fs";
import { resolve } from "node:path";

/* ------------------------------------------------------------------ *
 * ORD-0558 · lane 双数工 — an isolated runner for one spec.
 *
 * Why a second config instead of the acceptance suite: the acceptance suite starts a
 * backend and a seed project this copy does not need (every /api/v1/ call is served from
 * fixtures), and in developer mode it would reuse whatever process already holds :8000 --
 * which tonight is another lane's backend running another generation of the product.  Here
 * the only server is the vite dev server started from THIS worktree, and vite's /api proxy
 * is pointed at a port nothing listens on, so a request that escapes the fixtures fails
 * loudly instead of being answered by a neighbour.
 *
 * The numbers this run produces are dev-server numbers for a rendered-copy assertion; they
 * are not release evidence for anything server-side.
 * ------------------------------------------------------------------ */

const frontendPort = Number(process.env.CITYNEXUS_E2E_PORT ?? 5188);
const unansweredBackendPort = process.env.CITYNEXUS_UNANSWERED_BACKEND_PORT ?? "4199";
const evidenceBase = resolve(
  process.env.CITYNEXUS_EVIDENCE_DIR?.trim() ||
    resolve("..", "review/shuangshugong/ord0558_readouts"),
);
mkdirSync(evidenceBase, { recursive: true });

/* Which spec runs here is a parameter, not a constant: the same isolated harness is used to
   re-run the Live screen's existing rendered spec, so "nothing else went red" is a measurement
   taken on this worktree's bytes rather than a claim about the whole acceptance suite. */
const specPattern = process.env.CITYNEXUS_SPEC?.trim() || "qoder-shuangshugong-0558-live-dedup-plural-r1";

export default defineConfig({
  testDir: "./e2e",
  testMatch: new RegExp(specPattern + "\\.spec\\.ts$"),
  timeout: 90_000,
  expect: { timeout: 15_000 },
  workers: 1,
  fullyParallel: false,
  outputDir: "./test-results/qoder-shuangshugong-0558",
  reporter: [["list"], ["json", { outputFile: resolve(evidenceBase, "playwright_r1.json") }]],
  use: {
    baseURL: `http://127.0.0.1:${frontendPort}`,
    headless: true,
  },
  webServer: {
    command: `npm run dev -- --host 127.0.0.1 --port ${frontendPort}`,
    cwd: ".",
    url: `http://127.0.0.1:${frontendPort}`,
    reuseExistingServer: false,
    timeout: 180_000,
    stdout: "pipe",
    stderr: "pipe",
    env: { CITYNEXUS_BACKEND_PORT: unansweredBackendPort },
  },
});
