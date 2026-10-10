// ORD-0558 活明细 r4 — acceptance harness for the commander's 去系动词 ruling.
// Bundles the tip's bytes and this branch's bytes with the repo's own esbuild over the real
// import graph, then calls the exported poiImportCopy() for three counts (zero / one / many) in
// BOTH locales, before and after, byte for byte.
import { execFileSync } from "node:child_process";
import { createRequire } from "node:module";
import fs from "node:fs";
import path from "node:path";

const esbuild = createRequire(import.meta.url)("D:/moodle/_qoder_integration_20260919/frontend/node_modules/esbuild");
const WT = "D:/moodle/_qoder_huomingxi_0558/wt";
const REPO = "D:/moodle/CityNexus";
const TIP = "d89cfea25214b4bbb4e886dca765b096237362f1";
const REL = "frontend/src/features/poiimport/poiImportCopy.ts";
const PLURAL = "frontend/src/lib/plural.ts";

const base = "D:/moodle/_qoder_huomingxi_0558/cop_base";
fs.rmSync(base, { recursive: true, force: true });
for (const rel of [REL, PLURAL]) {
  const p = path.join(base, rel);
  fs.mkdirSync(path.dirname(p), { recursive: true });
  fs.writeFileSync(p, execFileSync("git", ["-C", REPO, "show", `${TIP}:${rel}`], { encoding: "utf8" }), "utf8");
}
const bTip = "D:/moodle/_qoder_huomingxi_0558/cop_tip.mjs";
const bBrn = "D:/moodle/_qoder_huomingxi_0558/cop_branch.mjs";
for (const [dir, outfile] of [[base, bTip], [WT, bBrn]]) {
  esbuild.buildSync({ entryPoints: [path.join(dir, REL)], bundle: true, format: "esm", outfile, platform: "neutral", logLevel: "error" });
}
const tipMod = await import("file:///" + bTip.replace(/\\/g, "/"));
const brnMod = await import("file:///" + bBrn.replace(/\\/g, "/"));

const keys = [
  { key: "collectedCount", params: (n) => ({ n, shelf: "Old Town" }) },
  { key: "collectAlready", params: (n) => ({ n, shelf: "Old Town" }) },
  { key: "addedCount", params: (n) => ({ n, day: "Day 2" }) },
];
const counts = [0, 1, 2];

const out = [];
out.push(`tip=${TIP}`);
out.push(`branch_worktree=${WT}`);
out.push(`method=esbuild bundle of tip bytes vs branch bytes, then the exported poiImportCopy() is called`);
let zhSame = 0, zhTotal = 0, enChanged = 0, enTotal = 0;
for (const k of keys) {
  out.push("");
  out.push(`key=${k.key}`);
  for (const n of counts) {
    const p = k.params(n);
    for (const loc of ["en", "zh"]) {
      const a = tipMod.poiImportCopy(loc, k.key, p);
      const b = brnMod.poiImportCopy(loc, k.key, p);
      const same = a === b;
      if (loc === "zh") { zhTotal += 1; if (same) zhSame += 1; }
      if (loc === "en") { enTotal += 1; if (!same) enChanged += 1; }
      out.push(`  n=${n} ${loc} tip   ${JSON.stringify(a)}`);
      out.push(`  n=${n} ${loc} branch ${JSON.stringify(b)} same=${same}`);
    }
  }
}
out.push("");
out.push(`SUMMARY zh_pairs_identical=${zhSame}/${zhTotal} en_pairs_changed=${enChanged}/${enTotal}`);
const text = out.join("\n");
process.stdout.write(text + "\n");
fs.writeFileSync("D:/moodle/_qoder_huomingxi_0558/wt/review/huomingxi/copula_ab_r1.txt", text + "\n", "utf8");
