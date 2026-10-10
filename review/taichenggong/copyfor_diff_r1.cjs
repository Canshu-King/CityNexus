/* ORD-0557 copyFor differential.
 *
 * The claim this tests: swapping two hardcoded media-type fallbacks for a read of the key the
 * traveller-label table already owns must move zero screen bytes.  "Looks the same" is not evidence,
 * so the whole {kicker,title,body} triple is rendered for every arm of every message_key, on the tip
 * bytes and on this tree's bytes, and the JSON is compared cell by cell.
 *
 * A ruler that never goes red proves nothing, so the run also builds a deliberate counter-arm: the
 * other way one could "move" the `empty ${body_kind} body` fallback (leave the field unset and let
 * the copy layer paint its own fallback).  That arm must bite, and it must name the cells it moves.
 *
 * Run: node review/taichenggong/copyfor_diff_r1.cjs [tip-sha]
 * Exit 0 only when candidate moves 0 cells and the counter-arm moves at least 1.
 */

const { execFileSync } = require("node:child_process");
const fs = require("node:fs");
const path = require("node:path");

const HERE = __dirname;
const REPO = path.resolve(HERE, "..", "..");
const TARGET = "frontend/src/lib/failureAttribution.ts";
const SRC = path.join(REPO, "frontend", "src", "lib");
const OUTDIR = path.join(HERE, "_build");
const REF = "refs/heads/mirror/integration-frontend-apple-pass1";
// Read the authoritative tip off origin at run time; an argument only pins a re-run of an older reading.
const TIP = process.argv[2] || execFileSync("git", ["-C", REPO, "ls-remote", "origin", REF],
  { encoding: "utf8" }).split(/\s+/)[0];
if (!/^[0-9a-f]{40}$/.test(TIP)) throw new Error("cannot read the authoritative tip");

// The exact bytes this order says must not be re-worded: the Chinese media-type fallback.
const ZH_FALLBACK = '?? "未知"';
// The one production site that leaves attribution.content_type unset, which is what makes the
// fallback reachable at all.
const COUNTER_FROM = 'null, error.content_type ?? `empty ${error.body_kind} body`);';
const COUNTER_TO = 'null, error.content_type);';

const esbuild = require(path.join(REPO, "frontend", "node_modules", "esbuild"));

function gitShow(rev) {
  return execFileSync("git", ["-C", REPO, "show", `${rev}:${TARGET}`],
    { encoding: "utf8", maxBuffer: 64 * 1024 * 1024 });
}

function gitBlob(rev) {
  try {
    return execFileSync("git", ["-C", REPO, "rev-parse", `${rev}:${TARGET}`], { encoding: "utf8" }).trim();
  } catch { return "<file absent at that revision>"; }
}
const candBlob = execFileSync("git", ["-C", REPO, "hash-object", TARGET], { encoding: "utf8" }).trim();

async function bundle(name, contents) {
  const outfile = path.join(OUTDIR, `${name}.cjs`);
  fs.mkdirSync(OUTDIR, { recursive: true });
  await esbuild.build({
    stdin: { contents, resolveDir: SRC, loader: "ts", sourcefile: `${name}.ts` },
    bundle: true,
    platform: "node",
    format: "cjs",
    outfile,
    logLevel: "silent",
  });
  delete require.cache[outfile];
  return require(outfile);
}

const MESSAGE_KEYS = [
  "failure.journeyNotFound", "failure.networkUnavailable", "failure.serverError",
  "failure.originInvalidResponse", "failure.rateLimited", "failure.rateLimitedNoWait",
  "failure.stateAlreadyMoved", "failure.noAnswer", "failure.unauthorized",
  "failure.forbidden", "failure.unknown", "failure.notInTable",
];

function cells(mod) {
  const out = {};
  const base = { evidence_kind: "HTTP_RESPONSE", source_layer: "RUNTIME", retryable: true,
    recovery_action: "retry", telemetry: "" };
  for (const message_key of MESSAGE_KEYS) {
    for (const http_status of [404, 500, null]) {
      for (const ct of ["text/html; charset=utf-8", undefined]) {
        for (const server_code of [null, "V13_FULL_GROUNDING_MISSING_MOBILITY_PAIR"]) {
          const attribution = { ...base, message_key, http_status, server_code,
            retry_after_ms: 1500 };
          if (ct !== undefined) attribution.content_type = ct;
          for (const zh of [true, false]) {
            for (const hasCachedCopy of [true, false]) {
              const copy = mod.copyFor(attribution, zh, { journeyId: "ca0f1ed1-0000-0000-0000", hasCachedCopy });
              const name = [message_key, `status=${http_status}`,
                ct === undefined ? "ct:unset" : "ct:given", server_code ? "code" : "nocode",
                zh ? "zh" : "en", hasCachedCopy ? "cached" : "nocache"].join("|");
              out[name] = JSON.stringify(copy);
            }
          }
        }
      }
    }
  }
  // The classified path, not just hand-built objects: what the request layer actually produces.
  const Error_ = mod.OriginResponseUnusableError;
  for (const [kind, header] of [["html", "text/html"], ["empty", null], ["not_json", ""]]) {
    const attribution = mod.classifyReadFailure(new Error_(200, header, kind));
    for (const zh of [true, false]) {
      for (const hasCachedCopy of [true, false]) {
        const name = `classified:${kind}:${header === null ? "nullHeader" : JSON.stringify(header)}|`
          + `${zh ? "zh" : "en"}|${hasCachedCopy ? "cached" : "nocache"}`;
        out[name] = JSON.stringify(mod.copyFor(attribution, zh, { hasCachedCopy }));
      }
    }
  }
  return out;
}

