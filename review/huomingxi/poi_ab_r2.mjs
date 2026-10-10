// ORD-0558 r2 — A/B readout of the REAL poiImportCopy module.
// Bundles the tip's bytes and this branch's bytes with the repo's own esbuild, then calls the
// exported poiImportCopy() for count=1 and count=2 in BOTH locales. Nothing is hand-copied:
// the only difference between the two bundles is the four {plural:...} markers on the en values.
import { execFileSync } from "node:child_process";
import fs from "node:fs";
import path from "node:path";

const WT = "D:/moodle/_qoder_huomingxi_0558/wt";
const TIP = "996f1b7588580a14fbbdec5301a6e4a7b70c93e4";
const REPO = "D:/moodle/CityNexus";
const ESBUILD = "D:/moodle/_qoder_integration_20260919/frontend/node_modules/.bin/esbuild.cmd";
const REL = "frontend/src/features/poiimport/poiImportCopy.ts";
const PLURAL = "frontend/src/lib/plural.ts";

import { createRequire } from "node:module";
const esbuild = createRequire(import.meta.url)("D:/moodle/_qoder_integration_20260919/frontend/node_modules/esbuild");
const base = "D:/moodle/_qoder_huomingxi_0558/ab_base";
fs.rmSync(base, { recursive: true, force: true });
for (const rel of [REL, PLURAL]) {
  const p = path.join(base, rel);
  fs.mkdirSync(path.dirname(p), { recursive: true });
  fs.writeFileSync(p, execFileSync("git", ["-C", REPO, "show", `${TIP}:${rel}`], { encoding: "utf8" }), "utf8");
}

function bundle(entryDir, outfile) {
  esbuild.buildSync({
    entryPoints: [path.join(entryDir, REL)],
    bundle: true,
    format: "esm",
    outfile,
    platform: "neutral",
    logLevel: "error",
  });
}
const bTip = "D:/moodle/_qoder_huomingxi_0558/ab_tip.mjs";
const bBrn = "D:/moodle/_qoder_huomingxi_0558/ab_branch.mjs";
bundle(base, bTip);
bundle(WT, bBrn);

const tipMod = await import("file:///" + bTip.replace(/\\/g, "/"));
const brnMod = await import("file:///" + bBrn.replace(/\\/g, "/"));

const cases = [
  { key: "addedCount", one: { n: 1, day: "Day 2" }, two: { n: 2, day: "Day 2" } },
  { key: "charCount", one: { n: 1 }, two: { n: 2 } },
  { key: "counts", one: { extracted: 1, resolved: 1, ambiguous: 0, unresolved: 0 }, two: { extracted: 2, resolved: 1, ambiguous: 3, unresolved: 4 } },
  { key: "selectedCount", one: { n: 1, total: 1 }, two: { n: 2, total: 5 } },
];

const out = [];
out.push(`tip=${TIP}`);
out.push(`branch_worktree=${WT}`);
out.push(`bundled_with=esbuild (repo node_modules, real import graph, no hand copy)`);
let zhSame = 0;
let enChanged = 0;
for (const c of cases) {
  out.push("");
  out.push(`key=${c.key}`);
  for (const state of ["one", "two"]) {
    const p = c[state];
    for (const loc of ["en", "zh"]) {
      const a = tipMod.poiImportCopy(loc, c.key, p);
      const b = brnMod.poiImportCopy(loc, c.key, p);
      const same = a === b;
      if (loc === "zh" && same) zhSame += 1;
      if (loc === "en" && !same) enChanged += 1;
      out.push(`  ${state} ${loc} tip=${JSON.stringify(a)}`);
      out.push(`  ${state} ${loc} branch=${JSON.stringify(b)} same=${same}`);
    }
  }
}
out.push("");
out.push(`SUMMARY zh_pairs_identical=${zhSame}/8 en_pairs_changed=${enChanged}/8`);
const text = out.join("\n");
process.stdout.write(text + "\n");
fs.writeFileSync("D:/moodle/_qoder_huomingxi_0558/wt/review/huomingxi/poi_copy_ab_r2.txt", text + "\n", "utf8");
