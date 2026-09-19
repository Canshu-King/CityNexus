import { defineConfig } from "@playwright/test";
import { existsSync, mkdirSync, writeFileSync } from "node:fs";
import { dirname, resolve } from "node:path";

/* ------------------------------------------------------------------ *
 * Two ways to run this suite.
 *
 * Default (developer) mode keeps the convenient behaviour: sensible
 * ports, a venv next to the repo if one exists, and reuse of any server
 * already listening.
 *
 * Authoritative mode (CITYNEXUS_E2E_AUTHORITATIVE=1) exists because of a
 * pass-12 finding: a clone without its own .venv fell back to a system
 * Python 3.10 that cannot even import the app, while reuseExistingServer
 * happily adopted whatever process already held :8000 — another lane's
 * backend, running other code, with another database and DeepSeek
 * enabled.  Green tests were reporting on a neighbour.  Here that is made
 * structurally impossible instead of merely unlikely: this run must own
 * both processes, or it must refuse to run.
 * ------------------------------------------------------------------ */

const AUTHORITATIVE = process.env.CITYNEXUS_E2E_AUTHORITATIVE === "1";

function refuse(reason: string): never {
  throw new Error(
    `[citynexus e2e] authoritative mode refuses to start: ${reason}\n` +
      `[citynexus e2e] fix the invocation, not the assertion.  See INTEGRATION_REPORT.md section 27.`,
  );
}

function requiredEnv(name: string, why: string): string {
  const value = process.env[name];
  if (!value) refuse(`${name} must be set explicitly (${why})`);
  return value;
}

function port(value: string, name: string): number {
  const parsed = Number(value);
  if (!Number.isInteger(parsed) || parsed < 1024 || parsed > 65535) {
    refuse(`${name} must be a numeric port, got "${value}"`);
  }
  return parsed;
}

let E2E_PORT: number;
let BACKEND_PORT: number;
let backendPython: string;
let databaseUrl: string | undefined;
let runId: string | undefined;
let aiDisabled: boolean;
let reuseServers: boolean;

