// ORD-0558 活明细 r6 — the last two ActivityDetail arms, measured three ways.
// (1) the tip's own bytes, (2) this branch's bytes, (3) the draft's suggested expression pulled out
// of _cn12_pl558draft2_1208.txt rather than retyped by this lane.
import { execFileSync } from "node:child_process";
import { createRequire } from "node:module";
import fs from "node:fs";

const require = createRequire(import.meta.url);
const ts = require("D:/moodle/_qoder_integration_20260919/frontend/node_modules/typescript");
const REPO = "D:/moodle/CityNexus";
const TIP = "26c8b9791f3559f2f0985bc79325da238c79d6d5";
const WT = "D:/moodle/_qoder_huomingxi_0558/wt";
const REL = "frontend/src/features/trip/ActivityDetail.tsx";
const DRAFT = "D:/moodle/_cn12_pl558draft2_1208.txt";

const pluralSrc = execFileSync("git", ["-C", REPO, "show", `${TIP}:frontend/src/lib/plural.ts`], { encoding: "utf8" });
const js = ts.transpileModule(pluralSrc, { compilerOptions: { module: ts.ModuleKind.ESNext, target: ts.ScriptTarget.ES2022 } }).outputText;
const tmp = "D:/moodle/_qoder_huomingxi_0558/plural_tip_r6.mjs";
fs.writeFileSync(tmp, js, "utf8");
const plural = await import("file:///" + tmp.replace(/\\/g, "/"));

const asLines = (t) => t.split(/\r?\n/);
const tipLines = asLines(execFileSync("git", ["-C", REPO, "show", `${TIP}:${REL}`], { encoding: "utf8" }));
const brnLines = asLines(fs.readFileSync(`${WT}/${REL}`, "utf8"));

const evalTpl = (tpl, scope) => {
  const names = Object.keys(scope);
  return new Function("englishCountNoun", ...names, `return (${tpl});`)(plural.englishCountNoun, ...names.map((n) => scope[n]));
};

// the draft's suggested replacement for the km row, taken from the draft file's own bytes
const draftRows = asLines(fs.readFileSync(DRAFT, "utf8"));
const kmRow = draftRows.find((l) => l.startsWith("frontend/src/features/trip/ActivityDetail.tsx:297"));
const kmCols = kmRow.split("|").map((c) => c.trim());
const kmDraftRaw = kmCols[2].split("//")[0].trim();
// the draft column carries the JSX closing brace after the template; keep only the template itself
const kmDraftExpr = (kmDraftRaw.match(/`[^`]*`/) || ["(no template found in draft column)"])[0];

const R_TIP = "`All within about ${nearbyRadiusM} m, ordered by straight-line distance.`";
const R_BRN = '`All within about ${nearbyRadiusM} ${englishCountNoun(nearbyRadiusM, "metre")}, ordered by straight-line distance.`';
const K_TIP = "`${(metres / 1000).toFixed(1)} km`";
const K_BRN = '`${(metres / 1000).toFixed(1)} ${englishCountNoun((metres / 1000).toFixed(1), "kilometre")}`';

const out = [];
out.push(`tip=${TIP}`);
out.push(`file=${REL}`);
out.push(`radius_is_a_literal_constant at tip:107 ${JSON.stringify((tipLines[106] ?? "").trim())}`);
out.push("");
out.push("=== site A: the nearby-list note ===");
out.push(`tip line 293 bytes   ${JSON.stringify((tipLines[292] ?? "").trim())}`);
out.push(`branch line 293 bytes ${JSON.stringify((brnLines[292] ?? "").trim())}`);
for (const r of [1500, 1, 2]) {
  out.push(`  nearbyRadiusM=${r} tip=${JSON.stringify(evalTpl(R_TIP, { nearbyRadiusM: r }))} branch=${JSON.stringify(evalTpl(R_BRN, { nearbyRadiusM: r }))}`);
}
out.push("  reachable on screen today: only nearbyRadiusM=1500, because line 107 is a literal.");
out.push("");
out.push("=== site B: a stop further than a kilometre away ===");
out.push(`tip line 311 bytes    ${JSON.stringify((tipLines[310] ?? "").trim())}`);
out.push(`branch line 311 bytes ${JSON.stringify((brnLines[310] ?? "").trim())}`);
out.push(`draft's suggested expression, read from ${DRAFT.split("/").pop()} (comment stripped): ${JSON.stringify(kmDraftExpr)}`);
for (const metres of [900, 1000, 1500, 2400]) {
  let draftR;
  try { draftR = evalTpl(kmDraftExpr, { metres }); } catch (e) { draftR = "EVAL_FAIL " + e.message; }
  out.push(`  metres=${metres} tip=${JSON.stringify(evalTpl(K_TIP, { metres }))} branch=${JSON.stringify(evalTpl(K_BRN, { metres }))} if_draft_copied=${JSON.stringify(draftR)}`);
}
const text = out.join("\n");
process.stdout.write(text + "\n");
fs.writeFileSync("D:/moodle/_qoder_huomingxi_0558/wt/review/huomingxi/activity_ab_r3.txt", text + "\n", "utf8");
