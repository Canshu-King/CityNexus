/**
 * ORD-0044 side question from the Commander: is 39-40 `GET /twin` per visit designed
 * polling or a loop?
 *
 * `useAuthoritativeTwin` declares refetchInterval 15s and is mounted in two places
 * (V8Experience and LiveRecovery).  Two observers on one key can each schedule their own
 * interval, which would double the rate -- so count, per screen, over a fixed window.
 *
 *   node review/count-twin-polls.mjs
 *
 * Needs `vite preview` on :4199 (production build) with the backend reachable through it.
 */

import { createRequire } from "node:module";
const require = createRequire(import.meta.url);
const { chromium } = require("D:/moodle/_qoder_ui_overnight_20260920/frontend/node_modules/playwright");

const PREVIEW = "http://127.0.0.1:4199";
const WINDOW_MS = 75_000;

const browser = await chromium.launch();
const context = await browser.newContext();
await context.addInitScript((id) => {
  if (id) localStorage.setItem("citynexus.v8.journey_id", id);
}, process.env.JOURNEY_ID ?? "");

const results = {};
for (const route of ["/v8/hub", "/v8/live"]) {
  const page = await context.newPage();
  let twin = 0;
  let all = 0;
  page.on("request", (request) => {
    if (!request.url().includes("/api/v1/")) return;
    all += 1;
    if (request.url().includes("/twin")) twin += 1;
  });
  await page.goto(`${PREVIEW}${route}`, { waitUntil: "networkidle" });
  const started = Date.now();
  const marks = [];
  while (Date.now() - started < WINDOW_MS) {
    await page.waitForTimeout(15_000);
    marks.push({ atSeconds: Math.round((Date.now() - started) / 1000), twin });
  }
  results[route] = { twin, allApi: all, marks };
  console.log(`${route}: ${twin} twin calls out of ${all} API calls in ${Math.round(WINDOW_MS / 1000)}s`);
  console.log("  progress:", JSON.stringify(marks));
  await page.close();
}
await browser.close();

console.log(JSON.stringify(results, null, 2));
