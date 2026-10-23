/**
 * Exercise the shipped refusal sentence in the browser that runs it.
 *
 * There is no frontend unit layer in this tree, so the only honest way to see all arms of
 * `infeasibleAtDepartureSentence` at once -- including the one the walk cannot reach tonight (an id the plan
 * does not carry) -- is to import the very module the dev server serves to the traveller and call it with
 * the gate's own row shapes.  This is a supplement to the real walk, not a substitute for it: the walk is
 * what proves the sentence reaches the screen.
 */
import fs from "node:fs";
import path from "node:path";
import { createRequire } from "node:module";

const require = createRequire("D:/moodle/_cmdr_rescue_v3_1022/frontend/package.json");
const { chromium } = require("playwright");

const OUT = "D:/moodle/_cmdr_rescue_v3_1022/trial/results/20261022_v3_human_chrome";
const BASE = process.env.PROBE_BASE || "http://127.0.0.1:14496";
const LOG = process.env.PROBE_LOG || "infeasible-sentence-arms-1.txt";
const stream = fs.openSync(path.join(OUT, LOG), "a");
const flat = (v) => String(v ?? "").replace(/\s+/g, " ").trim();
const say = (t) => { fs.writeSync(stream, t + "\n"); process.stdout.write(t + "\n"); };

const browser = await chromium.connectOverCDP("http://127.0.0.1:9335", { timeout: 120000 });
const context = browser.contexts()[0] ?? await browser.newContext();
const page = await context.newPage();
await page.goto(BASE + "/revolution", { waitUntil: "domcontentloaded", timeout: 60000 });
await page.waitForTimeout(4000);

const cases = await page.evaluate(async () => {
  const mod = await import("/src/trial/mobile/departureGaps.ts");
  const fn = mod.infeasibleAtDepartureSentence;
  const named = (id) => (id === "real-place-badaling" ? "八达岭长城（一日往返）" : null);
  return {
    closed_named: fn(["PLACE_CLOSED:real-place-badaling"], named),
    closed_unnamed: fn(["PLACE_CLOSED:real-place-badaling"], () => null),
    closed_two_of_three: fn(["PLACE_CLOSED:real-place-badaling", "PLACE_CLOSED:real-place-mutianyu", "PLACE_CLOSED:real-place-yiheyuan"], named),
    gap_unchanged: fn(["INSUFFICIENT_TRAVEL_GAP:real-place-a|real-place-b"], named),
    closed_plus_gap: fn(["PLACE_CLOSED:real-place-badaling", "INSUFFICIENT_TRAVEL_GAP:real-place-a|real-place-b"], named),
    unknown_code_still_shown: fn(["SOMETHING_NEW:x"], named),
    empty_rows: fn([], named),
    module_url: "/src/trial/mobile/departureGaps.ts",
  };
}).catch((error) => ({ probe_error: flat(error.message).slice(0, 200) }));

for (const [key, value] of Object.entries(cases)) say(`ARM ${key} :: ${flat(value)}`);
const anyRawCode = Object.entries(cases)
  .filter(([key]) => key.startsWith("closed_"))
  .filter(([, value]) => String(value).includes("PLACE_CLOSED"));
say(`RAW_CODE_LEAKS_INTO_CLOSED_ARMS=${anyRawCode.length}`);
say(`PROBE_DONE ${new Date().toISOString()}`);
await page.close().catch(() => undefined);
await browser.close().catch(() => undefined);
