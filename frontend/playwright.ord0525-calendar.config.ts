/* ORD-0525 (lane ics) — the calendar export gate: one tap on the itinerary must put a real .ics on
 * disk, and the file's event count must equal the stops the traveller is looking at.
 *
 * This config starts the FRONTEND only.  The backend is started by `review/ord0525/lane_stack_r1.py`,
 * which points `CITYNEXUS_DATABASE_URL` at this lane's own copy of a scheduled store and proves the
 * listener is reading that file before any screen reading is accepted.  Splitting it that way is
 * deliberate: a `webServer` array would let Playwright restart a backend mid-run and silently move
 * the rows under the arms, and a reused backend would mean borrowing a neighbour's store.
 *
 * Ports are env-overridable and default to 4912 (frontend) / 4911 (backend).  :8000, :4781, :4782,
 * :4783, :4785, :4787 and :8693 belong to other lanes and are never taken here.
 *
 * `fullyParallel: false` with one worker because one arm soft-deletes a trip: the day-count arms run
 * first, and the file order is the run order.  That is stated rather than assumed, since a parallel
 * worker would bin the trip under an arm that is still counting its stops.
 *
 * Usage:  npx playwright test -c playwright.ord0525-calendar.config.ts
 */
import { defineConfig } from "@playwright/test";

const frontendPort = Number(process.env.CITYNEXUS_ORD0525_PORT ?? 4912);
const backendPort = Number(process.env.CITYNEXUS_ORD0525_BACKEND_PORT ?? 4911);

export default defineConfig({
  testDir: "./e2e",
  testMatch: /qoder-ord0525-.*\.spec\.ts/,
  timeout: 240_000,
  expect: { timeout: 20_000 },
  fullyParallel: false,
  workers: 1,
  reporter: [
    ["list"],
    ["json", { outputFile: `../review/ord0525/readouts/report_ord0525_${process.env.CITYNEXUS_ORD0525_TAG ?? "r2"}.json` }],
  ],
  use: {
    baseURL: `http://127.0.0.1:${frontendPort}`,
    viewport: { width: 390, height: 844 },
    hasTouch: true,
    // The download must land in this lane's evidence folder, not in a shared browser profile.
    acceptDownloads: true,
  },
  webServer: {
    command: `npm run dev -- --host 127.0.0.1 --port ${frontendPort}`,
    port: frontendPort,
    reuseExistingServer: false,
    timeout: 180_000,
    stdout: "pipe",
    stderr: "pipe",
    env: { CITYNEXUS_BACKEND_PORT: String(backendPort) },
  },
});
