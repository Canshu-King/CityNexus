// ORD-0558 unit-symbol probe: runs the REAL plural.ts bytes from the authoritative tip
// (transpiled by the repo's own typescript 5.9.3), no hand-written copy of the ruler.
import { execFileSync } from "node:child_process";
import { createRequire } from "node:module";
import crypto from "node:crypto";
import fs from "node:fs";

const require = createRequire(import.meta.url);
const ts = require("D:/moodle/_qoder_integration_20260919/frontend/node_modules/typescript");

const TIP = "7ce836f9afafe9e763527cba828719b414b18db8";
const REPO = "D:/moodle/CityNexus";
const REL = "frontend/src/lib/plural.ts";

const src = execFileSync("git", ["-C", REPO, "show", `${TIP}:${REL}`], { encoding: "utf8" });
const blobId = execFileSync("git", ["-C", REPO, "rev-parse", `${TIP}:${REL}`], { encoding: "utf8" }).trim();
const localSha1 = crypto.createHash("sha1").update(src, "utf8").digest("hex");

const js = ts.transpileModule(src, {
  compilerOptions: { module: ts.ModuleKind.ESNext, target: ts.ScriptTarget.ES2022 },
}).outputText;
const tmp = "D:/moodle/_qoder_huomingxi_0558/plural_real.mjs";
fs.writeFileSync(tmp, js, { encoding: "utf8" });
const m = await import("file:///" + tmp.replace(/\\/g, "/"));

const units = ["min", "m", "km"];
const counts = [1, 2, 45, 1.5, 800];
const nouns = ["change", "leg", "stop"];

const lines = [];
lines.push(`ts_version=${ts.version}`);
lines.push(`plural_blob_at_tip=${blobId}`);
lines.push(`plural_bytes_local_sha1=${localSha1}`);
lines.push(`src_lines=${src.split(/\r?\n/).length}`);
for (const u of units) {
  for (const c of counts) {
    lines.push(`unit=${u} count=${c} -> englishCountNoun="${m.englishCountNoun(c, u)}" regularPlural="${m.regularPlural(u)}"`);
  }
}
for (const n of nouns) {
  lines.push(`noun=${n} count=2 -> "${m.englishCountNoun(2, n)}" (control: ruler still works on real nouns)`);
}
lines.push(`isOne_string_1.0 -> englishCountNoun("1.0","km")="${m.englishCountNoun("1.0", "km")}" (km arm feeds toFixed(1))`);
process.stdout.write(lines.join("\n") + "\n");
