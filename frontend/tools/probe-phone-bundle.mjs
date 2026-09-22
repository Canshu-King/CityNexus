/* ORD-0221/0222 follow-up: read this lane's targets on the bundle the phone actually gets.
 *
 * Read-only by construction: every non-GET to the two creation endpoints is aborted before it
 * leaves the page, and the probe counts them so the receipt proves whether the guard fired.
 * Nothing here clicks 确认创建, so no journey is written to the preview database.
 *
 * Run:  cd frontend && node ../review/probe-phone-bundle.mjs
 */
import { chromium } from "playwright";
import { writeFileSync, readFileSync } from "node:fs";
import { createHash } from "node:crypto";

const BASE = process.env.CNX_PREVIEW ?? "http://127.0.0.1:4781";
const DEPLOYED_DIST = process.env.CNX_DEPLOYED_DIST ?? "D:/moodle/_qoder_preview_20260920/dist";
const OUT = "../review/evidence/ui-overnight/phone-bundle-readings.json";

const bundle = await (await fetch(`${BASE}/`)).text();
const bundleName = (bundle.match(/assets\/index-[A-Za-z0-9_-]+\.js/) ?? ["(none)"])[0];
/* A filename is not a coordinate: content-hash what the preview serves and compare it with the
   deployed artifact on disk, so this receipt cannot be quoting some other build's file. */
const servedBytes = new Uint8Array(await (await fetch(`${BASE}/${bundleName}`)).arrayBuffer());
const servedSha256 = createHash("sha256").update(servedBytes).digest("hex");
const onDiskSha256 = createHash("sha256")
  .update(readFileSync(`${DEPLOYED_DIST}/${bundleName}`))
  .digest("hex");

const browser = await chromium.launch();
const context = await browser.newContext({
  viewport: { width: 390, height: 844 },
  hasTouch: true,
  locale: "zh-CN",
});
const page = await context.newPage();

const blockedWrites = [];
const requests = [];
await page.route("**/api/v1/**", async (route) => {
  const request = route.request();
  if (request.method() !== "GET" && /\/(travelers|journeys)\/?$/.test(new URL(request.url()).pathname)) {
    blockedWrites.push(`${request.method()} ${new URL(request.url()).pathname}`);
    await route.abort();
    return;
  }
  await route.fallback();
});
page.on("request", (request) => {
  const url = new URL(request.url());
  if (url.pathname.startsWith("/api/")) requests.push(`${request.method()} ${url.pathname}`);
});

const read = async (selector) => {
  const handle = await page.$(selector);
  if (!handle) return { selector, exists: false, text: "", rect: null, inViewport: false };
  const info = await handle.evaluate((el) => {
    const box = el.getBoundingClientRect();
    const style = getComputedStyle(el);
    return {
      text: (el.textContent ?? "").replace(/\s+/g, " ").trim(),
      rect: { top: Math.round(box.top), bottom: Math.round(box.bottom), height: Math.round(box.height), width: Math.round(box.width) },
      srOnly: !!el.closest(".v8-sr-only"),
      position: style.position,
      stickyAncestor: !!el.closest('[class*="sticky"]'),
      opacity: style.opacity,
      innerHeight: window.innerHeight,
      scrollY: Math.round(window.scrollY),
    };
  });
  return {
    selector,
    exists: true,
    text: info.text,
    rect: info.rect,
    insideSrOnly: info.srOnly,
    position: info.position,
    stickyAncestor: info.stickyAncestor,
    opacity: info.opacity,
    scrollY: info.scrollY,
    inViewport: info.rect.bottom > 0 && info.rect.top < info.innerHeight,
  };
};

await page.goto(`${BASE}/v8/hub`, { waitUntil: "load" });
await page.waitForSelector('[data-testid="trial-setup"]', { timeout: 30_000 });

const entry = await read('[data-testid="trial-tianjin-demo"]');
const wizardText = (await page.locator('[data-testid="trial-setup"]').innerText()).replace(/\s+/g, " ");

