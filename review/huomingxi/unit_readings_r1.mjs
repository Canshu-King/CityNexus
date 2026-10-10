// ORD-0558 · 活明细 · unit-readings instrument.
// Reads the FIVE site lines out of the working tree's real ActivityDetail.tsx bytes,
// asserts each recorded template is a byte substring of that line (no hand-written copy),
// then evaluates the real template for count=1 and count=2 and prints the screen string.
// It also calls the REAL lib/plural.ts (transpiled by the repo's own typescript) with the
// same unit strings so the "if we had put the ruler here" reading is measured, not guessed.
import fs from "node:fs";
import path from "node:path";
import { createRequire } from "node:module";

const require = createRequire(import.meta.url);
const ts = require(process.env.CNX_TS);
const WT = process.env.CNX_WT;
const PLURAL_TMP = "D:/moodle/_qoder_huomingxi_0558/plural_real.mjs";

const REL = "frontend/src/features/trip/ActivityDetail.tsx";
const src = fs.readFileSync(path.join(WT, REL), "utf8").split(/\r?\n/);

const sites = [
  { line: 150, tpl: "`${duration} min`", vars: ["duration"], states: [1, 2] },
  { line: 186, tpl: "`${activity.travel_from_prev_min} min`", vars: ["activity"], states: [1, 2] },
  { line: 279, tpl: "`All within about ${nearbyRadiusM} m, ordered by straight-line distance.`", vars: ["nearbyRadiusM"], states: [1, 2] },
  { line: 294, tpl: "`${Math.round(metres)} m`", vars: ["metres"], states: [1, 2] },
  { line: 297, tpl: "`${(metres / 1000).toFixed(1)} km`", vars: ["metres"], states: [1000, 2400] },
];

const unitFor = { 150: "min", 186: "min", 279: "m", 294: "m", 297: "km" };

const m = await import("file:///" + PLURAL_TMP.replace(/\\/g, "/"));
const out = [];
out.push(`wt=${WT}`);
out.push(`file=${REL}`);
out.push(`file_lines=${src.length}`);
out.push(`plural_module=${PLURAL_TMP}`);

for (const s of sites) {
  const bytes = src[s.line - 1];
  const holds = bytes.includes(s.tpl);
  out.push("");
  out.push(`site ${REL}:${s.line} template_holds_bytes=${holds}`);
  out.push(`  line_verbatim=${JSON.stringify(bytes.trim())}`);
  if (!holds) {
    out.push(`  VERDICT=ABORT recorded template is not a substring of the tip line`);
    continue;
  }
  for (const st of s.states) {
    const scope = {};
    if (s.vars.includes("duration")) scope.duration = st;
    if (s.vars.includes("activity")) scope.activity = { travel_from_prev_min: st };
    if (s.vars.includes("nearbyRadiusM")) scope.nearbyRadiusM = st;
    if (s.vars.includes("metres")) scope.metres = st;
    const names = Object.keys(scope);
    const rendered = new Function(...names, `return (${s.tpl});`)(...names.map((n) => scope[n]));
    const u = unitFor[s.line];
    const countedNumber = s.line === 294 ? Math.round(st) : s.line === 297 ? (st / 1000).toFixed(1) : st;
    const ifRuler = `${countedNumber} ${m.englishCountNoun(countedNumber, u)}`;
    out.push(`  count=${st} -> as_is="${rendered}" | if_ruler="${ifRuler}"`);
  }
}

const text = out.join("\n");
process.stdout.write(text + "\n");
fs.writeFileSync("D:/moodle/_qoder_huomingxi_0558/wt/review/huomingxi/unit_readings_0558_r1.txt", text + "\n", "utf8");
