/* Intelligence-copy debt ruler (lane 82f55d8a) -- private runner, source-only: reads two files, starts nothing.
 */
import { defineConfig } from "@playwright/test";

export default defineConfig({
  testDir: "./e2e",
  testMatch: /qoder-82f55d8a-intelligence-copy-debt-.*\.spec\.ts/,
  timeout: 120_000,
  reporter: [["list"]],
});
