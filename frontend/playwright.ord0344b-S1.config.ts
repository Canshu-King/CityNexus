/* ORD-0344-b (lane S1) -- the move witnessed in both directions against the shipped gate's own
 * predicates.  No backend and no dev server: the two DOM shapes are mounted in the page, because
 * what is being measured is how Playwright reads a collapsed <details>, not what the API returns.
 * Not the acceptance gate; `playwright.config.ts` stays the only thing that can sign one. */
import { defineConfig } from "@playwright/test";
export default defineConfig({
  testDir: "./e2e",
  testMatch: /qoder-ord0344b-.*\.spec\.ts/,
  timeout: 60_000,
  expect: { timeout: 10_000 },
  reporter: [["list"]],
});
