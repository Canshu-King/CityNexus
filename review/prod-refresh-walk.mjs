/**
 * Production-build user walk (ORD-0036 acceptance + ORD-0038's USER_GATES item).
 *
 * This is deliberately NOT part of the Playwright suite: the suite's webServer is
 * `npm run dev`, and the acceptance axis now says a dev-server result is not release
 * evidence.  Here the app is the shipped bundle, served by `vite preview`, with a real
 * service worker in control.
 *
 *   node review/prod-refresh-walk.mjs
 *
 * Expects a backend on CITYNEXUS_BACKEND_PORT (default 8360) and `vite preview` on :4199
 * serving D:/moodle/_qoder_ui_build_20260920.  It writes review/evidence/ui-overnight/
 * prod-walk.json plus screenshots, and prints what the screen actually said at each step.
 */

import { execSync } from "node:child_process";
import { createRequire } from "node:module";
import { readFileSync, writeFileSync, existsSync, rmSync } from "node:fs";

/* This script lives in review/, which has no node_modules above it, so a bare specifier
   cannot resolve.  Load the frontend's own Playwright, by absolute path. */
const require = createRequire(import.meta.url);
const { chromium } = require("D:/moodle/_qoder_ui_overnight_20260920/frontend/node_modules/playwright");

const OUT = "D:/moodle/_qoder_ui_overnight_20260920/review/evidence/ui-overnight";
const BUILD = "D:/moodle/_qoder_ui_build_20260920";
const FRONTEND = "D:/moodle/_qoder_ui_overnight_20260920/frontend";
const PREVIEW = "http://127.0.0.1:4199";
const MARKER_FILE = `${FRONTEND}/src/prodWalkMarker.ts`;

const assetHrefs = (html) => [...html.matchAll(/(?:src|href)="(\/assets\/[^"]+)"/g)].map((m) => m[1]).sort();

const report = { generatedBy: "e345b9d6", orders: ["ORD-0036", "ORD-0038"], preview: PREVIEW, steps: [] };
const record = (step, data) => {
  report.steps.push({ step, ...data });
  console.log(`\n--- ${step} ---`);
  for (const [key, value] of Object.entries(data)) {
    console.log(`  ${key}: ${typeof value === "string" ? JSON.stringify(value) : JSON.stringify(value)}`);
  }
};

const browser = await chromium.launch();

async function newPage(context, scheme) {
  const page = await context.newPage();
  await page.emulateMedia({ colorScheme: scheme, media: "screen" });
  await page.setViewportSize({ width: 390, height: 844 });
  return page;
}

async function awaitController(page) {
  await page.waitForFunction(
    () => Boolean(navigator.serviceWorker && navigator.serviceWorker.controller),
    null,
    { timeout: 20000 },
  );
}

/* ------------------------------------------------------------------ context ---- */
const context = await browser.newContext({ baseURL: PREVIEW });

/* A fresh context has no journey, so the app would open the creation wizard and every
   later step would be measuring the wrong screen.  Seed through the product API and hand
   the browser the id the same way the app itself persists it. */
const seedResponse = await fetch("http://127.0.0.1:8360/api/v1/demo/reset", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: "{}",
});
const seed = await seedResponse.json();
await context.addInitScript((id) => {
  localStorage.setItem("citynexus.v8.journey_id", id);
}, seed.journey_id);
record("A0 seeded a journey through the product API", {
  http: seedResponse.status,
  journey_id: seed.journey_id,
  traveler_id: seed.traveler_id,
});

/* ============================ A. the shipped shell boots under a worker ====== */
let page = await newPage(context, "light");
await page.goto(`${PREVIEW}/v8/hub`, { waitUntil: "networkidle" });
const firstLoad = {
  hasController: await page.evaluate(() => Boolean(navigator.serviceWorker.controller)),
  rootChildren: await page.evaluate(() => document.querySelectorAll("#root > *").length),
  heading: await page.getByTestId("today-heading").first().textContent().catch(() => null),
};
record("A1 first load (registers the worker)", firstLoad);

await page.goto(`${PREVIEW}/v8/hub`, { waitUntil: "networkidle" });
await awaitController(page);
const secondLoad = {
  hasController: await page.evaluate(() => Boolean(navigator.serviceWorker.controller)),
  scriptSrc: await page.evaluate(() => navigator.serviceWorker.controller.scriptURL),
  rootChildren: await page.evaluate(() => document.querySelectorAll("#root > *").length),
  heading: await page.getByTestId("today-heading").first().textContent().catch(() => null),
};
record("A2 second load (worker in control)", secondLoad);

