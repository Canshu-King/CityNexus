/* CMDR lane cmdraA r1 - does the plan-ranking note say traveller words, and can the ruler tell?
 *
 * Why: the commander measured 27 painted `SYNTHETIC_DEFAULT` on `/v8/hub` (zh arm) because
 * `PlanRankingPanel.tsx` handed `row.evidence.worstQuality` straight into the `{quality}` slot. His own
 * sweep is the acceptance ruler; this file is the lane's counter-example ruler -- it fails when the
 * mapping is mutated, in either direction:
 *   STATIC  the dictionary loses an entry, loses its zh or its en side, or a label itself carries a
 *           machine shape; or the slot stops going through the mapping.
 *   PAINTED a real browser on the built bundle shows a note that still matches one of the sweep's four
 *           machine shapes, or loses the two numbers the fact depends on, or loses the dictionary's
 *           own wording.
 * One arm per run (`zh` or `en`), one evidence file per arm, single sequential browser -- concurrent
 * Chromium on this box makes the app count before it has painted.
 *
 * usage: node cmdra_hubenum_quality_words_check_r2.js <base> <out.json> <zh|en> <frontend/src dir>
 */
const { chromium } = require("D:/moodle/CityNexus/frontend/node_modules/playwright");
const crypto = require("crypto");
const fs = require("fs");

const BASE = process.argv[2];
const OUT = process.argv[3];
const LOCALE = process.argv[4];
const SRC = process.argv[5];
if (!BASE || !OUT || !LOCALE || !SRC) {
  console.error("usage: node cmdra_hubenum_quality_words_check_r2.js <base> <out> <zh|en> <frontend/src>");
  process.exit(2);
}
const ZH = LOCALE.startsWith("zh");

/* The four shapes, copied verbatim from cmdr_machine_speech_sweep_r1.js:52-56 so this ruler cannot be
   more permissive than the one the commander reads. */
const SHAPES = [
  { kind: "UPPER_SNAKE", re: /\b[A-Z][A-Z0-9]*(?:_[A-Z0-9]+){1,}\b/ },
  { kind: "IANA_ZONE", re: /\b(?:Africa|America|Antarctica|Arctic|Asia|Atlantic|Australia|Europe|Indian|Pacific)\/[A-Za-z_]+(?:\/[A-Za-z_]+)?\b/ },
  { kind: "LOWER_SNAKE_KEY", re: /\b[a-z][a-z0-9]*(?:_[a-z0-9]+){1,}\b/ },
  { kind: "ALLCAPS_WORD", re: /\b[A-Z]{4,}\b/ },
];
const ALLOW = ["UTC", "GMT", "PDF", "ID", "URL", "API", "AI", "GPS", "OSM", "OK", "FAQ", "COPILOT"];

function machineShapeHit(text) {
  for (const s of SHAPES) {
    const m = text.match(s.re);
    if (!m) continue;
    if (s.kind === "ALLCAPS_WORD" && ALLOW.includes(m[0])) continue;
    if (s.kind === "ALLCAPS_WORD" && /[_]/.test(m[0])) continue;
    return { kind: s.kind, token: m[0] };
  }
  return null;
}

/* The two sides of the wording this screen is entitled to, taken from the source the bundle was built
   from -- not retyped here, so a copy edit cannot quietly make the assertion vacuous. */
const VOCAB = `${SRC}/lib/displayVocabulary.ts`;
const PANEL = `${SRC}/features/planning/PlanRankingPanel.tsx`;
const vocabText = fs.readFileSync(VOCAB, "utf8");
const panelText = fs.readFileSync(PANEL, "utf8");

function blockOf(source, marker) {
  const start = source.indexOf(marker);
  if (start < 0) return null;
  const open = source.indexOf("{", start);
  if (open < 0) return null;
  let depth = 0;
  for (let i = open; i < source.length; i += 1) {
    if (source[i] === "{") depth += 1;
    else if (source[i] === "}") {
      depth -= 1;
      if (depth === 0) return source.slice(open, i + 1);
    }
  }
  return null;
}

const qualityTable = blockOf(vocabText, "const MOBILITY_FACT_QUALITY: Record<string, Label>");
const unlistedBlock = blockOf(vocabText, "const MOBILITY_FACT_QUALITY_UNLISTED: Label");

function labelPair(text) {
  if (!text) return null;
  const zh = (text.match(/zh:\s*"([^"]*)"/) || [])[1];
  const en = (text.match(/en:\s*"([^"]*)"/) || [])[1];
  return { zh: zh === undefined ? null : zh, en: en === undefined ? null : en };
}
function entryOf(block, key) {
  if (!block) return null;
  const at = block.indexOf(key);
  return at < 0 ? null : block.slice(at);
}

const staticChecks = [];
function check(id, ok, observed) {
  staticChecks.push({ id, verdict: ok ? "PASS" : "FAIL", observed });
  return ok;
}

