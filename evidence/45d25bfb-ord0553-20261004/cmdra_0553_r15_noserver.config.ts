/* ORD-0553 r15 -- a no-server runner for file-reading rulers.
 *
 * Why: `playwright.config.ts` starts a backend and a dev server because most specs need them.  The
 * status-vocabulary ruler this lane landed in r2 reads five source files and starts nothing, so running it
 * through the product config would spawn two processes to answer a question about text.  This config
 * declares exactly one spec and no webServer, which is also why its green can only speak for that spec.
 */
import { defineConfig } from "@playwright/test";

const HERE = process.env.CMDRA_R15_ROOT ?? ".";

export default defineConfig({
  testDir: HERE,
  testMatch: /qoder-45d25bfb-authoritative-status-vocabulary-r1\.spec\.ts/,
  reporter: [["list"]],
  workers: 1,
  timeout: 60_000,
  outputDir: process.env.CMDRA_R15_OUT ?? "./_r15_test_output",
});
