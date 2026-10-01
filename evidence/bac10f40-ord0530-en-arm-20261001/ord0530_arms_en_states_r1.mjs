/**
 * ORD-0530 -- the English arm's three failure sentences, read off the glass.
 *
 * r3 names the English arm as the cell it did not verify.  The grouping and the row cells were
 * covered by `ord0530_screen_read_r5.mjs`; what is left are the three shapes that only appear when
 * the door gives nothing back, because those sentences live in the same zh/en table and a missing
 * English entry there puts a machine key on the screen instead of a sentence.
 *
 * All three states are reached through the product, not by editing the DOM:
 *   empty        a trip in this copy that carries no stamp
 *   unreachable  `route.abort` on the checkins read -- a failure, not a doctored answer
 *   refused      the trip's own DELETE door puts it in the recycle bin, the read then answers 409
 * The destructive one runs last so it cannot take a reading the earlier arms still need.
 */
import { chromium } from "playwright";
import { mkdirSync, readFileSync, writeFileSync } from "node:fs";

const BASE = process.env.ORD0530_BASE ?? "http://127.0.0.1:4795";
const BACKEND = process.env.ORD0530_BACKEND ?? "http://127.0.0.1:52508";
const SEEDED = "22222222-2222-4222-8222-222222222222";
const BLANK = "94669bae-e333-4bab-87cf-8c84ef3ad5c8";   // a trip in my copy with no stamps at all
const TABLE = "D:/moodle/_qoder_ai_ord0387_20260928/wt/frontend/src/features/checkin/footprintCopy.ts";
const args = process.argv.slice(2);
const outDir = args[args.indexOf("--out") + 1];
const tag = args[args.indexOf("--tag") + 1];
mkdirSync(outDir, { recursive: true });

function copyTable() {
  const src = readFileSync(TABLE, "utf8");
  const out = {};
  const re = /([A-Za-z]+):\s*\{((?:[^{}]|\{[^{}]*\})*)\}/gs;
  let m;
  while ((m = re.exec(src)) !== null) {
    const en = /en:\s*"((?:[^"\\]|\\.)*)"/s.exec(m[2]);
    const zh = /zh:\s*"((?:[^"\\]|\\.)*)"/s.exec(m[2]);
    if (en || zh) out[m[1]] = { en: en ? en[1] : null, zh: zh ? zh[1] : null };
  }
  return out;
}

const COPY = copyTable();
for (const k of ["empty", "unreachable", "refused"]) {
  if (!COPY[k] || !COPY[k].en) throw new Error(`no English sentence parsed for ${k}`);
}

const browser = await chromium.launch();
const report = { base: BASE, backend: BACKEND, tag, locale: "en-US",
                 expected: { empty: COPY.empty.en, unreachable: COPY.unreachable.en,
                             refused: COPY.refused.en },
                 arms: [] };

async function openScreen(page, journey) {
  await page.goto(`${BASE}/v8/footprints`, { waitUntil: "load", timeout: 60000 });
  await page.waitForSelector("[data-testid='footprint-panel']", { timeout: 30000 });
  await page.waitForTimeout(2000);
  return page.evaluate(() => {
    const text = (el) => (el instanceof HTMLElement ? el.innerText.replace(/\s+/g, " ").trim() : "");
    const panel = document.querySelector("[data-testid='footprint-panel']");
    const state = document.querySelector(".cn-footprints__state");
    return { panel_text: text(panel),
             state_line: text(state),
             rows: Array.from(document.querySelectorAll("[data-testid='footprint-row']")).length,
             days: Array.from(document.querySelectorAll("[data-testid='footprint-day']")).length };
  });
}

async function arm(name, journey, prepare) {
  const context = await browser.newContext({ viewport: { width: 390, height: 844 },
                                            locale: "en-US", timezoneId: "America/Los_Angeles" });
  const page = await context.newPage();
  await page.addInitScript((o) => {
    localStorage.setItem("citynexus.v8.journey_id", o.journey);
    localStorage.setItem("citynexus.locale", "en-US");
  }, { journey });
  if (prepare) await prepare(page);
  const read = await openScreen(page, journey);
  const door = await page.request.get(`${BACKEND}/api/v1/journeys/${journey}/checkins`);
  const body = await door.text();
  const rec = { arm: name, journey, ...read,
                sentence_matches_table_en: read.state_line === COPY[name].en,
                state_line_is_the_only_claim: read.state_line.length > 0,
                door_http_status: door.status(),
                door_reason_code_in_body: /reason_code/.test(body),
                reason_code_on_glass: /CHECKIN_[A-Z_]+/.test(read.panel_text),
                screaming_snake: (read.panel_text.match(/\b[A-Z][A-Z_]{3,}\b/g) || []).length,
                injected: name === "unreachable" ? "route.abort on the checkins read"
                          : name === "refused" ? "DELETE /api/v1/journeys/{id} put the trip in the recycle bin"
                          : "nothing injected -- this trip simply carries no stamp" };
  await page.screenshot({ path: `${outDir}/footprints_${tag}_${name}_en.png` });
  report.arms.push(rec);
  await context.close();
  return rec;
}

/* `--only=unreachable` is for replays: the blank trip this copy uses was already thrown away
   through the product's own door in the first run, so re-running the empty or refused arm here
   would read a state the earlier run left behind and call it a new fact. */
const only = (args.find((a) => a.startsWith("--only=")) || "").split("=")[1];
const want = (n) => !only || only.split(",").includes(n);

await (want("empty") ? arm("empty", BLANK) : Promise.resolve());
await (want("unreachable")
  ? arm("unreachable", SEEDED, (page) => page.route("**/api/v1/journeys/*/checkins*",
    (route) => route.abort()))
  : Promise.resolve());
if (want("refused")) {
  /* Destructive, so it runs last: the trip is thrown away through the product's own door. */
  const trashContext = await browser.newContext();
  report.trash_door_status = (await trashContext.request
    .delete(`${BACKEND}/api/v1/journeys/${BLANK}`)).status();
  await trashContext.close();
  await arm("refused", BLANK);
}

report.expected_arms = only ? only.split(",").length : 3;
report.arms_ok = report.arms.length === report.expected_arms &&
  report.arms.every((a) => a.sentence_matches_table_en && !a.reason_code_on_glass && a.rows === 0 &&
                           a.days === 0);
writeFileSync(`${outDir}/footprints_${tag}.json`, JSON.stringify(report, null, 1), "utf8");
console.log("arms", report.arms.length, "arms_ok", report.arms_ok, "trash", report.trash_door_status);
for (const a of report.arms) {
  console.log(`  ${a.arm} en_match ${a.sentence_matches_table_en} rows ${a.rows} days ${a.days}`,
             "door", a.door_http_status, "reason_on_glass", a.reason_code_on_glass,
             "|", a.state_line.slice(0, 96));
}
console.log("out", `${outDir}/footprints_${tag}.json`);
await browser.close();
