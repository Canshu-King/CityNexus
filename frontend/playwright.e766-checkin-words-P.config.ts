/**
 * lane e766b154 -- runner for the day24 check-in word reads. Same shape as this lane's other configs,
 * because each one was written after a mistake, not before:
 *   * no webServer: the stack is started by the lane's own shell script, so a run can never restart or
 *     kill a listener it does not own (the commander's :4783/:4787 and the shared :8000/:4781/:4782/:8693
 *     are refused by name below, not just "not started");
 *   * every coordinate comes from the environment and the run refuses to guess: no defaults;
 *   * one spec per run, so an early red cannot hide its siblings behind it;
 *   * serviceWorkers blocked, or a previous generation's shell answers the page and the words read are
 *     not the bundle under test.
 */
import { defineConfig } from "@playwright/test";

const BASE = process.env.CITYNEXUS_E766_WORDS_BASE || "";
const OUT = process.env.CITYNEXUS_E766_WORDS_OUT || "";
const MODE = process.env.CITYNEXUS_E766_WORDS_MODE || "";
const FORBIDDEN = ["8000", "4781", "4782", "8693", "4783", "4787"];

if (!BASE) throw new Error("ABORT CITYNEXUS_E766_WORDS_BASE is required -- no default base");
const port = new URL(BASE).port;
if (!port) throw new Error("ABORT base has no port: " + BASE);
if (FORBIDDEN.indexOf(port) >= 0) {
  throw new Error("ABORT refused port " + port + " -- that listener belongs to somebody else");
}
if (["fake", "real"].indexOf(MODE) < 0) {
  throw new Error("ABORT CITYNEXUS_E766_WORDS_MODE must be fake or real, got: " + MODE);
}
if (!OUT) throw new Error("ABORT CITYNEXUS_E766_WORDS_OUT is required -- readings need a directory");

export default defineConfig({
  testDir: "./e2e",
  testMatch: "qoder-e766b154-checkin-words-day24-r1.spec.ts",
  timeout: 180_000,
  expect: { timeout: 15_000 },
  fullyParallel: false,
  workers: 1,
  retries: 0,
  forbidOnly: true,
  reporter: [["list"], ["json", {
    file: `${OUT}/report_${MODE}_${process.env.CITYNEXUS_E766_WORDS_LOCALE || "na"}.json`,
  }]],
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
