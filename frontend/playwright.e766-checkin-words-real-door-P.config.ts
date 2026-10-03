/**
 * lane e766b154 -- runner for the real-door word reads. Same shape as this lane's other configs:
 * no webServer (the stack is started by the lane's shell script, so a run can never restart or kill a
 * listener it does not own), every coordinate from the environment with no defaults, the commander's
 * and the shared ports refused by name, and one spec per run so an early red cannot hide a sibling.
 */
import { defineConfig } from "@playwright/test";

const BASE = process.env.CITYNEXUS_E766_REAL_BASE || "";
const OUT = process.env.CITYNEXUS_E766_REAL_OUT || "";
const TARGETS = process.env.CITYNEXUS_E766_REAL_TARGETS || "";
const FORBIDDEN = ["8000", "4781", "4782", "8693", "4783", "4787", "4789"];

if (!BASE) throw new Error("ABORT CITYNEXUS_E766_REAL_BASE is required -- no default base");
if (!TARGETS) throw new Error("ABORT CITYNEXUS_E766_REAL_TARGETS is required -- ids must come from a receipt");
if (!OUT) throw new Error("ABORT CITYNEXUS_E766_REAL_OUT is required -- readings need a directory");
const port = new URL(BASE).port;
if (!port) throw new Error("ABORT base has no port: " + BASE);
if (FORBIDDEN.indexOf(port) >= 0) {
  throw new Error("ABORT refused port " + port + " -- that listener belongs to somebody else");
}

export default defineConfig({
  testDir: "./e2e",
  testMatch: "qoder-e766b154-checkin-words-real-door-r1.spec.ts",
  timeout: 180_000,
  expect: { timeout: 15_000 },
  fullyParallel: false,
  workers: 1,
  retries: 0,
  forbidOnly: true,
  reporter: [["list"], ["json", { file: `${OUT}/report_real_door.json` }]],
  use: {
    baseURL: BASE,
    headless: true,
    viewport: { width: 390, height: 844 },
    hasTouch: true,
    isMobile: true,
    serviceWorkers: "block",
    actionTimeout: 25_000,
    trace: "off",
    screenshot: "off",
  },
});
