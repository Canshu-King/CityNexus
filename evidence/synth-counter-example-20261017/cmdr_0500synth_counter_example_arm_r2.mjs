/* CMDR synthetic-default counter-example r2 -- the arm the SYNTHETIC_DEFAULT closure was asked for.
 *
 * Question it answers by measurement, not by assertion: does that vocabulary row do anything?
 *   A1 table as shipped on the rev  -> the enum answers in a human word, in both languages
 *   A2 same table, that one row cut -> the very same call answers with the machine word itself
 * Same input, same function, one variable: the row.  A row that cannot change the answer is not a fix,
 * and a gate that only counts rows would not notice -- which is why this arm exists.
 *
 * Usage: node cmdr_0500synth_counter_example_arm_r2.mjs <40-hex rev>
 */
import { execFileSync } from "node:child_process";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { createRequire } from "node:module";

const require_ = createRequire(import.meta.url);
const REPO = "D:/moodle/CityNexus";
const FRONTEND = path.join(REPO, "frontend");
const LIB = path.join(FRONTEND, "src", "lib");
const SRC_REL = "src/lib/displayVocabulary.ts";
const NL = String.fromCharCode(10);
const REV = process.argv[2] || "";
if (!/^[0-9a-f]{40}$/.test(REV)) {
  console.error("usage: node this.mjs <40-hex rev> -- the arm pins its own generation on purpose");
  process.exit(2);
}
const OUT = "D:/moodle/_qoder_cmdr_ref_20260921/live_checks/_0500synth_counter_example_arm_r2.json";
const ENUM = "SYNTHETIC_DEFAULT";
const esbuild = require_(path.join(FRONTEND, "node_modules", "esbuild"));

const git = (args) => execFileSync("git", ["-C", REPO].concat(args), { encoding: "utf8" });

// one helper is imported from LocaleContext and is NOT on the measured path; both arms get the same
// stub, so the only difference left between them is the vocabulary row.
function isolate(text) {
  return text.split(NL)
    .map((l) => (/^import .*LocaleContext/.test(l)
      ? 'const dictionaryCopy = (...a) => String(a[0] ?? "");'
      : l))
    .join(NL);
}

function cutRow(text) {
  const lines = text.split(NL);
  const kept = lines.filter((l) => !new RegExp("^\\s*" + ENUM + "\\s*:").test(l));
  if (kept.length !== lines.length - 1) {
    throw new Error("expected to cut exactly one row, cut " + (lines.length - kept.length));
  }
  return kept.join(NL);
}

function bundle(srcAbs, name) {
  const out = path.join(LIB, "_cmdrSynthArm_" + name + ".cjs");
  esbuild.buildSync({ entryPoints: [srcAbs], bundle: true, format: "cjs", platform: "node",
                      outfile: out, logLevel: "silent" });
  return out;
}

function answers(modPath) {
  const mod = require_(modPath);
  const fn = mod.mobilityFactQualityLabel;
  if (typeof fn !== "function") throw new Error("mobilityFactQualityLabel not exported: " + modPath);
  return { zh: fn(ENUM, "zh-CN"), en: fn(ENUM, "en-US"),
           unknown_zh: fn("SOME_NAME_NO_ROW_HAS", "zh-CN"),
           unknown_en: fn("SOME_NAME_NO_ROW_HAS", "en-US") };
}

const scratch = [];
let code = 1;
try {
  const shippedText = git(["show", REV + ":frontend/" + SRC_REL]);
  const sourceBlob = git(["rev-parse", REV + ":frontend/" + SRC_REL]).trim();
  if (!shippedText.includes(ENUM + ":")) throw new Error("rev has no " + ENUM + " row at all");

  const tipTs = path.join(LIB, "_cmdrSynthArm_tip.ts");
  const mutTs = path.join(LIB, "_cmdrSynthArm_mutant.ts");
  scratch.push(tipTs, mutTs);
  fs.writeFileSync(tipTs, isolate(shippedText), "utf8");
  fs.writeFileSync(mutTs, isolate(cutRow(shippedText)), "utf8");

  const m1 = bundle(tipTs, "shipped");
  const m2 = bundle(mutTs, "mutant");
  scratch.push(m1, m2);
  const a1 = answers(m1);
  const a2 = answers(m2);

  const machineWord = new RegExp(ENUM);
  const report = {
    instrument: "cmdr_0500synth_counter_example_arm_r2", at: new Date().toISOString(),
    rev: REV, source_blob: sourceBlob, enum_under_test: ENUM, source: SRC_REL,
    shipped_row_count: shippedText.split(NL).filter((l) => l.trim().startsWith(ENUM + ":")).length,
    A1_shipped: a1, A2_row_deleted: a2,
    verdicts: {
      A1_answers_in_human_words: !machineWord.test(a1.zh) && !machineWord.test(a1.en) &&
                                 /合成默认值/.test(a1.zh) && /synthetic default/i.test(a1.en),
      A2_leaks_the_machine_word: machineWord.test(a2.zh) && machineWord.test(a2.en),
      only_variable_is_the_row: a1.unknown_zh === a2.unknown_zh && a1.unknown_en === a2.unknown_en,
    },
  };
  report.arm_discriminates = report.verdicts.A1_answers_in_human_words &&
                             report.verdicts.A2_leaks_the_machine_word &&
                             report.verdicts.only_variable_is_the_row;
  fs.writeFileSync(OUT, JSON.stringify(report, null, 1), "utf8");
  console.log(JSON.stringify({ rev: REV.slice(0, 10), shipped: a1, deleted: a2,
                               verdicts: report.verdicts, discriminates: report.arm_discriminates }));
  code = report.arm_discriminates ? 0 : 1;
} finally {
  for (const f of scratch) { try { fs.unlinkSync(f); } catch (e) { /* already gone */ } }
  const left = fs.readdirSync(LIB).filter((n) => n.indexOf("_cmdrSynthArm_") === 0);
  if (left.length) console.error("LEFTOVER scratch files: " + JSON.stringify(left));
  process.exit(code);   // exit only here: process.exit() inside a try skips the finally block
}
