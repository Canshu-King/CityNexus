/* 前置单 (lane e766b154) -- the four shared-testid neighbours, re-run against the day15 bundle.
 *
 * The order (commander 01:48): run `qoder-ord0502-phone-mainline` and the three `qoder-bac10f40-*`
 * footprint/map specs -- the four that read the same testids -- on the stack the 01:45 block put up,
 * and deliver the readings whether they are red or green.
 *
 * Two things this config deliberately does NOT do, and both are the point of it:
 *
 *   1. no `webServer`. The generation being measured is the one on :4783/:4787; a config that started
 *      its own backend would measure my tree and call it day15. So every port here is required,
 *      never defaulted, and the four standing 不提供 ports are refused by name -- the same list the
 *      ORD-0502 lane's own config refuses.
 *   2. one spec per run. `CITYNEXUS_E766_NEIGHBOR` names which file this trip measures, because a run
 *      that carries all four lets one early red hide the siblings behind it, and the readings this
 *      order is asked for are per-spec.
 *
 * Service workers are blocked: the claim being read is about the bytes `index.html` names, and
 * `run/day15_stack_proof_r1.json` (lane-side) shows those bytes equal to the day15 dist on disk. A
 * precache from an earlier generation would answer for them instead.
 */
import { defineConfig } from "@playwright/test";

const frontendPort = Number(process.env.CITYNEXUS_E2E_PORT ?? "");
const backendPort = Number(process.env.CITYNEXUS_BACKEND_PORT ?? "");
for (const [name, value] of [
  ["CITYNEXUS_E2E_PORT", frontendPort],
  ["CITYNEXUS_BACKEND_PORT", backendPort],
] as const) {
  if (!Number.isInteger(value) || value < 1024) {
    throw new Error(`[day15-neighbors] ${name} must name the day15 listener; refusing to walk anywhere else`);
  }
}
if (frontendPort === backendPort) {
  throw new Error("[day15-neighbors] the front and the api must be named as two listeners");
}
for (const [name, value] of [
  ["CITYNEXUS_E2E_PORT", frontendPort],
  ["CITYNEXUS_BACKEND_PORT", backendPort],
] as const) {
  if ([8000, 4781, 4782, 8693].includes(value)) {
    throw new Error(`[day15-neighbors] ${name} may not be ${value}: that port belongs to another stack`);
  }
}

const NEIGHBOR = (process.env.CITYNEXUS_E766_NEIGHBOR ?? "").trim();
const MATCHES: Record<string, RegExp> = {
  "ord0502": /qoder-ord0502-phone-mainline\.spec\.ts/,
  "ord0497": /qoder-bac10f40-ord0497-footprints-on-map\.spec\.ts/,
  "ord0530": /qoder-bac10f40-ord0530-footprints-by-day\.spec\.ts/,
  "ord0537": /qoder-bac10f40-ord0537-map-toggle-reach\.spec\.ts/,
};
if (!(NEIGHBOR in MATCHES)) {
  throw new Error(
    `[day15-neighbors] CITYNEXUS_E766_NEIGHBOR must be one of ${Object.keys(MATCHES).join(", ")}`,
  );
}

export default defineConfig({
  testDir: "./e2e",
  testMatch: MATCHES[NEIGHBOR],
  timeout: 420_000,
  expect: { timeout: 20_000 },
  workers: 1,
  reporter: [
    ["list"],
    ["json", { outputFile: process.env.CITYNEXUS_E766_REPORT ?? "D:/moodle/_qoder_e766b154_ord0528_20261001/run/neighbors_report.json" }],
  ],
  use: {
    baseURL: `http://127.0.0.1:${frontendPort}`,
    viewport: { width: 390, height: 844 },
    hasTouch: true,
    locale: "zh-CN",
    serviceWorkers: "block",
  },
});
