/* Behavioural differential for the failure-attribution kicker table.
 *
 * The text arm proves the table exists and its rows keep their arms. This proves the stronger thing:
 * `copyFor` still returns the SAME words for every reason, both locales, both cached-copy states.
 * A copy refactor that moves one screen's sentence by one character is exactly what a substring
 * comparison can miss and an invocation cannot.
 *
 * It builds the "before" tree from a git revision and the "after" tree from a worktree root, so it
 * re-runs anywhere. Nothing is stubbed: both sides load the module's real `lib` directory.
 *
 * usage: node copyfor_diff_r1.cjs [tree-root] [before-rev]
 * exit 0 when every cell matches, 1 otherwise.
 */
const cp = require("child_process");
const fs = require("fs");
const path = require("path");

const ROOT = path.resolve(process.argv[2] || "D:/moodle/_qoder_laneE9_20261008/wt9");
const BEFORE_REV = process.argv[3] || "cf5915ea948579b4dc80aa57a299639b5440150e";
const TS = "D:/moodle/_qoder_cmdr_ref_20260921/frontend/node_modules/typescript";
const REPO = "D:/moodle/CityNexus";
const SCRATCH = path.join(ROOT, "review", "laneE9-failure-kicker", "_scratch");

const ts = require(TS);

function transpileDir(inDir, outDir) {
  fs.rmSync(outDir, { recursive: true, force: true });
  fs.mkdirSync(outDir, { recursive: true });
  for (const f of fs.readdirSync(inDir)) {
    if (!f.endsWith(".ts")) continue;
    const src = fs.readFileSync(path.join(inDir, f), "utf8");
    const js = ts.transpileModule(src, {
      compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 },
    }).outputText;
    fs.writeFileSync(path.join(outDir, f.replace(/\.ts$/, ".js")), js);
  }
}

function stageBefore(outDir) {
  const raw = path.join(SCRATCH, "raw_before");
  fs.rmSync(raw, { recursive: true, force: true });
  fs.mkdirSync(raw, { recursive: true });
  // git-bash eats Windows backslashes, so hand the shell forward slashes only.
  const rawPosix = raw.replace(/\\/g, "/");
  cp.execSync(`git -C ${REPO} archive ${BEFORE_REV} frontend/src/lib | tar -x -C ${rawPosix}`, {
    stdio: "pipe",
  });
  transpileDir(path.join(raw, "frontend", "src", "lib"), outDir);
}

function stageAfter(outDir) {
  transpileDir(path.join(ROOT, "frontend", "src", "lib"), outDir);
}

const KEYS = [
  "failure.journeyNotFound", "failure.networkUnavailable", "failure.serverError",
  "failure.originInvalidResponse", "failure.rateLimited", "failure.rateLimitedNoWait",
  "failure.stateAlreadyMoved", "failure.noAnswer", "failure.unauthorized",
  "failure.forbidden", "failure.readFailed", "an-unmapped-key",
];

function main() {
  fs.rmSync(SCRATCH, { recursive: true, force: true });
  fs.mkdirSync(SCRATCH, { recursive: true });
  const beforeDir = path.join(SCRATCH, "before");
  const afterDir = path.join(SCRATCH, "after");
  stageBefore(beforeDir);
  stageAfter(afterDir);
  const before = require(path.join(beforeDir, "failureAttribution.js"));
  const after = require(path.join(afterDir, "failureAttribution.js"));

  let cells = 0;
  const bad = [];
  for (const key of KEYS) {
    for (const zh of [true, false]) {
      for (const hasCachedCopy of [true, false]) {
        const attribution = {
          reason: "R", evidence_kind: "E", http_status: 503, source_layer: "S",
          retryable: true, recovery_action: "A", message_key: key,
          server_code: null, content_type: "application/json",
        };
        const detail = { journeyId: "ca0f1ed1-1111-2222-3333-444455556666", hasCachedCopy };
        let a, b;
        try { a = JSON.stringify(before.copyFor({ ...attribution }, zh, detail)); }
        catch (e) { a = "THrown:" + String(e); }
        try { b = JSON.stringify(after.copyFor({ ...attribution }, zh, detail)); }
        catch (e) { b = "THrown:" + String(e); }
        cells += 1;
        if (a !== b) {
          bad.push(`copyFor(${key}, zh=${zh}, cached=${hasCachedCopy}) moved`);
        }
      }
    }
  }
  console.log(`copyFor differential: ${cells} cells against ${BEFORE_REV}, ${bad.length} moved`);
  for (const item of bad) console.log("  MOVED: " + item);
  fs.rmSync(SCRATCH, { recursive: true, force: true });
  return bad.length ? 1 : 0;
}

process.exit(main());
