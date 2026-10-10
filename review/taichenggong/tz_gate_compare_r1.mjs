/* ORD-0553 tz follow-up: prove this lane added no gate red, on a tree whose shared dependencies broke.

   The tree-wide gates are red right now for reasons that have nothing to do with this change: the
   `frontend/node_modules` this worktree junctions to is missing packages other lanes' code imports
   (`@dnd-kit/core`, `@babel/core`).  "Not my fault" is a claim, so it is measured instead: the same
   command is run against the tip's bytes and against this branch's bytes, and the two error sets are
   compared.  A change that adds nothing to the red set is a change the gate cannot be holding against.

   The product file is swapped for the run and written back in a finally; both hashes are printed, and
   the shared node_modules is never touched.

   Run: node review/taichenggong/tz_gate_compare_r1.mjs [--base=<40-hex>]
*/

import { spawnSync } from "node:child_process";
import { createHash } from "node:crypto";
import { readFileSync, writeFileSync } from "node:fs";
import path from "node:path";

const HERE = import.meta.dirname;
const REPO = path.resolve(HERE, "..", "..");
const FRONTEND = path.join(REPO, "frontend");
const TARGET_REL = "frontend/src/features/execution/V10LiveExecutionPanel.tsx";
const TARGET = path.join(REPO, TARGET_REL);
const REF = "refs/heads/mirror/integration-frontend-apple-pass1";

const liveTip = (spawnSync("git", ["-C", REPO, "ls-remote", "origin", REF], { encoding: "utf8" })
  .stdout.split(/\s+/)[0] ?? "");
const baseArg = process.argv.slice(2).find((a) => a.startsWith("--base="));
const TIP = baseArg ? baseArg.split("=")[1] : liveTip;
if (!/^[0-9a-f]{40}$/.test(TIP)) { console.error("no 40-hex generation to compare against"); process.exit(2); }

const sha = (t) => createHash("sha256").update(t).digest("hex").slice(0, 12);
const candBytes = readFileSync(TARGET, "utf8");
const baseBytes = spawnSync("git", ["-C", REPO, "show", `${TIP}:${TARGET_REL}`],
  { encoding: "utf8", maxBuffer: 64 * 1024 * 1024 }).stdout;
if (!baseBytes) { console.error("could not read the tip's bytes"); process.exit(2); }

const rows = [];
const say = (l) => { rows.push(l); console.log(l); };

function run(cmd, args) {
  const p = spawnSync(cmd, args, { cwd: FRONTEND, encoding: "utf8", maxBuffer: 64 * 1024 * 1024 });
  return { rc: p.returncode, out: (p.stdout ?? "") + (p.stderr ?? "") };
}
/* Only file-level diagnostics: the module-not-found lines that name a source file. */
function errors(text) {
  return text.split("\n").map((l) => l.trim()).filter((l) => /^[^\s]+\.tsx?\(\d+,\d+\): error/.test(l)).sort();
}

say(`0 compared tip=${TIP} live_tip=${liveTip}`);
say(`1 tip bytes sha=${sha(baseBytes)} branch bytes sha=${sha(candBytes)}`);

const results = {};
for (const state of ["tip", "branch"]) {
  writeFileSync(TARGET, state === "tip" ? baseBytes : candBytes, "utf8");
  const t = run(process.execPath, [path.join("node_modules", "typescript", "bin", "tsc"),
    "-p", "tsconfig.typecheck.json", "--noEmit"]);
  const b = run(process.execPath, [path.join("node_modules", "vite", "bin", "vite.js"), "build"]);
  results[state] = { tscRc: t.rc, tsc: errors(t.out), buildRc: b.rc,
    buildHead: b.out.split("\n").map((l) => l.trim()).filter(Boolean).slice(0, 3).join(" / ").slice(0, 240) };
  say(`2 state=${state} tsc rc=${t.rc} file_level_errors=${results[state].tsc.length}`);
  for (const e of results[state].tsc) say(`    ${e.slice(0, 150)}`);
  say(`3 state=${state} build rc=${b.rc} first lines: ${results[state].buildHead}`);
}

writeFileSync(TARGET, candBytes, "utf8");
const back = sha(readFileSync(TARGET, "utf8"));
say(`4 restored branch bytes sha=${back} expected=${sha(candBytes)} match=${back === sha(candBytes)}`);

const only = (side) => results[side].tsc.filter((e) => !results[side === "branch" ? "tip" : "branch"].tsc.includes(e));
const addedByBranch = only("branch");
const removedByBranch = only("tip");
say(`5 file-level diagnostics this change ADDS: ${addedByBranch.length} ${JSON.stringify(addedByBranch.slice(0, 3)).slice(0, 200)}`);
say(`6 file-level diagnostics this change REMOVES: ${removedByBranch.length} ${JSON.stringify(removedByBranch.slice(0, 3)).slice(0, 200)}`);
say(`7 build rc on tip=${results.tip.buildRc} on branch=${results.branch.buildRc} (equal means the break is not the change)`);
const verdict = addedByBranch.length === 0 && results.tip.buildRc === results.branch.buildRc
  ? "PASS this lane added no gate red; both generations fail the same way"
  : "FAIL this change moved the red set";
say(`8 ${verdict}`);
writeFileSync(path.join(HERE, "tz_gate_compare_r1.txt"), rows.join("\n") + "\n", "utf8");
process.exit(addedByBranch.length === 0 ? 0 : 1);
