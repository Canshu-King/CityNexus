/**
 * ORD-0044 probe — a legal 4-day journey stalls on step 3.
 *
 * The Commander measured: travelers 201, journeys 201, then nothing further -- not even
 * stay-options/generate -- while the screen sat on step 3 for 24s.  This script drives the
 * real wizard against the real production build and records every API call with its status
 * and body, every console error, and what the screen said over time, so the stall is
 * located by observation rather than by reading the code and guessing.
 *
 *   node review/probe-ord0044.mjs
 *
 * Needs the backend on :8360 and `vite preview` on :4199 (see review/prod-refresh-walk.mjs).
 */

import { createRequire } from "node:module";
import { writeFileSync } from "node:fs";
const require = createRequire(import.meta.url);
const { chromium } = require("D:/moodle/_qoder_ui_overnight_20260920/frontend/node_modules/playwright");

const PREVIEW = "http://127.0.0.1:4199";
const OUT = "D:/moodle/_qoder_ui_overnight_20260920/review/evidence/ui-overnight/ord0044-probe.json";

const calls = [];
const errors = [];
const timeline = [];

const browser = await chromium.launch();
const context = await browser.newContext({ viewport: { width: 390, height: 844 } });
const page = await context.newPage();

page.on("console", (message) => {
  if (["error", "warning"].includes(message.type())) errors.push(message.text().slice(0, 300));
});
page.on("pageerror", (error) => errors.push(`pageerror: ${String(error).slice(0, 300)}`));
page.on("requestfailed", (request) =>
  calls.push({ url: request.url(), method: request.method(), failed: request.failure()?.errorText }),
);

/* Log the API traffic without altering it: the point is to see which call never happens. */
await page.route("**/api/v1/**", async (route) => {
  const request = route.request();
  const response = await route.fetch({ url: request.url() });
  const text = await response.text();
  calls.push({
    url: request.url().replace(PREVIEW, ""),
    method: request.method(),
    status: response.status(),
    contentType: response.headers()["content-type"] ?? "",
    body: text.slice(0, 260),
  });
  await route.fulfill({ response });
});

await page.goto(`${PREVIEW}/v8`, { waitUntil: "networkidle" });
await page.evaluate(() => {
  localStorage.clear();
  sessionStorage.clear();
});
await page.reload({ waitUntil: "networkidle" });

const say = (label) => {
  timeline.push(`${label}: ${new Date().toISOString().slice(11, 23)}`);
};

say("wizard open");
await page.getByTestId("trial-city").fill("天津");
/* A legal window: 4 days, well inside the 7-day product ceiling. */
await page.getByTestId("trial-start").fill("2026-10-09T18:00");
await page.getByTestId("trial-end").fill("2026-10-13T15:00");
await page.getByTestId("trial-arrival").fill("天津站");
await page.getByTestId("trial-departure").fill("滨海机场");
say("dates filled (4 days)");
await page.getByTestId("trial-next").click();
await page.waitForTimeout(400);
say("step 2");
await page.getByTestId("trial-next").click();
await page.waitForTimeout(400);
say("step 3");
await page.getByTestId("trial-create").click();
say("create clicked");

for (const seconds of [2, 5, 10, 20, 30]) {
  await page.waitForTimeout(seconds === 2 ? 2000 : 5000);
  const state = await page.evaluate(() => ({
    shell: Boolean(document.querySelector(".v8-product-shell")),
    error: document.querySelector('[data-testid="trial-create-error"]')?.innerText?.replace(/\s+/g, " ") ?? null,
    busy: document.querySelector('[data-testid="trial-create"]')?.hasAttribute("disabled") ?? null,
    url: location.pathname,
    text: document.body.innerText.replace(/\s+/g, " ").slice(0, 130),
  }));
  timeline.push(`@${seconds}s ` + JSON.stringify(state));
  if (state.shell) break;
}

const report = {
  generatedBy: "e345b9d6",
  order: "ORD-0044",
  apiCalls: calls,
  consoleErrors: errors,
  timeline,
};
writeFileSync(OUT, JSON.stringify(report, null, 2) + "\n");
console.log(JSON.stringify(report, null, 2));
await browser.close();
