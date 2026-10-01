/**
 * ORD-0530 -- the English failure sentences, replayed at a moved tip, on a trip created for this run.
 *
 * `bac10f40_1404.md` names the cell this instrument closes: the empty and refused arms had been
 * read once, against a blank trip that already existed in my copy, and that trip was thrown away
 * through the product's own DELETE door during the run -- so a replay would have read a state the
 * earlier run left behind.  Here the blank trip is created through POST /api/v1/journeys at the
 * start of the run, so all three arms are fresh facts about the generation under measurement.
 *
 * Still no DOM surgery: empty = a trip that carries no stamp, unreachable = route.abort on the
 * read leg, refused = the trip's own DELETE door puts it in the recycle bin. The expected
 * sentences come out of `footprintCopy.ts` itself, so what is judged is whether the English copy
 * reaches the glass, not whether it exists in the file.
 */
import { chromium } from "playwright";
import { mkdirSync, readFileSync, writeFileSync } from "node:fs";

const BASE = process.env.ORD0530_BASE;
const BACKEND = process.env.ORD0530_BACKEND;
const TRAVELER = process.env.ORD0530_TRAVELER;
if (!BASE || !BACKEND || !TRAVELER) throw new Error("ORD0530_BASE / ORD0530_BACKEND / ORD0530_TRAVELER are required");
const SEEDED = "22222222-2222-4222-8222-222222222222";
const TABLE = "D:/moodle/_qoder_ai_ord0387_20260928/wt/frontend/src/features/checkin/footprintCopy.ts";
const TAG = process.env.ORD0530_TAG || "states_r7";
const GEN = process.env.ORD0530_GENERATION || "";
const args = process.argv.slice(2);
const outDir = args[args.indexOf("--out") + 1];
mkdirSync(outDir, { recursive: true });

function copyTable() {
  const src = readFileSync(TABLE, "utf8");
  const out = {};
  const re = /([A-Za-z]+):\s*\{((?:[^{}]|\{[^{}]*\})*)\}/gs;
  let m;
  while ((m = re.exec(src)) !== null) {
    const en = /en:\s*"((?:[^"\\]|\\.)*)"/s.exec(m[2]);
    if (en) out[m[1]] = en[1];
  }
  return out;
}
const EN = copyTable();
for (const k of ["empty", "unreachable", "refused"]) {
  if (!EN[k]) throw new Error(`no English sentence parsed for ${k} -- the judge is broken`);
}

const browser = await chromium.launch();
const report = { base: BASE, backend: BACKEND, tag: TAG, generation: GEN, locale: "en-US",
                 expected: { empty: EN.empty, unreachable: EN.unreachable, refused: EN.refused },
                 arms: [] };

/* A trip created for this run, through the product's create door. */
const boot = await browser.newContext();
const start = new Date();
const end = new Date(start.getTime() + 86400000);
/* The door's own rows are naive instants (`2026-10-01T11:28:08.698076`); a Z suffix arrives as an
   aware value and the end_at-must-follow-start_at rule then compares two shapes that do not match.
   Sending the naive form is how the rest of this store writes the column, not a way around the rule. */
const iso = (d) => d.toISOString().replace(/Z$/, "");
const created = await boot.request.post(`${BACKEND}/api/v1/journeys`, {
  data: { traveler_id: TRAVELER, title: `ORD-0530 English arm ${TAG}`, city_code: "TIANJIN",
          timezone: "Asia/Shanghai", start_at: iso(start), end_at: iso(end),
          budget: { amount_minor: 120000, currency: "CNY" }, planning_mode: "balanced" },
});
report.create_door = { http_status: created.status(),
                       body_head: (await created.text()).slice(0, 900) };
const BLANK = created.status() === 201
  ? JSON.parse(await created.text().catch(() => "{}")).id ?? "" : "";
if (BLANK.length < 10) {
  await boot.close();
  await browser.close();
  throw new Error(`the create door did not hand over a trip: ${JSON.stringify(report.create_door)}`);
}
report.sent_to_the_create_door = { start_at: iso(start), end_at: iso(end) };
report.blank_trip_created_for_this_run = BLANK;
await boot.close();

async function openScreen(page) {
  await page.goto(`${BASE}/v8/footprints`, { waitUntil: "load", timeout: 60000 });
  await page.waitForSelector("[data-testid='footprint-panel']", { timeout: 30000 });
  await page.waitForTimeout(2200);
  return page.evaluate(() => {
    const text = (el) => (el instanceof HTMLElement ? el.innerText.replace(/\s+/g, " ").trim() : "");
    const panel = document.querySelector("[data-testid='footprint-panel']");
    return { panel_text: text(panel),
             state_line: text(document.querySelector(".cn-footprints__state")),
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
  const read = await openScreen(page);
  const door = await page.request.get(`${BACKEND}/api/v1/journeys/${journey}/checkins`);
  const body = await door.text();
  const rec = { arm: name, journey, ...read,
                sentence_matches_table_en: read.state_line === EN[name],
                door_http_status: door.status(),
                door_reason_code_in_body: /reason_code/.test(body),
                reason_code_on_glass: /CHECKIN_[A-Z_]+/.test(read.panel_text),
                screaming_snake: (read.panel_text.match(/\b[A-Z][A-Z_]{3,}\b/g) || []).length,
                machine_tokens: read.panel_text.match(/FOREGROUND_WEB|footprint[A-Z]\w*|[a-z]+_[a-z]+_[a-z]+/g) || [],
                injected: name === "unreachable" ? "route.abort on the checkins read"
                          : name === "refused" ? "DELETE /api/v1/journeys/{id} on the trip this run created"
                          : "nothing injected -- the trip this run created carries no stamp" };
  await page.screenshot({ path: `${outDir}/footprints_${TAG}_${name}_en.png` });
  report.arms.push(rec);
  await context.close();
  return rec;
}

await arm("empty", BLANK);
await arm("unreachable", SEEDED, (page) => page.route("**/api/v1/journeys/*/checkins*",
  (route) => route.abort()));
const trashContext = await browser.newContext();
report.trash_door_status = (await trashContext.request
  .delete(`${BACKEND}/api/v1/journeys/${BLANK}`)).status();
await trashContext.close();
await arm("refused", BLANK);

report.arms_ok = report.arms.length === 3 && report.arms.every(
  (a) => a.sentence_matches_table_en && !a.reason_code_on_glass && a.rows === 0 && a.days === 0 &&
         a.machine_tokens.length === 0);
writeFileSync(`${outDir}/footprints_${TAG}.json`, JSON.stringify(report, null, 1), "utf8");
console.log("arms", report.arms.length, "arms_ok", report.arms_ok,
            "create", report.create_door.http_status, "trash", report.trash_door_status);
for (const a of report.arms) {
  console.log(`  ${a.arm} en_match ${a.sentence_matches_table_en} rows ${a.rows} days ${a.days}`,
              "door", a.door_http_status, "reason_on_glass", a.reason_code_on_glass,
              "snake", a.screaming_snake, "|", a.state_line.slice(0, 90));
}
console.log("out", `${outDir}/footprints_${TAG}.json`);
await browser.close();