await page.fill('[data-testid="trial-city"]', "天津");
await page.fill('[data-testid="trial-arrival"]', "天津站");
await page.fill('[data-testid="trial-departure"]', "北京南站");
await page.click('[data-testid="trial-next"]');
await page.waitForSelector('[data-testid="trial-step2-body"]', { timeout: 20_000 });
await page.fill('[data-testid="trial-budget"]', "0");
await page.waitForTimeout(1_200);

await page.click('[data-testid="trial-next"]', { force: true });
/* The fix was an *instant* reveal, so the first sample is taken 150 ms after the press -- before any
   animation could have carried the hint into view. `scrollBehaviour` below says whether one exists. */
await page.waitForTimeout(150);
const hintAt150 = await read('[data-testid="trial-required-hint"]');
const scrollAt150 = await page.evaluate(() => Math.round(window.scrollY));
await page.waitForTimeout(550);
const hintAfterPress = await read('[data-testid="trial-required-hint"]');
const spokenAfterPress = await read("#trial-next-reason");
/* A hint read mid-fade reports opacity 0 while already correct on screen; settle before judging. */
await page
  .waitForFunction(
    () => {
      const el = document.querySelector('[data-testid="trial-required-hint"]');
      return !el || getComputedStyle(el).opacity === "1";
    },
    undefined,
    { timeout: 5000 },
  )
  .catch(() => {});
const hintSettled = await read('[data-testid="trial-required-hint"]');
const scrollBehaviour = await page.evaluate(() => ({
  html: getComputedStyle(document.documentElement).scrollBehavior,
  body: getComputedStyle(document.body).scrollBehavior,
}));

await page.fill('[data-testid="trial-budget"]', "1500");
await page.waitForTimeout(700);
const hintAfterFix = await read('[data-testid="trial-required-hint"]');
const spokenAfterFix = await read("#trial-next-reason");

await page.click('[data-testid="trial-next"]');
await page.waitForSelector('[data-testid="trial-step3-body"]', { timeout: 20_000 });
const hintAtStep3 = await read('[data-testid="trial-required-hint"]');
const spokenAtStep3 = await read("#trial-next-reason");

const receipt = {
  generatedBy: "e345b9d6",
  at: new Date().toISOString(),
  base: BASE,
  servedBundle: bundleName,
  servedBundleIdentity: {
    bytes: servedBytes.byteLength,
    servedSha256,
    deployedDistOnDiskSha256: onDiskSha256,
    sameBytes: servedSha256 === onDiskSha256,
    deployedDist: DEPLOYED_DIST,
  },
  read_only_guarantee: {
    note: "non-GET to /travelers or /journeys is aborted in-page; 确认创建 is never clicked",
    blockedWrites,
    requestsSeen: requests.length,
    creationPostsAttempted: requests.filter((line) => line.startsWith("POST")).length,
  },
  ord0216_4_entry_copy: { label: entry.text, wizardScreenMentionsCity: /天津|Tianjin|广州|Guangzhou/.test(wizardText) },
  ord0220_3_and_0222_1_hint_reachability: { afterPress: hintAfterPress, afterFix: hintAfterFix },
  ord0222_1_instant_reveal: {
    note: "sampled 150 ms after the refused press, before any tween could carry the hint in; the fix was an instant scrollIntoView, not a sticky bar",
    scrollAt150,
    at150: hintAt150,
    settled: hintSettled,
    scrollBehaviour,
  },
  ord0222_2_after_create: {
    not_measured_here: "this probe aborts every creation POST by construction, so 确认创建 is never clicked",
    measured_on_same_bytes:
      "node ord0222-6-the-announcement-is-still-gone-after-the-trip-exists, played against the deployed dist with a real create on this lane's own throwaway database (run101513, playwright.deployed-bundle.config.ts)",
  },
  ord0220_2_announcement: { afterPress: spokenAfterPress, afterFix: spokenAfterFix, atStep3: spokenAtStep3 },
  ord0222_2_visible_hint_at_step3: hintAtStep3,
};
writeFileSync(OUT, JSON.stringify(receipt, null, 2) + "\n", "utf-8");
console.log(JSON.stringify(receipt, null, 1));
await browser.close();
