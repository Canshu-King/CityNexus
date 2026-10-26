import { chromium } from "file:///D:/moodle/_cmdr_rescue_v3_1022/frontend/node_modules/playwright/index.mjs";
import fs from "node:fs";

const URL = process.env.PAIR_URL || "";
const DIR = "D:/moodle/_cmdr_rescue_v3_1022/trial/results/20261026_gozero";
const OUT = `${DIR}/plans-updated-wiring-390.txt`;
const NL = String.fromCharCode(10);
const lines = [];
const note = (v) => { lines.push(v); fs.writeFileSync(OUT, lines.join(NL) + NL, "utf8"); };

const ctx = await chromium.launchPersistentContext("D:/moodle/_cmdr_v3_live_1022/_chrome_plans_updated", {
  channel: "chrome", headless: false, viewport: { width: 390, height: 844 },
});
const page = ctx.pages()[0] ?? await ctx.newPage();
let mapPlaces = 0;
page.on("response", (resp) => {
  const url = resp.url();
  if (/\/map-places/.test(url)) { mapPlaces += 1; note(`MAP_PLACES ${resp.request().method()} ${resp.status()} #${mapPlaces}`); }
});

await page.goto(URL, { waitUntil: "domcontentloaded", timeout: 60000 });
await page.waitForTimeout(12000);
const probe = await page.evaluate(() => ({
  keys: Object.keys(localStorage),
  v8: localStorage.getItem("citynexus.v8.journey_id"),
  legacy: localStorage.getItem("citynexus.demo.journey_id"),
  body: (document.body.innerText || "").slice(0, 200),
}));
note(`LS_KEYS ${JSON.stringify(probe.keys)}`);
note(`BODY ${JSON.stringify(probe.body)}`);
const journeyId = probe.v8 || probe.legacy;
note(`JOURNEY ${journeyId}`);
const before = mapPlaces;
note(`BASELINE ${before}`);

// This is the same event the presenter dispatches after a real acceptance.  We are testing whether
// the journey screen has a reader for it; the click path itself is not being simulated here.
if (journeyId) {
  await page.evaluate((id) => window.dispatchEvent(new CustomEvent("citynexus:plans-updated", { detail: id })), journeyId);
  await page.waitForTimeout(4000);
}
note(`AFTER_DISPATCH ${mapPlaces}`);
note(`DELTA ${mapPlaces - before}`);
await ctx.close();
