/**
 * lane e766b154 -- runner for the recycle-bin real-door reading. Same shape as this lane's other configs:
 * no webServer, every coordinate from the environment with no defaults, the commander's and the shared
 * ports refused by name, one spec per run, serviceWorkers blocked.
 */
import { defineConfig } from "@playwright/test";

const BASE = process.env.CITYNEXUS_E766_BIN_BASE || "";
const OUT = process.env.CITYNEXUS_E766_BIN_OUT || "";
const JOURNEY = process.env.CITYNEXUS_E766_BIN_JOURNEY || "";
const FORBIDDEN = ["8000", "4781", "4782", "8693", "4783", "4787", "4789"];

if (!BASE) throw new Error("ABORT CITYNEXUS_E766_BIN_BASE is required");
if (!OUT) throw new Error("ABORT CITYNEXUS_E766_BIN_OUT is required -- readings need a directory");
if (JOURNEY.length < 8) throw new Error("ABORT the journey id must come from the door, not be guessed");
const port = new URL(BASE).port;
if (!port) throw new Error("ABORT base has no port: " + BASE);
if (FORBIDDEN.indexOf(port) >= 0) {
  throw new Error("ABORT refused port " + port + " -- that listener belongs to somebody else");
}

export default defineConfig({
  testDir: "./e2e",
  testMatch: "qoder-e766b154-journey-in-bin-real-door-r1.spec.ts",
  timeout: 240_000,
  expect: { timeout: 15_000 },
  fullyParallel: false,
  workers: 1,
  retries: 0,
  forbidOnly: true,
  reporter: [["list"], ["json", { file: `${OUT}/report_journey_in_bin.json` }]],
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