/* ============================ B. rebuild -> plain reload picks it up ========= */
const beforeHtml = await page.content();
const beforeAssets = assetHrefs(await page.evaluate(() => document.documentElement.outerHTML));
const mainPath = `${FRONTEND}/src/main.tsx`;
const mainOriginal = readFileSync(mainPath, "utf8");
try {
  writeFileSync(MARKER_FILE, `export const PROD_WALK_MARKER = "cnx-prod-walk-${Date.now()}";\n`);
  // Import the marker from the app entry so it must appear in the executed bundle.
  writeFileSync(
    mainPath,
    `import { PROD_WALK_MARKER } from "./prodWalkMarker";\nvoid ((window as unknown as { __cnxProdWalk?: string }).__cnxProdWalk = PROD_WALK_MARKER);\n${mainOriginal}`,
  );
  execSync("npx vite build --outDir ../../_qoder_ui_build_20260920", { cwd: FRONTEND, stdio: "pipe" });

  await page.goto(`${PREVIEW}/v8/hub`, { waitUntil: "networkidle" });
  // A plain reload: no cache clearing, no hard reload, no unregistering anything.
  await page.reload({ waitUntil: "networkidle" });
  const markerSeen = await page.evaluate(() => window.__cnxProdWalk ?? null);
  const afterAssets = assetHrefs(await page.evaluate(() => document.documentElement.outerHTML));
  const workerScript = await page.evaluate(async () => {
    const registration = await navigator.serviceWorker.getRegistration();
    return registration?.active?.scriptURL ?? registration?.installing?.scriptURL ?? null;
  });
  record("B rebuild then plain reload", {
    markerReachedRunningPage: markerSeen,
    assetsBefore: beforeAssets,
    assetsAfter: afterAssets,
    assetNamesChanged: JSON.stringify(beforeAssets) !== JSON.stringify(afterAssets),
    activeWorkerScript: workerScript,
    rootChildren: await page.evaluate(() => document.querySelectorAll("#root > *").length),
  });
} finally {
  /* This edit is temporary by definition; leaving it behind would pollute a tracked file
     if anything above threw. */
  writeFileSync(mainPath, mainOriginal);
  if (existsSync(MARKER_FILE)) rmSync(MARKER_FILE);
  const dirty = execSync("git status --porcelain -- frontend/src", {
    cwd: "D:/moodle/_qoder_ui_overnight_20260920",
  })
    .toString()
    .trim();
  console.log(`  source restored; git status frontend/src: ${dirty === "" ? "clean" : dirty}`);
}

/* ============================ C. the AI sheet, both themes ================== */
for (const scheme of ["light", "dark"]) {
  const walkPage = await newPage(context, scheme);
  await walkPage.goto(`${PREVIEW}/v8/hub`, { waitUntil: "networkidle" });
  await awaitController(walkPage);
  await walkPage.getByTestId("hub-plan-with-ai").click();
  await walkPage.getByTestId("plan-ai-sheet").waitFor({ timeout: 15000 });
  const preflight = await walkPage.getByTestId("plan-ai-preflight").textContent().catch(() => null);
  await walkPage.getByTestId("plan-ai-input").fill("带爸妈去厦门三天，不要走太多路，酒店要靠近地铁。");
  await walkPage.getByTestId("plan-ai-submit").click();
  await walkPage.getByTestId("plan-ai-live").waitFor({ timeout: 15000 }).catch(() => undefined);
  const waitingFirst = await walkPage.getByTestId("plan-ai-elapsed").textContent().catch(() => null);
  await walkPage.waitForTimeout(2200);
  const waitingSecond = await walkPage.getByTestId("plan-ai-elapsed").textContent().catch(() => null);
  await walkPage.screenshot({ path: `${OUT}/prod-390-${scheme}-ai-waiting.png` });
  const result = await walkPage
    .getByTestId("plan-ai-result")
    .textContent({ timeout: 60000 })
    .catch(() => null);
  const resultStatus = await walkPage.getByTestId("plan-ai-result").getAttribute("data-result-status").catch(() => null);
  await walkPage.screenshot({ path: `${OUT}/prod-390-${scheme}-ai-result.png` });
  record(`C AI sheet (${scheme})`, {
    preflight: preflight?.trim() ?? null,
    waitingFirst: waitingFirst?.trim() ?? null,
    waitingSecond: waitingSecond?.trim() ?? null,
    /* Only two real readings can prove the number moved.  When the second read is null the
       request finished before it, which says nothing either way -- the elapsed claim is
       evidenced by the e2e node that holds the request open, not here. */
    secondsAdvanced:
      waitingFirst != null && waitingSecond != null && waitingFirst !== waitingSecond,
    waitingSecondMissingReason:
      waitingSecond == null
        ? "the waiting block was gone before the second read, so this walk cannot show the number moving"
        : null,
    resultStatus,
    resultText: result?.replace(/\s+/g, " ").trim().slice(0, 220) ?? null,
  });
  await walkPage.close();
}

/* ============================ D. horizontal overflow at 360 ================ */
const narrow = await newPage(context, "light");
await narrow.setViewportSize({ width: 360, height: 800 });
await narrow.goto(`${PREVIEW}/v8/hub`, { waitUntil: "networkidle" });
const overflow = await narrow.evaluate(() => ({
  scrollWidth: document.documentElement.scrollWidth,
  clientWidth: document.documentElement.clientWidth,
}));
await narrow.screenshot({ path: `${OUT}/prod-360-hub-light.png` });
record("D 360px width", { ...overflow, overflows: overflow.scrollWidth > overflow.clientWidth + 1 });
await narrow.close();

/* ---- cleanup: the marker must not survive the run -------------------------- */
writeFileSync(mainPath, mainOriginal);
if (existsSync(MARKER_FILE)) rmSync(MARKER_FILE);

await context.close();
await browser.close();

writeFileSync(`${OUT}/prod-walk.json`, JSON.stringify(report, null, 2) + "\n");
console.log(`\nwrote ${OUT}/prod-walk.json`);