const synth = labelPair(entryOf(qualityTable, "SYNTHETIC_DEFAULT"));
check("dict_block_present", qualityTable !== null, "MOBILITY_FACT_QUALITY block found: " + (qualityTable !== null));
check("dict_synthetic_has_zh", Boolean(synth && synth.zh), `zh side: ${synth && JSON.stringify(synth.zh)}`);
check("dict_synthetic_has_en", Boolean(synth && synth.en), `en side: ${synth && JSON.stringify(synth.en)}`);
check("dict_labels_carry_no_machine_shape",
  Boolean(synth) && !machineShapeHit(synth.zh || "") && !machineShapeHit(synth.en || ""),
  `zh hit ${synth ? JSON.stringify(machineShapeHit(synth.zh || "")) : "n/a"}, en hit ${synth ? JSON.stringify(machineShapeHit(synth.en || "")) : "n/a"}`);
const unlisted = labelPair(unlistedBlock);
check("unlisted_block_present", unlistedBlock !== null, "MOBILITY_FACT_QUALITY_UNLISTED found: " + (unlistedBlock !== null));
check("unlisted_has_both_sides", Boolean(unlisted && unlisted.zh && unlisted.en),
  `zh ${unlisted && JSON.stringify(unlisted.zh)}, en ${unlisted && JSON.stringify(unlisted.en)}`);
check("unlisted_falls_back_without_the_token",
  Boolean(unlisted) && !machineShapeHit(unlisted.zh) && !machineShapeHit(unlisted.en)
  && !unlisted.zh.includes("SYNTHETIC") && !unlisted.en.includes("SYNTHETIC"),
  `unlisted zh/en both readable and free of any server name`);
check("slot_does_not_hand_the_enum_to_the_sentence",
  !/quality:\s*row\.evidence\.worstQuality\s*(?:\?\?|,|\})/.test(panelText),
  "the slot value is not the enum handed over as-is (a branch that routes it through words first is what the order asks for)");
check("slot_goes_through_the_mapping",
  /mobilityFactQualityLabel\(/.test(panelText) && /import\s*\{[^}]*mobilityFactQualityLabel[^}]*\}\s*from\s*"[^"]*lib\/displayVocabulary"/.test(panelText),
  "the panel imports mobilityFactQualityLabel from lib/displayVocabulary and calls it for this slot");
/* The order closes uppercase names on this screen. `pick` ends in `rawChannel`, whose whole purpose is
   to paint the labelled server name, so a mapping built on `pick` leaves exactly the shape the order
   shuts: an unlisted grade returns as `SYNTHETIC_...` on the traveller's note. */