function diff(a, b) {
  const moved = [];
  for (const key of Object.keys(a)) {
    if (a[key] !== b[key]) moved.push([key, a[key], b[key]]);
  }
  return moved;
}

(async () => {
  const baseSrc = gitShow(TIP);
  const candSrc = fs.readFileSync(path.join(REPO, TARGET), "utf8");
  if (!baseSrc.includes(ZH_FALLBACK)) throw new Error("tip bytes no longer carry the fallback this order names");
  if (candSrc.includes(ZH_FALLBACK)) throw new Error("candidate still carries a hardcoded fallback");

  const counterSrc = baseSrc.replace(COUNTER_FROM, COUNTER_TO);
  if (counterSrc === baseSrc) throw new Error("counter-arm patch did not apply - the site moved");

  // Second counter-arm, aimed at this edit rather than at the alternative: a key name that does not
  // exist in the table still renders *something* (the label helper humanises the token), so the only
  // thing that proves my two lines are really reading the key is breaking the key name on purpose.
  const mutantSrc = candSrc.split('categoryLabel("UNKNOWN"').join('categoryLabel("UNKNOWX"');
  if (mutantSrc === candSrc) throw new Error("mutant patch did not apply - the read is not where this tool thinks it is");
  if (mutantSrc.includes('categoryLabel("UNKNOWN"')) throw new Error("mutant patch was partial; every site must change");

  const base = await bundle("base", baseSrc);
  const cand = await bundle("cand", candSrc);
  const counter = await bundle("counter", counterSrc);
  const mutant = await bundle("mutant", mutantSrc);

  const baseCells = cells(base);
  const candCells = cells(cand);
  const counterCells = cells(counter);
  const mutantCells = cells(mutant);

  const candMoved = diff(baseCells, candCells);
  const counterMoved = diff(baseCells, counterCells);
  const mutantMoved = diff(baseCells, mutantCells);

  const lines = [];
  const say = (s) => { lines.push(s); };
  const liveTip = execFileSync("git", ["-C", REPO, "ls-remote", "origin", REF], { encoding: "utf8" })
    .split(/\s+/)[0];
  say(`0 comparison generation (pinned for this run): ${TIP}`);
  say(`0b live authoritative tip at run time: ${liveTip}`);
  say(`0c file blob live=${gitBlob(liveTip)} pinned=${gitBlob(TIP)} candidate-on-disk=${candBlob}`);
  say(`1 cells rendered on both sides: ${Object.keys(baseCells).length}`);
  say(`2 candidate vs tip: cells moved = ${candMoved.length}`);
  for (const [name, before, after] of candMoved) say(`3 MOVED ${name}\n   was ${before}\n   now ${after}`);
  say(`4 counter-arm (leave the field unset instead) vs tip: cells moved = ${counterMoved.length}`);
  for (const [name, before, after] of counterMoved) {
    say(`5 counter MOVED ${name}`);
    say(`   was ${before.slice(0, 260)}`);
    say(`   now ${after.slice(0, 260)}`);
  }
  const probe = Object.keys(baseCells).filter((k) => k.startsWith("classified:not_json"));
  for (const k of probe) say(`6 this order's edited cell reads, on tip: ${baseCells[k].slice(0, 300)}`);
  for (const k of probe) say(`7 the same cell on candidate: ${candCells[k].slice(0, 300)}`);
  say(`8 mutant (the key name broken on purpose) vs tip: cells moved = ${mutantMoved.length}`);
  for (const [name, , after] of mutantMoved.slice(0, 4)) {
    say(`9 mutant ${name} now ${after.slice(0, 220)}`);
  }

  const verdict = candMoved.length !== 0
    ? "FAIL candidate moved screen bytes"
    : (counterMoved.length === 0 ? "FAIL counter-arm did not bite; the ruler is blind"
      : (mutantMoved.length === 0 ? "FAIL mutant did not bite; the screen is not reading the key"
        : `PASS candidate=0 moved, counter-arm bit ${counterMoved.length}, mutant bit ${mutantMoved.length}`));
  say(`10 ${verdict}`);
  const text = lines.join("\n") + "\n";
  fs.writeFileSync(path.join(HERE, "copyfor_diff_r1.txt"), text, "utf8");
  process.stdout.write(text);
  console.log(verdict);
  if (!verdict.startsWith("PASS")) process.exit(1);
})().catch((err) => { console.error("ERROR " + err.message); process.exit(2); });