if (AUTHORITATIVE) {
  E2E_PORT = port(requiredEnv("CITYNEXUS_E2E_PORT", "the frontend must not be borrowed"), "CITYNEXUS_E2E_PORT");
  BACKEND_PORT = port(
    requiredEnv("CITYNEXUS_BACKEND_PORT", "the backend must not be borrowed"),
    "CITYNEXUS_BACKEND_PORT",
  );
  if (E2E_PORT === BACKEND_PORT) refuse("frontend and backend ports must differ");

  const python = requiredEnv("CITYNEXUS_PYTHON", "falling back to system Python is what tested a neighbour");
  if (!existsSync(resolve(python))) refuse(`CITYNEXUS_PYTHON="${python}" does not exist`);
  backendPython = python;

  databaseUrl = requiredEnv("CITYNEXUS_DATABASE_URL", "an authoritative run gets its own database");
  if (!databaseUrl.startsWith("sqlite:///")) {
    refuse(`CITYNEXUS_DATABASE_URL must be a sqlite:/// path in this mode, got "${databaseUrl}"`);
  }
  /* The file is deleted before the run, so refuse to touch anything that does
     not look disposable.  A leading underscore is also git-ignored. */
  const dbFile = databaseUrl.replace(/^sqlite:\/\/\//, "");
  const dbBase = dbFile.split(/[\\/]/).pop() ?? "";
  if (!dbBase.startsWith("_") || !dbBase.endsWith(".db")) {
    refuse(`CITYNEXUS_DATABASE_URL must point at a throwaway "_*.db" file, got "${dbFile}"`);
  }
  runId = requiredEnv("CITYNEXUS_E2E_RUN_ID", "the backend echoes it back to prove who started it");
  /* Naming the database after the run makes "fresh isolated DB" structural: no
     later invocation can reopen this file, because it will carry a new id. */
  if (!dbBase.includes(runId)) {
    refuse(`CITYNEXUS_DATABASE_URL ("${dbFile}") must contain CITYNEXUS_E2E_RUN_ID "${runId}"`);
  }

  const liveKeys = ["DEEPSEEK_API_KEY", "CITYNEXUS_AI_API_KEY"].filter((k) => !!process.env[k]);
  if (liveKeys.length) {
    refuse(`external AI must be off for the deterministic suite (found ${liveKeys.join(", ")})`);
  }
  if (process.env.CITYNEXUS_AI_ENABLED !== "false") {
    refuse('CITYNEXUS_AI_ENABLED must be "false"');
  }
  aiDisabled = true;
  reuseServers = false;
} else {
  E2E_PORT = Number(process.env.CITYNEXUS_E2E_PORT ?? 4173);
  BACKEND_PORT = Number(process.env.CITYNEXUS_BACKEND_PORT ?? 8000);
  backendPython =
    process.env.CITYNEXUS_PYTHON ??
    (process.platform === "win32" && existsSync("../.venv/Scripts/python.exe")
      ? "..\\.venv\\Scripts\\python.exe"
      : "python");
  databaseUrl = process.env.CITYNEXUS_DATABASE_URL;
  runId = process.env.CITYNEXUS_E2E_RUN_ID;
  aiDisabled = false;
  reuseServers = true;
}

/* One provenance block per run, printed and also written into the evidence
   directory, so a package can be judged on whether it tested its own tree. */
const provenance = {
  authoritative: AUTHORITATIVE,
  runId: runId ?? "(none)",
  python: backendPython,
  pythonResolved: resolve(backendPython),
  frontendPort: E2E_PORT,
  backendPort: BACKEND_PORT,
  databaseUrl: databaseUrl ?? "(inherited default)",
  ai: AUTHORITATIVE ? "disabled" : "inherited from the environment",
  reuseExistingServer: reuseServers,
  workers: 1,
  retries: 0,
  recordedAt: new Date().toISOString(),
};
const provenanceLine =
  `[citynexus e2e] authoritative=${provenance.authoritative} python=${provenance.python} ` +
  `frontend=:${provenance.frontendPort} backend=:${provenance.backendPort} ` +
  `db=${provenance.databaseUrl} ai=${provenance.ai} reuseExistingServer=${provenance.reuseExistingServer}`;
console.error(provenanceLine);
if (AUTHORITATIVE) {
  const target = resolve("../reports/e2e-provenance/authoritative.json");
  mkdirSync(dirname(target), { recursive: true });
  writeFileSync(target, JSON.stringify({ ...provenance, provenanceLine }, null, 2) + "\n", "utf-8");
}

const backendCwd = "../backend";
const backendCommand = `${
  backendPython.includes(" ") ? `"${backendPython}"` : backendPython
} -m uvicorn app.main:app --host 127.0.0.1 --port ${BACKEND_PORT}`;

export default defineConfig({
  testDir: "./e2e",
  /* Authoritative mode checks that this run can actually own both ports before
     webServer starts them — globalSetup is the only hook that runs earlier. */
  ...(AUTHORITATIVE ? { globalSetup: "./e2e/_qoderAuthoritativeSetup.ts" } : {}),
  // Guardian recovery is an asynchronous provider -> solver -> policy ->
  // mutation path.  Windows CI occasionally needs longer than Playwright's
  // 30s default while the browser reloads and the shared local SQLite worker
  // drains; the product assertions retain their own targeted time budgets.
  timeout: 60_000,
  expect: { timeout: 10_000 },
  // The local demo intentionally uses one shared SQLite process/database;
  // serial workers keep reset-and-replay scenarios isolated.
  workers: 1,
  /* globalSetup would run before this config's webServer entries have a live
     port, so the seed is a Playwright setup *project*: it runs against the very
     servers Playwright starts, then every test replays its storageState. */
  projects: [
    { name: "real-seed", testMatch: /_qoderRealSeed\.setup\.ts/ },
    {
      name: "chromium",
      dependencies: ["real-seed"],
      use: { storageState: "./e2e/.qoder-seed-state.json" },
    },
  ],
  use: { baseURL: `http://127.0.0.1:${E2E_PORT}` },
  webServer: [
    {
      command: backendCommand,
      cwd: backendCwd,
      env: {
        ...(process.env as Record<string, string>),
        ...(databaseUrl ? { CITYNEXUS_DATABASE_URL: databaseUrl } : {}),
        ...(runId ? { CITYNEXUS_E2E_RUN_ID: runId } : {}),
      },
      url: `http://127.0.0.1:${BACKEND_PORT}/api/v1/health`,
      reuseExistingServer: reuseServers,
      timeout: 120000,
      stdout: "pipe",
      stderr: "pipe",
    },
    {
      command: `npm run dev -- --host 127.0.0.1 --port ${E2E_PORT}`,
      cwd: ".",
      url: `http://127.0.0.1:${E2E_PORT}`,
      reuseExistingServer: reuseServers,
      timeout: 120000,
    },
  ],
});