const fnStart = vocabText.indexOf("export function mobilityFactQualityLabel");
const fnBody = fnStart < 0 ? "" : vocabText.slice(fnStart, vocabText.indexOf("}", vocabText.indexOf("{", fnStart)) + 1);
check("mapping_is_exported", fnBody.length > 0, "mobilityFactQualityLabel is exported: " + (fnBody.length > 0));
check("unlisted_grade_cannot_paint_the_server_name",
  fnBody.length > 0 && !/[^A-Za-z_]pick\(/.test(fnBody) && !/rawChannel/.test(fnBody) && /UNLISTED/.test(fnBody),
  `mapping body read back: ${JSON.stringify(fnBody.replace(/\s+/g, " ").slice(0, 240))}`);
check("null_quality_keeps_its_own_reading", /[Qq]uality === null/.test(panelText),
  "the no-tag case is still branched before the dictionary");
/* planRanking.ts:78 filters the two hard-eligible qualities out of worstQuality, so words for them in
   this table would put a "the rest are ..." claim on a leg the gate already counted as hard. */
check("table_names_only_grades_the_slot_can_hold",
  Boolean(qualityTable) && !/EXPLICIT_FROZEN_FIXTURE/.test(qualityTable) && !/LIVE_PROVIDER_CAPTURE/.test(qualityTable),
  `hard-eligible qualities kept out of the note table: ${JSON.stringify(qualityTable)}`);

const expected = ZH ? (synth && synth.zh) : (synth && synth.en);

async function main() {
  const browser = await chromium.launch({ channel: "chrome", headless: true });
  const ctx = await browser.newContext({ viewport: { width: 390, height: 844 }, hasTouch: true, locale: LOCALE });
  const page = await ctx.newPage();
  const pageErrors = [];
  page.on("pageerror", (e) => pageErrors.push(String(e).slice(0, 160)));
  await page.goto(BASE, { waitUntil: "networkidle", timeout: 90000 });
  for (const cand of [page.getByText("使用封存的演示行程", { exact: false }).first(),
                      page.getByText(/sealed demo trip/i).first()]) {
    if (await cand.count()) { await cand.click(); await page.waitForTimeout(4500); break; }
  }
  await page.goto(BASE.replace(/\/$/, "") + "/v8/hub", { waitUntil: "domcontentloaded", timeout: 60000 });
  await page.waitForTimeout(2500);

  const read = await page.evaluate(() => {
    const panel = document.querySelector('[data-testid="plan-ranking"]');
    const notes = Array.from(document.querySelectorAll('[data-testid="rank-note"]'));
    const evidenceCells = Array.from(document.querySelectorAll('[data-testid^="rank-cell-evidence"]'))
      .map((td) => (td.textContent || "").trim());
    return {
      panelPresent: Boolean(panel),
      noteCount: notes.length,
      noteTexts: notes.map((li) => (li.textContent || "").replace(/\s+/g, " ").trim()),
      noteTokens: notes.map((li) => li.getAttribute("data-quality") || ""),
      evidenceCells,
      journeyId: localStorage.getItem("citynexus.v8.journey_id") || "",
    };
  });

  const painted = [];
  read.noteTexts.forEach((text, index) => {
    const hit = machineShapeHit(text);
    if (hit) painted.push({ index, ...hit, text_head: text.slice(0, 110) });
  });
  const numbersKept = read.noteTexts.map((text, index) => {
    const cell = read.evidenceCells[index] || "";
    const hard = cell.split("/")[0];
    const total = cell.split("/")[1];
    if (!hard || !total) return { index, verdict: "FAIL", observed: `evidence cell ${JSON.stringify(cell)} is not <hard>/<total>` };
    const ok = text.includes(hard) && text.includes(total);
    return { index, verdict: ok ? "PASS" : "FAIL", observed: ok
      ? `note keeps hard=${hard} and total=${total}`
      : `note lost hard=${hard} or total=${total}: ${JSON.stringify(text.slice(0, 110))}` };
  });
  const wording = read.noteTexts.map((text, index) => ({
    index,
    verdict: expected && text.includes(expected) ? "PASS" : "FAIL",
    observed: `${JSON.stringify(expected)} ${expected && text.includes(expected) ? "is painted" : "is NOT painted"} on note ${index}`,
  }));

  const arms = [
    { id: "panel_reached", verdict: read.panelPresent && read.noteCount > 0 ? "PASS" : "FAIL",
      observed: `panelPresent=${read.panelPresent} noteCount=${read.noteCount} journeyId=${read.journeyId || "(none)"} -- a 0-hit run on an unreached panel is NOT green` },
    { id: "no_machine_shape_painted", verdict: painted.length === 0 ? "PASS" : "FAIL",
      observed: painted.length === 0 ? "0 of " + read.noteCount + " notes match the sweep's four shapes"
        : JSON.stringify(painted.slice(0, 3)) },
    { id: "facts_survive_the_mapping", verdict: numbersKept.length > 0 && numbersKept.every((n) => n.verdict === "PASS") ? "PASS" : "FAIL",
      observed: JSON.stringify(numbersKept.slice(0, 3)) },
    { id: "dictionary_wording_is_what_shows", verdict: wording.length > 0 && wording.every((n) => n.verdict === "PASS") ? "PASS" : "FAIL",
      observed: JSON.stringify(wording.slice(0, 3)) },
    { id: "no_page_error", verdict: pageErrors.length === 0 ? "PASS" : "FAIL", observed: JSON.stringify(pageErrors.slice(0, 3)) },
  ];
  const all = staticChecks.concat(arms);
  const reds = all.filter((a) => a.verdict === "FAIL").map((a) => a.id);
  const report = {
    instrument: "cmdra_hubenum_quality_words_check_r2",
    script_sha256: crypto.createHash("sha256").update(fs.readFileSync(__filename)).digest("hex"),
    base: BASE, locale: LOCALE, viewport: "390x844", src_dir: SRC,
    shapes_reused_from: "cmdr_machine_speech_sweep_r1.js:52-56",
    expected_label_for_this_arm: expected,
    read: { panelPresent: read.panelPresent, noteCount: read.noteCount,
            evidenceCells: read.evidenceCells.slice(0, 3), journeyId: read.journeyId,
            note_samples: read.noteTexts.slice(0, 3), data_quality_values: read.noteTokens.slice(0, 3) },
    static_checks: staticChecks, painted_arms: arms, verdict: reds.length ? "RED" : "GREEN",
    red_arms: reds,
  };
  fs.writeFileSync(OUT, JSON.stringify(report, null, 2));
  await ctx.close();
  await browser.close();
  console.log(JSON.stringify({ out: OUT, locale: LOCALE, verdict: report.verdict, red_arms: reds,
    noteCount: read.noteCount, expected_label_for_this_arm: expected }, null, 2));
  process.exit(reds.length ? 1 : 0);
}
main().catch((e) => { console.error("FATAL", e); process.exit(1); });
