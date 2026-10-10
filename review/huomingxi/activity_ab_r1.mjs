// ORD-0558 round 3 — A/B of the REAL ActivityDetail.tsx template bytes (tip vs this branch).
// For each site the instrument (1) takes the tip's line bytes and the branch's line bytes,
// (2) asserts the recorded template is a verbatim substring of that line, (3) evaluates both
// templates with the repo's own lib/plural.ts (transpiled from the tip's bytes by the repo's own
// typescript) and prints the English the screen would show for count=1 and count=2.
import { execFileSync } from "node:child_process";
import { createRequire } from "node:module";
import fs from "node:fs";

const require = createRequire(import.meta.url);
const ts = require("D:/moodle/_qoder_integration_20260919/frontend/node_modules/typescript");
const REPO = "D:/moodle/CityNexus";
const TIP = "996f1b7588580a14fbbdec5301a6e4a7b70c93e4";
const WT = "D:/moodle/_qoder_huomingxi_0558/wt";
const REL = "frontend/src/features/trip/ActivityDetail.tsx";

const pluralSrc = execFileSync("git", ["-C", REPO, "show", `${TIP}:frontend/src/lib/plural.ts`], { encoding: "utf8" });
const pluralBlob = execFileSync("git", ["-C", REPO, "rev-parse", `${TIP}:frontend/src/lib/plural.ts`], { encoding: "utf8" }).trim();
const js = ts.transpileModule(pluralSrc, { compilerOptions: { module: ts.ModuleKind.ESNext, target: ts.ScriptTarget.ES2022 } }).outputText;
fs.writeFileSync("D:/moodle/_qoder_huomingxi_0558/plural_tip.mjs", js, "utf8");
const plural = await import("file:///D:/moodle/_qoder_huomingxi_0558/plural_tip.mjs");

const tipLines = plural2(execFileSync("git", ["-C", REPO, "show", `${TIP}:${REL}`], { encoding: "utf8" }));
const brnLines = plural2(fs.readFileSync(`${WT}/${REL}`, "utf8"));
function plural2(text) { return text.split(/\r?\n/); }

// each site: tip line number, tip template, branch line number, branch template, the variable it counts
const sites = [
  { tl: 150, tt: "`${duration} min`", bl: 151, bt: "`${duration} ${englishCountNoun(duration, \"minute\")}`", v: "duration", states: [1, 2, 45] },
  { tl: 186, tt: "`${activity.travel_from_prev_min} min`", bl: 187, bt: "`${activity.travel_from_prev_min} ${englishCountNoun(activity.travel_from_prev_min, \"minute\")}`", v: "activity", states: [1, 2] },
  { tl: 294, tt: "`${Math.round(metres)} m`", bl: 295, bt: "`${Math.round(metres)} ${englishCountNoun(Math.round(metres), \"metre\")}`", v: "metres", states: [1, 2, 850] },
];

const out = [];
out.push(`tip=${TIP}`);
out.push(`tip_file=${REL}`);
out.push(`plural_ts_blob_at_tip=${pluralBlob}`);
out.push(`tip_lines=${tipLines.length} branch_lines=${brnLines.length}`);
for (const s of sites) {
  const tl = tipLines[s.tl - 1] ?? "";
  const bl = brnLines[s.bl - 1] ?? "";
  const okT = tl.includes(s.tt);
  const okB = bl.includes(s.bt);
  out.push("");
  out.push(`site tip:${s.tl} holds=${okT} verbatim=${JSON.stringify(tl.trim())}`);
  out.push(`site branch:${s.bl} holds=${okB} verbatim=${JSON.stringify(bl.trim())}`);
  if (!okT || !okB) { out.push("  VERDICT=ABORT recorded template is not a substring of that line"); continue; }
  for (const st of s.states) {
    const scope = s.v === "activity" ? { activity: { travel_from_prev_min: st } } : { [s.v]: st };
    const names = Object.keys(scope);
    const mk = (tpl) => new Function("englishCountNoun", ...names, `return (${tpl});`)(plural.englishCountNoun, ...names.map((n) => scope[n]));
    out.push(`  n=${st} tip=${JSON.stringify(mk(s.tt))} branch=${JSON.stringify(mk(s.bt))}`);
  }
}
// the >=60 arm of the same duration concept is deliberately untouched
out.push("");
out.push(`untouched_compact_arm tip:147=${JSON.stringify((tipLines[146] ?? "").trim())}`);
out.push(`untouched_compact_arm branch:148=${JSON.stringify((brnLines[147] ?? "").trim())}`);
const text = out.join("\n");
process.stdout.write(text + "\n");
fs.writeFileSync("D:/moodle/_qoder_huomingxi_0558/wt/review/huomingxi/activity_ab_r1.txt", text + "\n", "utf8");
