/* ORD-0568 route-provenance gloss ruler (lane cff87c64) — the private runner for
 * `e2e/qoder-cff87c64-ord0568-route-provenance-gloss-r1.spec.ts`.
 *
 * It starts nothing and listens on nothing: the ruler reads the route, the display vocabulary and the
 * recovery panel, so it works on a bare checkout with no backend, no front and no store. There is
 * deliberately no webServer and no port variable to default — a lane that points this at a shared port has
 * changed what is being measured.
 *
 * Not the acceptance gate: `playwright.config.ts` stays the only thing that can sign one.
 */
import { defineConfig } from "@playwright/test";

export default defineConfig({
  testDir: "./e2e",
  testMatch: /qoder-cff87c64-ord0568-route-provenance-gloss-.*\.spec\.ts/,
  timeout: 120_000,
  reporter: [["list"], ["json", { outputFile: process.env.CITYNEXUS_PROV_REPORT }]],
});
